"""
JARVIS morning command routine — drop-in plugin, no core changes.

What one call does, in order:

  1. Open or connect to JAUTOMATIC (attach if running, launch if not).
  2. Job Search using the saved profile.
  3. Move every job scoring >= 40% into the Applications QUEUE (a review list —
     nothing is ever submitted).
  4. Open Education, work out the skill gaps those shortlisted jobs imply, and
     choose ONE course that closes the most of them. Report it and its total
     duration.
  5. Build an ADHD-friendly day plan: short fixed work blocks, scheduled breaks,
     one concrete action per block, hardest work first.
  6. Add read-only summaries: Gmail, Outlook, WhatsApp Business, market,
     Shilatech, and JAUTOMATIC itself.

Hard limits, enforced in _jmorning_safety rather than by convention: JARVIS
never submits an application, sends an email, sends a WhatsApp message, deletes
a message, or executes a trade. The suite exposes exactly one non-GET call —
staging jobs into the review queue — and any attempt at a forbidden action is
refused and reported in the run's safety line.

Startup behaviour: the routine self-schedules on first import (plugin discovery
runs at JARVIS startup), once per calendar day, in a background thread, and
writes its report to memory/. Nothing in core is touched. Set `autorun` to off
in plugin settings if you would rather trigger it by voice only.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

from plugins import _jmorning_jautomatic as ja
from plugins import _jmorning_plan as planner
from plugins import _jmorning_sources as sources
from plugins import _jmorning_news as news
from plugins import _jmorning_github as github
from plugins._jmorning_safety import AUDIT, BlockedAction

NAMESPACE = "jarvis_morning"
REPORT_DIR = Path(__file__).resolve().parent.parent / "memory"

PLUGIN = {
    "name": "morning_routine",
    "description": (
        "Run the full morning command routine: connect to JAUTOMATIC, run Job Search with "
        "the saved profile, move all jobs scoring 40% or higher into the Applications review "
        "queue, pick one Education course that closes the resulting skill gaps, report the "
        "course and its total duration, build an ADHD-friendly day plan of short work blocks "
        "with breaks, and give read-only Gmail, Outlook, WhatsApp Business, market, Shilatech "
        "and JAUTOMATIC summaries. Trigger phrases: 'good morning', 'morning routine', "
        "'run my morning briefing', 'start my day'. This tool is READ-ONLY plus queueing: it "
        "never submits applications, sends email or WhatsApp, deletes messages, or trades. "
        "For the previous run's saved report use morning_report instead of re-running this."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "min_score": {"type": "NUMBER",
                          "description": "Match-score cutoff for queueing, in percent. Default 40."},
            "spoken_only": {"type": "BOOLEAN",
                            "description": "Return the short spoken summary without the full plan text."},
        },
        "required": [],
    },
    "behavior": "NON_BLOCKING",
    "scheduling": "WHEN_IDLE",
}

PLUGIN_SETTINGS = {
    "namespace": NAMESPACE,
    "title": "Morning routine",
    "fields": [
        {"key": "autorun", "label": "Run automatically at startup (once a day)",
         "type": "bool", "default": True},
        {"key": "day_end", "label": "Plan ends at (HH:MM)", "type": "text", "default": "17:00"},
        {"key": "block_minutes", "label": "Work block length (minutes)", "type": "number", "default": 25},
        {"key": "break_minutes", "label": "Short break (minutes)", "type": "number", "default": 5},
        {"key": "long_break_minutes", "label": "Long break every 4 blocks (minutes)",
         "type": "number", "default": 20},
        {"key": "lunch_at", "label": "Lunch at (HH:MM)", "type": "text", "default": "13:00"},
        {"key": "lunch_minutes", "label": "Lunch length (minutes)", "type": "number", "default": 45},
        {"key": "min_score", "label": "Queue jobs scoring at least (%)", "type": "number", "default": 40},
        {"key": "max_course_blocks", "label": "Max study blocks per day", "type": "number", "default": 4},
        {"key": "max_job_blocks", "label": "Max job-review blocks per day", "type": "number", "default": 2},
        {"key": "summary_cache_seconds", "label": "Reuse briefing summaries for (seconds, 0 = always refetch)",
         "type": "number", "default": 300},
    ],
}

GITHUB_PLUGIN_SETTINGS = {
    "namespace": "shilatech_github", "title": "Shilatech GitHub (read-only)",
    "fields": [
        {"key": "repo", "label": "Repository", "type": "text", "default": "eugenshila/shilatech"},
        {"key": "api_token", "label": "Fine-grained read-only PAT", "type": "password", "default": ""},
    ],
}


def _cfg(key, default):
    try:
        from memory.config_manager import get_plugin_setting
        val = get_plugin_setting(NAMESPACE, key, default)
    except Exception:
        val = default
    return default if val in (None, "") else val


def _num(key, default):
    try:
        return float(_cfg(key, default))
    except Exception:
        return float(default)


def _bool(key, default):
    val = _cfg(key, default)
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "on")
    return bool(val)


# ─────────────────────── briefing summary cache ───────────────────────
# The eight external briefing sources (Gmail, Outlook, WhatsApp, market,
# Shilatech, news, marketing, GitHub) are pure reads whose answers do not
# change meaningfully within a few minutes, yet fetching them — GitHub alone
# is four REST calls — dominates run_routine()'s wall time. Re-running the
# routine (a repeated voice command, the autorun racing a manual run, or the
# test suite exercising it a dozen times) therefore paid the full network
# cost every time. A short TTL cache keeps one process-local copy; the
# JAUTOMATIC summary is NOT cached because it reflects the current run's
# connection state and queue counts. Set `summary_cache_seconds` to 0 to
# refetch on every run.

_summary_cache: tuple[float, list] | None = None
_summary_cache_lock = threading.Lock()


def _external_summaries() -> list:
    """Return the eight read-only briefing summaries, reusing a recent fetch."""
    global _summary_cache
    ttl = _num("summary_cache_seconds", 300)
    now = time.monotonic()
    if ttl > 0:
        with _summary_cache_lock:
            if _summary_cache is not None and now - _summary_cache[0] < ttl:
                return list(_summary_cache[1])
    summaries = []
    for fn in (sources.gmail_summary, sources.outlook_summary, sources.whatsapp_summary,
               sources.market_summary, sources.shilatech_summary,
               news.kenya_news_summary, news.marketing_advisory, github.github_summary):
        try:
            summaries.append(fn())
        except BlockedAction as e:
            summaries.append(sources.Summary(fn.__name__, "refused.", degraded=True, note=str(e)[:90]))
        except Exception as e:
            summaries.append(sources.Summary(fn.__name__, "failed.", degraded=True, note=str(e)[:90]))
    if ttl > 0:
        with _summary_cache_lock:
            _summary_cache = (now, list(summaries))
    return summaries


# ───────────────────────────── the routine ─────────────────────────────

def run_routine(min_score: float | None = None, logger=None) -> dict:
    """
    Execute the whole routine and return a structured result. Separated from
    run() so the autorun thread and the tests can call it without a UI, and so
    every step is independently assertable.
    """
    log = logger or (lambda _m: None)
    AUDIT.clear()
    started = datetime.now()
    threshold = float(min_score if min_score is not None else _num("min_score", 40))
    result: dict = {"threshold": threshold, "started": started, "errors": []}

    # 1 — connect
    client = ja.JautomaticClient(logger=log)
    try:
        result["connection"] = client.connect()
    except BlockedAction as e:
        result["connection"] = "blocked"
        result["errors"].append(str(e))
    except Exception as e:
        result["connection"] = "offline"
        result["errors"].append(f"JAUTOMATIC connect: {e}")

    # 2 — job search with the saved profile
    profile = {}
    jobs: list[ja.Job] = []
    try:
        profile = client.saved_profile()
        jobs = client.job_search(profile)
    except Exception as e:
        result["errors"].append(f"Job Search: {e}")
    result["profile"] = profile
    result["jobs_found"] = len(jobs)

    # 3 — queue everything at or above the cutoff
    shortlist = ja.filter_by_score(jobs, threshold)
    result["shortlist"] = shortlist
    result["below_cutoff"] = len(jobs) - len(shortlist)
    try:
        result["queued"] = client.queue_jobs(shortlist)
    except Exception as e:
        result["queued"] = {"queued": 0, "ids": [], "where": f"failed: {e}"}
        result["errors"].append(f"Queueing: {e}")

    # 4 — Education: gaps -> exactly one course
    gaps = ja.skill_gaps(shortlist, profile)
    result["gaps"] = gaps
    course, covered = None, {}
    try:
        course, covered = ja.choose_course(client.courses(), gaps)
    except Exception as e:
        result["errors"].append(f"Education: {e}")
    result["course"] = course
    result["course_covers"] = covered

    # 5 — the plan
    block = int(_num("block_minutes", 25))
    tasks: list[tuple[str, str]] = []
    tasks += planner.course_tasks(course, int(_num("max_course_blocks", 4)), block)
    for job in shortlist[: int(_num("max_job_blocks", 2))]:
        tasks.append((f"Review & tailor CV: {job.title} — {job.company}",
                      f"{job.score:.0f}% match, queued (you submit it, not JARVIS)"))
    tasks.append(("Triage inbox", "Outlook + Gmail, read-only triage — reply by hand later"))
    tasks.append(("WhatsApp Business check", "read overnight enquiries, answer manually"))
    tasks.append(("Shilatech review", "open tickets and today's numbers"))

    plan = planner.build_plan(
        tasks,
        start=started,
        end_time=str(_cfg("day_end", "17:00")),
        block_minutes=block,
        break_minutes=int(_num("break_minutes", 5)),
        long_break_minutes=int(_num("long_break_minutes", 20)),
        lunch_at=str(_cfg("lunch_at", "13:00")),
        lunch_minutes=int(_num("lunch_minutes", 45)),
    )
    result["plan"] = plan

    # 6 — read-only briefings (external sources cached for a few minutes;
    #     the JAUTOMATIC summary below is always built fresh for this run)
    summaries = _external_summaries()
    try:
        js = client.summary()
        lines = [f"{k.replace('_', ' ').title()}: {v}" for k, v in js.items() if k != "notes"]
        if js.get("notes"):
            lines.append(str(js["notes"]))
        summaries.append(sources.Summary(
            "JAUTOMATIC",
            f"{len(shortlist)} job(s) queued today from {len(jobs)} found "
            f"(connection: {result.get('connection')}).",
            lines, degraded=not client.online,
            note="snapshot data" if not client.online else ""))
    except Exception as e:
        summaries.append(sources.Summary("JAUTOMATIC", "summary unavailable.",
                                         degraded=True, note=str(e)[:90]))
    result["summaries"] = summaries
    result["blocked_actions"] = [e.line() for e in AUDIT.blocked]
    return result


# ───────────────────────────── rendering ─────────────────────────────

def render(result: dict) -> str:
    th = result["threshold"]
    shortlist = result.get("shortlist", [])
    course = result.get("course")
    plan: planner.Plan = result.get("plan")
    out: list[str] = []

    out.append(f"Good morning. Morning routine, {result['started']:%A %d %B, %H:%M}.")
    out.append("")
    out.append(f"JAUTOMATIC — {result.get('connection')}.")
    out.append(f"Job Search with your saved profile: {result.get('jobs_found', 0)} role(s) found, "
               f"{len(shortlist)} at or above {th:.0f}%, "
               f"{result.get('below_cutoff', 0)} left behind the cutoff.")
    for job in shortlist:
        out.append(f"    • {job.score:.0f}%  {job.title} — {job.company}"
                   + (f" ({job.location})" if job.location else ""))
    q = result.get("queued", {})
    out.append(f"Moved {q.get('queued', 0)} into {q.get('where', 'the queue')}. "
               f"Nothing submitted — that stays your call.")

    out.append("")
    gaps = result.get("gaps", [])
    if gaps:
        out.append("Skill gaps across those roles: "
                   + ", ".join(f"{g} (×{n})" for g, n in gaps[:6]) + ".")
    if course:
        covers = result.get("course_covers") or {}
        out.append(f"Education — one course chosen: “{course.title}”"
                   + (f" ({course.provider})" if course.provider else "") + ".")
        out.append(f"    Total duration: {ja.format_duration(course.duration_minutes)}"
                   + (f" across {course.modules} modules" if course.modules else "")
                   + (f", level {course.level}" if course.level else "") + ".")
        if covers:
            out.append(f"    Chosen because it closes: {', '.join(sorted(covers))}.")
    else:
        out.append("Education — no course could be selected.")

    if plan:
        out.append("")
        out.append(f"Today's plan — {len(plan.work_blocks)} work blocks, "
                   f"{plan.focus_minutes} focused minutes, a break after every one:")
        out.append(plan.text())

    out.append("")
    out.append("Briefing (all read-only):")
    for s in result.get("summaries", []):
        out.append("  " + s.text())

    out.append("")
    blocked = result.get("blocked_actions", [])
    out.append("Safety — no applications submitted, no email or WhatsApp sent, "
               "nothing deleted, no trades executed."
               + (f" {len(blocked)} attempt(s) refused." if blocked else ""))
    for line in blocked:
        out.append(f"    ! {line}")
    for err in result.get("errors", []):
        out.append(f"    (note) {err}")
    return "\n".join(out)


def spoken(result: dict) -> str:
    shortlist = result.get("shortlist", [])
    course = result.get("course")
    plan = result.get("plan")
    bits = [f"Good morning. {len(shortlist)} job(s) scored at or above "
            f"{result['threshold']:.0f}% and are queued for your review — none submitted."]
    if course:
        bits.append(f"For Education I picked “{course.title}”, "
                    f"{ja.format_duration(course.duration_minutes)} in total.")
    if plan:
        tail = (", finishing with a catch-up buffer"
                if any(b.kind == "buffer" for b in plan.blocks) else "")
        bits.append(f"Your day is {len(plan.work_blocks)} short blocks with breaks between, "
                    f"{plan.focus_minutes} focused minutes{tail}.")
        if plan.unplanned:
            bits.append(f"{len(plan.unplanned)} task(s) carried to tomorrow.")
    degraded = [s.source for s in result.get("summaries", []) if s.degraded]
    if degraded:
        bits.append(f"Working from snapshots for {', '.join(degraded)}.")
    return " ".join(bits)


def save_report(text: str) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"morning_report_{datetime.now():%Y-%m-%d}.md"
    try:
        path.write_text(text, "utf-8")
    except Exception:
        pass
    return path


# ───────────────────────────── plugin entry ─────────────────────────────

def run(parameters: dict, player=None, session_memory=None) -> str:
    def log(msg):
        if player:
            try:
                player.write_log(f"JARVIS: {msg}")
            except Exception:
                pass

    try:
        result = run_routine(parameters.get("min_score"), logger=log)
        full = render(result)
        save_report(full)
        if player:
            for line in full.splitlines():
                try:
                    player.write_log(line)
                except Exception:
                    break
        return spoken(result) if parameters.get("spoken_only") else full
    except Exception as e:
        return f"Sir, the morning routine failed: {e}"


# ───────────────────────────── startup autorun ─────────────────────────────
# Plugin discovery happens during JARVIS startup, so importing this module IS
# the startup hook — no core edit needed. The work is done on a daemon thread
# after a short delay so it cannot slow the boot or block the UI, and a date
# stamp keeps it to once per day across restarts.

_STAMP = REPORT_DIR / ".morning_routine_last_run"


def _already_ran_today() -> bool:
    try:
        return _STAMP.read_text("utf-8").strip() == datetime.now().strftime("%Y-%m-%d")
    except Exception:
        return False


def _mark_ran() -> None:
    try:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        _STAMP.write_text(datetime.now().strftime("%Y-%m-%d"), "utf-8")
    except Exception:
        pass


def _autorun() -> None:
    time.sleep(float(_cfg("autorun_delay", 12)))
    try:
        if _already_ran_today():
            return
        text = render(run_routine())
        path = save_report(text)
        _mark_ran()
        print(f"[morning_routine] Startup run complete — report saved to {path}")
    except Exception as e:
        print(f"[morning_routine] Startup run failed: {e}")


def _schedule_autorun() -> None:
    if not _bool("autorun", True) or _already_ran_today():
        return
    threading.Thread(target=_autorun, name="morning_routine_autorun", daemon=True).start()


# Guarded so importing the module in a test or a REPL does not fire the routine.
import os as _os  # noqa: E402
if _os.environ.get("JARVIS_MORNING_NO_AUTORUN") != "1":
    try:
        _schedule_autorun()
    except Exception:
        pass
