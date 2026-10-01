"""
Tests for the morning-routine plugin suite.

Runs standalone (`python tests/test_morning_routine.py`) as well as under
pytest, because the repo ships no test runner and the point is that anyone can
verify the safety rules without installing anything.

The safety assertions are the important ones: they encode the user's hard rules
as executable checks, so a later edit that quietly adds a send/submit/delete/
trade path fails here rather than in production.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

os.environ["JARVIS_MORNING_NO_AUTORUN"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from plugins import _jmorning_jautomatic as ja          # noqa: E402
from plugins import _jmorning_plan as planner           # noqa: E402
from plugins import _jmorning_safety as safety          # noqa: E402
from plugins import _jmorning_sources as sources        # noqa: E402
from plugins import morning_report, morning_routine     # noqa: E402


class TestSafetyRules(unittest.TestCase):
    """The five things JARVIS must never do."""

    FORBIDDEN = [
        "submit the job application for J-1001",
        "apply to the Automation Engineer role",
        "send an email to the recruiter",
        "reply to this email thread",
        "forward the message to accounts",
        "send a WhatsApp message to the client",
        "delete the message from the inbox",
        "archive this email thread",
        "execute a trade on BTC",
        "place a buy order for 10 shares",
        "sell the position",
        "cancel the pending order",
    ]

    ALLOWED = [
        "read recent mail headers from Outlook (Gmail)",
        "list unread messages",
        "search jobs in JAUTOMATIC using the saved profile",
        "queue jobs into the JAUTOMATIC Applications review list",
        "read market prices for the watchlist",
        "open or connect to JAUTOMATIC",
        "summarise the Shilatech business metrics",
    ]

    def test_forbidden_intents_are_blocked(self):
        for intent in self.FORBIDDEN:
            with self.subTest(intent=intent):
                allowed, reason = safety.classify(intent)
                self.assertFalse(allowed, f"{intent!r} should be blocked")
                self.assertTrue(reason)
                with self.assertRaises(safety.BlockedAction):
                    safety.guard(intent)

    def test_read_only_intents_pass(self):
        for intent in self.ALLOWED:
            with self.subTest(intent=intent):
                allowed, _ = safety.classify(intent)
                self.assertTrue(allowed, f"{intent!r} should be allowed")
                safety.guard(intent)

    def test_http_refuses_state_changing_methods(self):
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            with self.subTest(method=method):
                with self.assertRaises(safety.BlockedAction):
                    safety.http_get("http://127.0.0.1:1/x", method=method)

    def test_blocked_attempts_are_audited(self):
        safety.AUDIT.clear()
        with self.assertRaises(safety.BlockedAction):
            safety.guard("send an email to finance")
        self.assertEqual(len(safety.AUDIT.blocked), 1)
        self.assertIn("send an email", safety.AUDIT.blocked[0].line())

    def test_suite_exposes_no_write_helpers(self):
        for mod in (safety, sources, ja):
            for name in dir(mod):
                self.assertNotIn(
                    name.lower(),
                    ("http_post", "http_put", "http_delete", "send_mail", "send_message",
                     "submit_application", "apply_to_job", "place_order", "execute_trade"),
                    f"{mod.__name__} exposes a forbidden helper: {name}")

    def test_source_modules_contain_no_send_or_delete_calls(self):
        """
        A backstop against a future edit reintroducing a write path.

        Comments and docstrings are stripped first: the modules *describe* the
        calls they refuse to make, and a naive grep would flag that prose while
        a real `.Send()` hidden in a long file is what we actually care about.
        """
        import io
        import tokenize

        banned = (".Send(", ".Delete(", ".Reply(", ".ReplyAll(", ".Forward(", ".Move(")
        for mod in (sources, ja, planner, morning_routine):
            src = Path(mod.__file__).read_text("utf-8")
            code = []
            for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                if tok.type in (tokenize.COMMENT, tokenize.STRING):
                    continue
                code.append(tok.string)
            code = " ".join(code).replace(" ", "")
            for token in banned:
                self.assertNotIn(token.replace(" ", ""), code,
                                 f"{mod.__name__} contains a live {token} call")


class TestJobSearchAndScoring(unittest.TestCase):
    def setUp(self):
        self.client = ja.JautomaticClient()
        self.client.online = False
        self.profile = self.client.saved_profile()
        self.jobs = self.client.job_search(self.profile)

    def test_search_returns_jobs_sorted_by_score(self):
        self.assertTrue(self.jobs)
        scores = [j.score for j in self.jobs]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_threshold_is_inclusive_at_40(self):
        jobs = [ja.Job(id="a", title="A", company="C", score=40.0),
                ja.Job(id="b", title="B", company="C", score=39.9),
                ja.Job(id="c", title="C", company="C", score=100.0)]
        kept = ja.filter_by_score(jobs, 40)
        self.assertEqual([j.id for j in kept], ["a", "c"])

    def test_fractional_scores_are_normalised_to_percent(self):
        self.assertEqual(ja.Job.from_api({"id": "x", "title": "t", "score": 0.86}).score, 86.0)
        self.assertEqual(ja.Job.from_api({"id": "x", "title": "t", "score": 86}).score, 86.0)

    def test_demo_shortlist_matches_expected_cutoff(self):
        kept = ja.filter_by_score(self.jobs, 40)
        self.assertEqual([j.id for j in kept], ["J-1001", "J-1002", "J-1003", "J-1004"])

    def test_queueing_never_submits(self):
        with tempfile.TemporaryDirectory() as tmp:
            ja.SNAPSHOT_FILE = Path(tmp) / "snap.json"
            res = self.client.queue_jobs(ja.filter_by_score(self.jobs, 40))
            self.assertEqual(res["queued"], 4)
            staged = json.loads((Path(tmp) / "jautomatic_pending_queue.json").read_text())
            self.assertTrue(all(s["stage"] == "queued" for s in staged))
            self.assertFalse(any("submit" in json.dumps(s).lower() for s in staged))


class TestSkillGapsAndCourseChoice(unittest.TestCase):
    def setUp(self):
        client = ja.JautomaticClient()
        client.online = False
        self.profile = client.saved_profile()
        self.shortlist = ja.filter_by_score(client.job_search(self.profile), 40)
        self.courses = client.courses()

    def test_gaps_exclude_skills_already_held(self):
        gaps = dict(ja.skill_gaps(self.shortlist, self.profile))
        self.assertNotIn("python", gaps)
        self.assertNotIn("sql", gaps)
        self.assertIn("docker", gaps)

    def test_gaps_ordered_by_demand(self):
        gaps = ja.skill_gaps(self.shortlist, self.profile)
        self.assertEqual(gaps[0][0], "docker")
        self.assertEqual(gaps[0][1], 4)

    def test_exactly_one_course_chosen_and_it_closes_the_top_gap(self):
        gaps = ja.skill_gaps(self.shortlist, self.profile)
        course, covered = ja.choose_course(self.courses, gaps)
        self.assertIsInstance(course, ja.Course)
        self.assertEqual(course.id, "C-01")
        self.assertIn("docker", covered)

    def test_total_duration_is_reported_in_hours_and_minutes(self):
        course, _ = ja.choose_course(self.courses, ja.skill_gaps(self.shortlist, self.profile))
        self.assertEqual(course.duration_minutes, 420)
        self.assertEqual(ja.format_duration(course.duration_minutes), "7h")
        self.assertEqual(ja.format_duration(95), "1h 35m")
        self.assertEqual(ja.format_duration(45), "45m")

    def test_duration_parsing_variants(self):
        self.assertEqual(ja.Course.from_api({"title": "t", "duration": "6h 30m"}).duration_minutes, 390)
        self.assertEqual(ja.Course.from_api({"title": "t", "duration_hours": 2}).duration_minutes, 120)

    def test_falls_back_to_shortest_course_when_nothing_matches(self):
        course, covered = ja.choose_course(self.courses, [("cobol", 3)])
        self.assertEqual(course.id, "C-03")
        self.assertEqual(covered, {})


class TestAdhdPlan(unittest.TestCase):
    def build(self, n_tasks=10, start="08:00", end="17:00"):
        start_dt = datetime(2026, 10, 1, *map(int, start.split(":")))
        tasks = [(f"Task {i}", f"detail {i}") for i in range(n_tasks)]
        return planner.build_plan(tasks, start=start_dt, end_time=end,
                                  block_minutes=25, break_minutes=5,
                                  long_break_minutes=20, lunch_at="13:00",
                                  lunch_minutes=45)

    def test_work_blocks_are_short_and_uniform(self):
        plan = self.build()
        self.assertTrue(plan.work_blocks)
        self.assertTrue(all(b.minutes == 25 for b in plan.work_blocks))

    def test_a_break_follows_every_work_block(self):
        plan = self.build()
        kinds = [b.kind for b in plan.blocks]
        for i, kind in enumerate(kinds[:-1]):
            if kind == "work" and i + 1 < len(kinds):
                self.assertIn(kinds[i + 1], ("break", "long_break", "buffer"),
                              f"work block {i} is not followed by a break")

    def test_long_break_after_four_blocks(self):
        plan = self.build()
        self.assertTrue(any(b.kind == "long_break" for b in plan.blocks))

    def test_blocks_never_overlap_and_run_in_order(self):
        plan = self.build()
        for a, b in zip(plan.blocks, plan.blocks[1:]):
            self.assertLessEqual(a.end, b.start)

    def test_plan_never_runs_past_the_end_time(self):
        plan = self.build(n_tasks=40, end="12:00")
        self.assertTrue(plan.blocks)
        self.assertLessEqual(plan.blocks[-1].end.hour, 12)
        self.assertTrue(plan.unplanned, "overflow tasks should be carried forward, not crammed")

    def test_lunch_is_protected(self):
        plan = self.build(n_tasks=30)
        lunch = [b for b in plan.blocks if b.title.startswith("Lunch")]
        self.assertEqual(len(lunch), 1)
        for b in plan.work_blocks:
            self.assertFalse(b.start < lunch[0].end and b.end > lunch[0].start)

    def test_each_block_has_exactly_one_action(self):
        plan = self.build()
        for b in plan.work_blocks:
            self.assertNotIn(" and ", b.title.lower())
            self.assertTrue(b.detail, "every work block needs a concrete finish line")

    def test_no_break_overlaps_lunch(self):
        """Regression: a 5-minute break used to be opened at 13:00, on top of lunch."""
        start = datetime(2026, 10, 1, 12, 35)
        tasks = [(f"Task {i}", f"d{i}") for i in range(8)]
        plan = planner.build_plan(tasks, start=start, end_time="17:00",
                                  block_minutes=25, break_minutes=5,
                                  long_break_minutes=20, lunch_at="13:00",
                                  lunch_minutes=45)
        for a, b in zip(plan.blocks, plan.blocks[1:]):
            self.assertLessEqual(a.end, b.start, f"{a.line()} overlaps {b.line()}")

    def test_plan_never_ends_on_a_break(self):
        # A closing buffer is a fine way to end; an idle break is not.
        for end in ("11:00", "12:00", "15:30", "17:00"):
            with self.subTest(end=end):
                plan = self.build(n_tasks=40, end=end)
                self.assertIn(plan.blocks[-1].kind, ("work", "buffer"))

    def test_module_ranges_cover_every_module_exactly_once(self):
        """Regression: 7 modules over 4 blocks used to report 1, 2, 4, 6."""
        import re
        for modules, blocks in ((7, 4), (5, 2), (3, 3), (10, 4), (2, 5)):
            with self.subTest(modules=modules, blocks=blocks):
                course = ja.Course(id="C", title="T", duration_minutes=modules * 60,
                                   modules=modules)
                tasks = planner.course_tasks(course, max_blocks=blocks, block_minutes=60)
                seen = []
                for _, detail in tasks:
                    nums = [int(n) for n in re.findall(r"\d+", detail)][:-1]
                    seen.extend(range(nums[0], (nums[1] if len(nums) > 1 else nums[0]) + 1))
                self.assertEqual(seen, sorted(set(seen)), "module numbers repeat or go backwards")
                self.assertEqual(seen[0], 1)
                self.assertEqual(seen[-1], modules)

    def test_course_split_into_block_sized_tasks_with_module_numbers(self):
        course = ja.Course(id="C", title="Docker", duration_minutes=420, modules=7)
        tasks = planner.course_tasks(course, max_blocks=4, block_minutes=25)
        self.assertEqual(len(tasks), 4)
        self.assertIn("module 1 of 7", tasks[0][1])
        self.assertTrue(all(t[0] == "Study: Docker" for t in tasks))


class TestSummaries(unittest.TestCase):
    def test_every_source_returns_a_summary_and_never_raises(self):
        for fn in (sources.gmail_summary, sources.outlook_summary,
                   sources.whatsapp_summary, sources.market_summary,
                   sources.shilatech_summary):
            with self.subTest(source=fn.__name__):
                s = fn()
                self.assertIsInstance(s, sources.Summary)
                self.assertTrue(s.headline)
                self.assertIsInstance(s.text(), str)

    def test_unreachable_sources_are_marked_degraded_not_silent(self):
        s = sources.outlook_summary()   # no Outlook in CI / on Linux
        if s.degraded:
            self.assertTrue(s.note, "a degraded source must explain itself")


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.result = morning_routine.run_routine()

    def test_routine_completes_every_step(self):
        r = self.result
        self.assertIn(r["connection"], ("attached", "launched", "offline"))
        self.assertGreater(r["jobs_found"], 0)
        self.assertTrue(r["shortlist"])
        self.assertTrue(all(j.score >= 40 for j in r["shortlist"]))
        self.assertIsNotNone(r["course"])
        self.assertTrue(r["plan"].work_blocks)
        self.assertGreaterEqual(len(r["summaries"]), 6)

    def test_all_six_briefing_sources_present(self):
        names = {s.source for s in self.result["summaries"]}
        for expected in ("Gmail", "Outlook", "WhatsApp Business", "Market",
                         "Shilatech", "JAUTOMATIC"):
            self.assertIn(expected, names)

    def test_no_forbidden_action_was_attempted(self):
        self.assertEqual(self.result["blocked_actions"], [])

    def test_report_mentions_course_duration_and_safety(self):
        text = morning_routine.render(self.result)
        self.assertIn("Total duration:", text)
        self.assertIn("Nothing submitted", text)
        self.assertIn("no trades executed", text)
        self.assertIn("Today's plan", text)

    def test_spoken_summary_is_short_and_safe(self):
        line = morning_routine.spoken(self.result)
        self.assertLess(len(line), 600)
        self.assertIn("none submitted", line.lower())

    def test_plugin_entry_point_returns_text(self):
        out = morning_routine.run({"min_score": 40})
        self.assertIsInstance(out, str)
        self.assertIn("Good morning", out)

    def test_custom_threshold_is_respected(self):
        r = morning_routine.run_routine(min_score=70)
        self.assertTrue(all(j.score >= 70 for j in r["shortlist"]))
        self.assertEqual(len(r["shortlist"]), 2)

    def test_entry_point_never_raises_on_bad_input(self):
        self.assertIsInstance(morning_routine.run({"min_score": "nonsense"}), str)


class TestPluginContract(unittest.TestCase):
    """The loader's rules, checked here so a bad PLUGIN dict fails in tests."""

    MODULES = (morning_routine, morning_report)

    def test_plugin_dicts_validate(self):
        import re
        for mod in self.MODULES:
            with self.subTest(plugin=mod.__name__):
                p = mod.PLUGIN
                self.assertRegex(p["name"], r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")
                self.assertTrue(p["description"].strip())
                self.assertEqual(p["parameters"]["type"], "OBJECT")
                self.assertTrue(callable(mod.run))

    def test_names_do_not_collide_with_core_tools(self):
        main = (Path(__file__).resolve().parent.parent / "main.py").read_text("utf-8", "replace")
        for mod in self.MODULES:
            self.assertNotIn(f'"name": "{mod.PLUGIN["name"]}"', main)

    def test_discovery_accepts_the_suite(self):
        from core.plugin_loader import discover_plugins
        reg = discover_plugins(Path(__file__).resolve().parent.parent / "plugins",
                               core_tool_names=set(), logger=lambda _m: None)
        names = [r["name"] for r in reg.list_for_ui() if r["valid"]]
        self.assertIn("morning_routine", names)
        self.assertIn("morning_report", names)
        for rec in reg.list_for_ui():
            self.assertTrue(rec["valid"], f"{rec['name']} rejected: {rec['error']}")

    def test_helpers_are_underscore_prefixed_so_they_are_not_loaded(self):
        for mod in (safety, sources, ja, planner):
            self.assertTrue(Path(mod.__file__).name.startswith("_"))

    def test_no_core_files_were_modified(self):
        import subprocess
        root = Path(__file__).resolve().parent.parent
        out = subprocess.run(["git", "diff", "--name-only", "579f56df13c308b18f8ea9e415aa12da15d9c999"],
                             cwd=root, capture_output=True, text=True).stdout.split()
        protected = ("main.py", "ui.py", "core/", "memory/config_manager.py",
                     "memory/memory_manager.py", "actions/", "dashboard/")
        for path in out:
            self.assertFalse(path.startswith(protected),
                             f"core file modified: {path}")


class TestReportPlayback(unittest.TestCase):
    def test_report_round_trips(self):
        text = morning_routine.render(morning_routine.run_routine())
        path = morning_routine.save_report(text)
        self.assertTrue(path.exists())
        back = morning_report.run({"section": "full"})
        self.assertIn("Good morning", back)
        self.assertIn("Today's plan", morning_report.run({"section": "plan"}))

    def test_queue_playback_lists_nothing_as_submitted(self):
        out = morning_report.run({"section": "queue"})
        self.assertIsInstance(out, str)
        self.assertNotIn("submitted", out.replace("none submitted", ""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
