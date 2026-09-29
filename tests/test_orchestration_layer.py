"""Tier 2: task queue, planner, executor, warmup, profile memory, file processor, API auth."""

from __future__ import annotations

import json
import threading
import time

import pytest

from jarvis.core.task_queue import Priority, TaskQueue, TaskStatus
from jarvis.core.types import AgentResponse


class _ScriptedEngine:
    """Returns canned responses in order; repeats the last one."""

    def __init__(self, *responses: str):
        self.responses = list(responses) or ["{}"]
        self.calls: list[str] = []

    def generate(self, messages, **kwargs):
        self.calls.append(messages[-1].content if messages else "")
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        return AgentResponse(content=self.responses[index])


# ── task queue ────────────────────────────────────────────────────────────────


@pytest.fixture
def queue():
    q = TaskQueue(workers=1)
    q.start()
    yield q
    q.stop(timeout=2)


def test_task_runs_and_reports_result(queue):
    task = queue.submit("add", lambda t: 2 + 2)
    assert task.wait(timeout=5)
    assert task.status is TaskStatus.COMPLETED
    assert task.result == 4


def test_task_failure_is_captured_not_raised(queue):
    task = queue.submit("boom", lambda t: 1 / 0)
    assert task.wait(timeout=5)
    assert task.status is TaskStatus.FAILED
    assert "ZeroDivisionError" in task.error


def test_high_priority_jumps_the_queue():
    q = TaskQueue(workers=1)
    order: list[str] = []
    gate = threading.Event()

    q.submit("blocker", lambda t: gate.wait(timeout=5))
    q.start()
    time.sleep(0.1)  # let the blocker occupy the single worker

    q.submit("low", lambda t: order.append("low"), priority=Priority.LOW)
    q.submit("high", lambda t: order.append("high"), priority=Priority.HIGH)
    gate.set()
    time.sleep(0.6)
    q.stop(timeout=2)
    assert order[:2] == ["high", "low"]


def test_equal_priorities_are_fifo():
    q = TaskQueue(workers=1)
    order: list[int] = []
    gate = threading.Event()
    q.submit("blocker", lambda t: gate.wait(timeout=5))
    q.start()
    time.sleep(0.1)
    for i in range(4):
        q.submit(f"t{i}", lambda t, i=i: order.append(i))
    gate.set()
    time.sleep(0.8)
    q.stop(timeout=2)
    assert order == [0, 1, 2, 3]


def test_pending_task_is_cancelled_before_it_runs():
    q = TaskQueue(workers=1)
    ran: list[str] = []
    gate = threading.Event()
    q.submit("blocker", lambda t: gate.wait(timeout=5))
    q.start()
    time.sleep(0.1)
    victim = q.submit("victim", lambda t: ran.append("victim"))
    assert q.cancel(victim.task_id) is True
    gate.set()
    time.sleep(0.4)
    q.stop(timeout=2)
    assert ran == []
    assert victim.status is TaskStatus.CANCELLED


def test_running_task_sees_the_cancel_flag(queue):
    observed = {}

    def _long(task):
        for _ in range(50):
            if task.cancelled:
                observed["stopped_early"] = True
                return "stopped"
            time.sleep(0.02)
        return "finished"

    task = queue.submit("long", _long)
    time.sleep(0.1)
    queue.cancel(task.task_id)
    task.wait(timeout=5)
    assert observed.get("stopped_early") is True
    assert task.status is TaskStatus.CANCELLED


def test_progress_is_visible_in_the_snapshot(queue):
    gate = threading.Event()

    def _work(task):
        task.note("halfway")
        gate.wait(timeout=5)
        return "done"

    queue.submit("reporting", _work)
    time.sleep(0.15)
    snapshot = queue.snapshot()
    assert snapshot["counts"]["running"] == 1
    assert snapshot["active"][0]["progress"] == "halfway"
    gate.set()


def test_bad_completion_callback_does_not_kill_the_worker(queue):
    queue.submit("cb", lambda t: "x", on_complete=lambda t: 1 / 0)
    later = queue.submit("after", lambda t: "still working")
    assert later.wait(timeout=5)
    assert later.status is TaskStatus.COMPLETED


# ── planner ───────────────────────────────────────────────────────────────────


def test_catalogue_is_generated_from_live_specs():
    from jarvis.agents.planner import tool_catalogue

    text = tool_catalogue(["file_read", "file_write"])
    assert "file_read" in text and "file_write" in text
    # The argument names come from the real ToolSpec schema, not from prose.
    assert "- path" in text and "required" in text


def test_catalogue_flags_tools_that_need_confirmation():
    from jarvis.agents.planner import tool_catalogue

    assert "confirmation" in tool_catalogue(["shell"])


def test_planner_accepts_a_valid_plan():
    from jarvis.agents.planner import plan

    engine = _ScriptedEngine(
        json.dumps({"reasoning": "read it", "steps": [
            {"tool": "file_read", "arguments": {"path": "/tmp/x"}, "purpose": "read"}
        ]})
    )
    result = plan("read /tmp/x", engine=engine)
    assert result.ok
    assert result.steps[0].tool == "file_read"


def test_planner_rejects_an_unknown_tool():
    from jarvis.agents.planner import plan

    engine = _ScriptedEngine(json.dumps({"steps": [{"tool": "frobnicate", "arguments": {}}]}))
    result = plan("do magic", engine=engine)
    assert not result.ok
    assert "unknown tool" in result.errors[0]


def test_planner_rejects_invented_arguments():
    from jarvis.agents.planner import plan

    engine = _ScriptedEngine(
        json.dumps({"steps": [{"tool": "file_read", "arguments": {"pathh": "/tmp/x"}}]})
    )
    result = plan("read", engine=engine)
    assert not result.ok
    assert "no argument" in result.errors[0]


def test_planner_rejects_missing_required_arguments():
    from jarvis.agents.planner import plan

    engine = _ScriptedEngine(json.dumps({"steps": [{"tool": "file_read", "arguments": {}}]}))
    result = plan("read", engine=engine)
    assert "missing required argument" in result.errors[0]


def test_planner_survives_non_json_output():
    from jarvis.agents.planner import plan

    result = plan("x", engine=_ScriptedEngine("I would start by thinking about it."))
    assert not result.ok
    assert "valid JSON" in result.errors[0]


def test_planner_caps_step_count():
    from jarvis.agents.planner import plan

    steps = [{"tool": "file_read", "arguments": {"path": f"/tmp/{i}"}} for i in range(20)]
    result = plan("many", engine=_ScriptedEngine(json.dumps({"steps": steps})), max_steps=3)
    assert len(result.steps) == 3


def test_plan_flags_when_approval_is_needed():
    from jarvis.agents.planner import plan

    engine = _ScriptedEngine(
        json.dumps({"steps": [{"tool": "shell", "arguments": {"command": "ls"}}]})
    )
    assert plan("list files", engine=engine).needs_approval is True


# ── executor ──────────────────────────────────────────────────────────────────


def _plan_of(*steps):
    from jarvis.agents.planner import Plan, Step

    return Plan(goal="test", steps=[Step(tool=t, arguments=a) for t, a in steps])


def test_executor_runs_every_step(tmp_path, monkeypatch):
    from jarvis.agents import executor as ex

    calls = []
    monkeypatch.setattr(ex, "_run_tool", lambda step: (calls.append(step.tool), ("ok", False))[1])
    result = ex.execute(_plan_of(("file_read", {}), ("file_read", {})))
    assert result.ok
    assert len(calls) == 2


def test_executor_retries_a_transient_failure(monkeypatch):
    from jarvis.agents import executor as ex

    attempts = {"n": 0}

    def _fake(step):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return "Error: connection refused", True
        return "worked", False

    monkeypatch.setattr(ex, "_run_tool", _fake)
    result = ex.execute(_plan_of(("file_read", {})))
    assert attempts["n"] == 2
    assert result.ok


def test_executor_skips_a_non_critical_failure(monkeypatch):
    from jarvis.agents import executor as ex

    monkeypatch.setattr(ex, "_run_tool", lambda step: ("Error: No module named 'faiss'", True))
    result = ex.execute(_plan_of(("file_read", {}), ("file_read", {})))
    assert result.results[0].decision == "skip"
    assert len(result.results) == 2, "execution should continue past a skip"


def test_executor_aborts_on_permission_denied(monkeypatch):
    from jarvis.agents import executor as ex

    monkeypatch.setattr(ex, "_run_tool", lambda step: ("Error: permission denied", True))
    result = ex.execute(_plan_of(("file_read", {}), ("file_read", {})))
    assert result.aborted
    assert len(result.results) == 1, "nothing should run after an abort"


def test_executor_replans_once_then_gives_up(monkeypatch):
    from jarvis.agents import executor as ex

    monkeypatch.setattr(ex, "_run_tool", lambda step: ("Error: no such file or directory", True))
    replans = {"n": 0}

    def _fake_plan(goal, engine=None, **kwargs):
        replans["n"] += 1
        return _plan_of(("file_read", {"path": "/tmp/other"}))

    monkeypatch.setattr(ex, "make_plan", _fake_plan)
    result = ex.execute(_plan_of(("file_read", {"path": "/tmp/x"})), max_replans=1)
    assert replans["n"] == 1
    assert result.replans == 1
    assert result.aborted


def test_executor_honours_cancellation(monkeypatch):
    from jarvis.agents import executor as ex

    monkeypatch.setattr(ex, "_run_tool", lambda step: ("ok", False))
    result = ex.execute(_plan_of(("file_read", {}), ("file_read", {})), is_cancelled=lambda: True)
    assert result.cancelled
    assert result.results == []


def test_run_goal_reports_an_unworkable_plan():
    from jarvis.agents.executor import run_goal

    _, result = run_goal("x", engine=_ScriptedEngine("not json at all"))
    assert result.aborted
    assert "could not build a workable plan" in result.messages[0].lower()


# ── ollama warmup ─────────────────────────────────────────────────────────────


def test_warmup_sends_the_static_prompt_and_one_token(monkeypatch):
    from jarvis.engine.ollama import OllamaEngine

    captured = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _fake_urlopen(req, timeout=None):
        captured["payload"] = json.loads(req.data.decode())
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    engine = OllamaEngine()
    assert engine.warmup("STATIC SYSTEM PROMPT") is True

    payload = captured["payload"]
    assert payload["messages"][0]["content"] == "STATIC SYSTEM PROMPT"
    assert payload["options"]["num_predict"] == 1, "warmup must not generate an answer"
    assert payload["keep_alive"], "model should stay resident after warming"


def test_warmup_is_idempotent_for_the_same_prompt(monkeypatch):
    from jarvis.engine.ollama import OllamaEngine

    calls = {"n": 0}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def _fake_urlopen(req, timeout=None):
        calls["n"] += 1
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen)
    engine = OllamaEngine()
    engine.warmup("same")
    engine.warmup("same")
    assert calls["n"] == 1
    engine.warmup("different")
    assert calls["n"] == 2


def test_failed_warmup_is_not_an_error(monkeypatch):
    from jarvis.engine.ollama import OllamaEngine

    def _boom(req, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr("urllib.request.urlopen", _boom)
    assert OllamaEngine().warmup("x") is False


# ── profile memory ────────────────────────────────────────────────────────────


@pytest.fixture
def profile(tmp_path):
    from jarvis.memory.profile import Profile

    return Profile(home=tmp_path)


def test_profile_round_trips(profile):
    profile.remember("identity", "name", "Eugene")
    assert profile.get("identity", "name") == "Eugene"
    assert "Eugene" in profile.for_prompt()


def test_profile_rejects_unknown_categories(profile):
    assert "Unknown category" in profile.remember("astrology", "sign", "leo")


def test_profile_truncates_an_over_long_value(profile):
    from jarvis.memory.profile import MAX_VALUE_CHARS

    profile.remember("notes", "essay", "x" * (MAX_VALUE_CHARS * 3))
    assert len(profile.get("notes", "essay")) == MAX_VALUE_CHARS


def test_profile_enforces_a_total_budget(profile):
    from jarvis.memory.profile import MAX_TOTAL_CHARS

    for i in range(200):
        profile.remember("notes", f"fact{i}", "y" * 300)
    assert profile.size()["chars"] <= MAX_TOTAL_CHARS


def test_budget_eviction_prefers_notes_over_identity(profile):
    profile.remember("identity", "name", "Eugene")
    for i in range(200):
        profile.remember("notes", f"junk{i}", "z" * 300)
    assert profile.get("identity", "name") == "Eugene", "identity should outlive notes"


def test_empty_profile_adds_nothing_to_the_prompt(profile):
    assert profile.for_prompt() == ""


def test_corrupt_profile_does_not_break_startup(profile):
    profile.path.parent.mkdir(parents=True, exist_ok=True)
    profile.path.write_text("{ this is not json", encoding="utf-8")
    assert profile.all() == {}


def test_profile_is_injected_into_the_system_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    import jarvis.memory.profile as profile_mod

    profile_mod.reset()
    profile_mod.get_profile().remember("identity", "name", "Eugene")

    from jarvis.agents.base import BaseAgent

    class _Agent(BaseAgent):
        def __init__(self):
            self.preset = type("P", (), {"system_prompt": "You are JARVIS.", "tools": []})()

        def run(self, prompt, context="", **kwargs):
            return None

    message = _Agent()._system_message()
    assert "You are JARVIS." in message.content
    assert "Eugene" in message.content
    profile_mod.reset()


# ── file processor ────────────────────────────────────────────────────────────


def test_detects_types_by_extension():
    from pathlib import Path

    from jarvis.tools.file_processor import detect_type

    assert detect_type(Path("a.pdf")) == "pdf"
    assert detect_type(Path("a.py")) == "code"
    assert detect_type(Path("a.CSV")) == "csv"
    assert detect_type(Path("a.xyz")) == "unknown"


def test_stats_needs_no_model(tmp_path):
    from jarvis.tools.file_processor import FileProcessorTool

    target = tmp_path / "notes.txt"
    target.write_text("one two three\nfour five\n", encoding="utf-8")
    out = FileProcessorTool().run(path=str(target), action="stats")
    assert "words: 5" in out


def test_csv_analysis_is_local_and_typed(tmp_path):
    from jarvis.tools.file_processor import FileProcessorTool

    target = tmp_path / "data.csv"
    target.write_text("name,score\nada,10\nbob,30\ncy,20\n", encoding="utf-8")
    out = FileProcessorTool().run(path=str(target), action="analyze")
    assert "3 data row(s), 2 column(s)" in out
    assert "score: numeric" in out and "min=10" in out and "max=30" in out
    assert "name: text" in out


def test_json_validation_reports_the_error_position(tmp_path):
    from jarvis.tools.file_processor import FileProcessorTool

    good = tmp_path / "good.json"
    good.write_text('{"a": 1, "b": 2}', encoding="utf-8")
    assert "Valid JSON object with 2 key(s)" in FileProcessorTool().run(path=str(good), action="validate")

    bad = tmp_path / "bad.json"
    bad.write_text('{"a": 1,,}', encoding="utf-8")
    assert "Invalid JSON at line" in FileProcessorTool().run(path=str(bad), action="validate")


def test_archive_listing(tmp_path):
    import zipfile

    from jarvis.tools.file_processor import FileProcessorTool

    archive = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("a.txt", "hello")
        zf.writestr("b.txt", "world")
    out = FileProcessorTool().run(path=str(archive), action="list")
    assert "2 entries" in out and "a.txt" in out


def test_unsupported_verb_lists_what_is_possible(tmp_path):
    from jarvis.tools.file_processor import FileProcessorTool

    target = tmp_path / "x.mp4"
    target.write_bytes(b"\x00\x00")
    out = FileProcessorTool().run(path=str(target), action="analyze")
    assert "not available for a video file" in out
    assert "stats" in out


def test_missing_file_is_reported_not_raised():
    from jarvis.tools.file_processor import FileProcessorTool

    assert "no such file" in FileProcessorTool().run(path="/nope/nothing.txt").lower()


def test_oversized_file_is_refused(tmp_path, monkeypatch):
    import jarvis.tools.file_processor as fp

    target = tmp_path / "big.txt"
    target.write_text("x" * 100, encoding="utf-8")
    monkeypatch.setattr(fp, "MAX_BYTES", 10)
    assert "the limit is" in fp.FileProcessorTool().run(path=str(target))


def test_summarize_uses_the_model_with_extracted_text(tmp_path):
    from jarvis.tools.file_processor import FileProcessorTool

    target = tmp_path / "doc.md"
    target.write_text("# Title\nThe budget is 400 dollars.", encoding="utf-8")
    engine = _ScriptedEngine("It is about a 400 dollar budget.")
    out = FileProcessorTool().run(path=str(target), action="summarize", engine=engine)
    assert "400 dollar" in out
    assert "budget is 400 dollars" in engine.calls[0], "the file text must reach the model"


# ── API auth ──────────────────────────────────────────────────────────────────


def test_token_is_generated_and_persisted_privately(tmp_path, monkeypatch):
    import os

    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.delenv("JARVIS_API_TOKEN", raising=False)
    from jarvis.server import auth

    first = auth.get_token()
    assert len(first) > 20
    assert auth.get_token() == first, "token must be stable across calls"
    assert oct(os.stat(tmp_path / "api_token").st_mode)[-3:] == "600"


def test_rotation_invalidates_the_old_token(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.delenv("JARVIS_API_TOKEN", raising=False)
    from jarvis.server import auth

    old = auth.get_token()
    assert auth.rotate_token() != old


def test_loopback_is_exempt_but_remote_is_not(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.delenv("JARVIS_API_TOKEN", raising=False)
    monkeypatch.delenv("JARVIS_API_REQUIRE_TOKEN", raising=False)
    from jarvis.server import auth

    allowed, _ = auth.check("/tasks", "127.0.0.1", {}, {})
    assert allowed is True

    allowed, reason = auth.check("/tasks", "192.168.1.50", {}, {})
    assert allowed is False and "Missing API token" in reason


def test_remote_request_with_a_valid_token_is_allowed(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.delenv("JARVIS_API_TOKEN", raising=False)
    from jarvis.server import auth

    token = auth.get_token()
    allowed, _ = auth.check("/tasks", "192.168.1.50", {"authorization": f"Bearer {token}"}, {})
    assert allowed is True

    allowed, reason = auth.check("/tasks", "192.168.1.50", {"authorization": "Bearer wrong"}, {})
    assert allowed is False and "Invalid" in reason


def test_query_token_works_for_clients_that_cannot_set_headers(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.delenv("JARVIS_API_TOKEN", raising=False)
    from jarvis.server import auth

    allowed, _ = auth.check("/tasks", "10.0.0.9", {}, {"token": auth.get_token()})
    assert allowed is True


def test_health_stays_open_for_probes(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.server import auth

    allowed, _ = auth.check("/health", "203.0.113.7", {}, {})
    assert allowed is True


def test_require_token_removes_the_loopback_exemption(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.delenv("JARVIS_API_TOKEN", raising=False)
    monkeypatch.setenv("JARVIS_API_REQUIRE_TOKEN", "1")
    from jarvis.server import auth

    allowed, _ = auth.check("/tasks", "127.0.0.1", {}, {})
    assert allowed is False


def test_auth_can_be_switched_off(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_API_AUTH", "off")
    from jarvis.server import auth

    allowed, _ = auth.check("/tasks", "203.0.113.7", {}, {})
    assert allowed is True
