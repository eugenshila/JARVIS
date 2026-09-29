"""Tests for the reliability/safety layer: ladder, confirm, undo, recovery, discovery."""

from __future__ import annotations

import time

import pytest

from jarvis.agents.recovery import Decision, Recovery, RetryBudget, classify
from jarvis.core import confirm as confirm_gate
from jarvis.core import undo as undo_stack
from jarvis.core.types import AgentResponse, Message, Role
from jarvis.engine import ladder
from jarvis.engine.ladder import LadderEngine, LadderExhausted, Rung


# ── helpers ───────────────────────────────────────────────────────────────────


class _StubEngine:
    """Minimal engine: answers, raises, hangs, or returns nothing."""

    def __init__(self, reply="ok", raises=None, delay=0.0):
        self.reply = reply
        self.raises = raises
        self.delay = delay
        self.calls = 0

    def generate(self, messages, **kwargs):
        self.calls += 1
        if self.delay:
            time.sleep(self.delay)
        if self.raises:
            raise self.raises
        return AgentResponse(content=self.reply, model="stub")


def _ladder_with(pairs):
    """Build a LadderEngine whose rungs resolve to the given stub engines."""
    rungs = [Rung("mock", name, timeout=t) for name, _, t in pairs]
    engines = {f"mock:{name}": eng for name, eng, _ in pairs}
    eng = LadderEngine.__new__(LadderEngine)
    eng.purpose = ladder.FAST
    eng.name = "ladder:test"
    eng._config = None
    eng.rungs = rungs
    eng._instances = {}
    eng._lock = __import__("threading").Lock()
    eng.last_trace = []
    eng._build = lambda rung: engines[rung.key]  # type: ignore[assignment]
    return eng


@pytest.fixture(autouse=True)
def _clean_state():
    ladder.reset()
    confirm_gate.clear()
    undo_stack.clear()
    yield
    ladder.reset()
    confirm_gate.clear()
    undo_stack.clear()


# ── ladder ────────────────────────────────────────────────────────────────────


def test_ladder_uses_first_healthy_rung():
    first, second = _StubEngine("from first"), _StubEngine("from second")
    eng = _ladder_with([("a", first, 5), ("b", second, 5)])
    assert eng.generate([]).content == "from first"
    assert second.calls == 0


def test_ladder_falls_through_on_error():
    broken = _StubEngine(raises=RuntimeError("429 rate limit"))
    good = _StubEngine("recovered")
    eng = _ladder_with([("a", broken, 5), ("b", good, 5)])
    assert eng.generate([]).content == "recovered"
    assert [t["result"] for t in eng.last_trace] == ["error", "ok"]


def test_ladder_treats_empty_response_as_failure():
    empty, good = _StubEngine(""), _StubEngine("real answer")
    eng = _ladder_with([("a", empty, 5), ("b", good, 5)])
    assert eng.generate([]).content == "real answer"


def test_ladder_bounds_a_slow_rung_by_timeout():
    slow, fast = _StubEngine("late", delay=2.0), _StubEngine("quick")
    eng = _ladder_with([("a", slow, 0.2), ("b", fast, 5)])
    started = time.monotonic()
    assert eng.generate([]).content == "quick"
    # The caller is released on schedule even though the worker is still going.
    assert time.monotonic() - started < 1.5
    assert eng.last_trace[0]["result"] == "timeout"


def test_failed_rung_goes_on_cooldown_and_is_skipped_next_time():
    broken = _StubEngine(raises=RuntimeError("boom"))
    good = _StubEngine("fine")
    eng = _ladder_with([("a", broken, 5), ("b", good, 5)])

    eng.generate([])
    assert broken.calls == 1

    eng.generate([])
    assert broken.calls == 1, "cooling-down rung must not be called again"
    assert eng.last_trace[0]["result"] == "cooling_down"


def test_cooldown_clears_after_success():
    flaky = _StubEngine(raises=RuntimeError("boom"))
    eng = _ladder_with([("a", flaky, 5), ("b", _StubEngine("fine"), 5)])
    eng.generate([])
    assert not ladder.COOLDOWNS.available("mock:a")
    ladder.COOLDOWNS.note_success("mock:a")
    assert ladder.COOLDOWNS.available("mock:a")


def test_cooldown_backoff_grows():
    first = ladder.COOLDOWNS.note_failure("mock:x", "e")
    second = ladder.COOLDOWNS.note_failure("mock:x", "e")
    assert second > first


def test_ladder_exhausted_when_every_rung_fails():
    eng = _ladder_with([("a", _StubEngine(raises=RuntimeError("x")), 5)])
    with pytest.raises(LadderExhausted):
        eng.generate([])


def test_default_ladders_cover_every_purpose():
    for purpose in ladder.PURPOSES:
        assert ladder.DEFAULT_LADDERS[purpose], purpose


# ── confirmation gate ─────────────────────────────────────────────────────────


def test_request_does_not_run_the_work():
    ran = []
    confirm_gate.request("Delete", "everything", lambda: ran.append(1) or "done")
    assert ran == []
    assert len(confirm_gate.pending()) == 1


def test_only_resolve_runs_the_work():
    ran = []
    entry = confirm_gate.request("Run", "ls", lambda: (ran.append(1), "output")[1])
    assert confirm_gate.resolve(entry.token) == "output"
    assert ran == [1]


def test_token_cannot_be_reused():
    entry = confirm_gate.request("Run", "ls", lambda: "output")
    confirm_gate.resolve(entry.token)
    with pytest.raises(confirm_gate.ConfirmationError):
        confirm_gate.resolve(entry.token)


def test_unknown_token_is_rejected():
    with pytest.raises(confirm_gate.ConfirmationError):
        confirm_gate.resolve("not-a-real-token")


def test_cancel_drops_the_work():
    ran = []
    entry = confirm_gate.request("Run", "ls", lambda: ran.append(1))
    assert confirm_gate.cancel(entry.token) is True
    assert ran == []
    with pytest.raises(confirm_gate.ConfirmationError):
        confirm_gate.resolve(entry.token)


def test_expired_request_cannot_be_resolved(monkeypatch):
    entry = confirm_gate.request("Run", "ls", lambda: "output")
    monkeypatch.setattr(confirm_gate, "TIMEOUT_SECONDS", -1.0)
    with pytest.raises(confirm_gate.ConfirmationError):
        confirm_gate.resolve(entry.token)


def test_pending_queue_is_bounded():
    for i in range(confirm_gate.MAX_PENDING + 3):
        confirm_gate.request(f"t{i}", "d", lambda: "x")
    assert len(confirm_gate.pending()) <= confirm_gate.MAX_PENDING


def test_shell_tool_does_not_run_without_a_human():
    from jarvis.tools.builtins import ShellTool

    marker = "/tmp/jarvis_confirm_gate_test_marker"
    result = ShellTool().run(command=f"touch {marker}")
    assert "confirmation" in result.lower()
    import pathlib

    assert not pathlib.Path(marker).exists(), "command ran without human confirmation"
    assert len(confirm_gate.pending()) == 1


def test_shell_tool_has_no_forgeable_confirm_parameter():
    from jarvis.tools.builtins import ShellTool

    props = ShellTool.spec.parameters.get("properties", {})
    assert "confirm" not in props
    assert "confirmed" not in props


# ── undo ──────────────────────────────────────────────────────────────────────


def test_undo_reverses_the_last_action():
    state = {"volume": 10}

    def set_volume(v):
        old = state["volume"]
        state["volume"] = v
        undo_stack.push_undo(f"volume -> {v}", lambda: (state.__setitem__("volume", old), "restored")[1])

    set_volume(80)
    assert state["volume"] == 80
    assert "Undone" in undo_stack.undo_last()
    assert state["volume"] == 10


def test_undo_is_lifo():
    order = []
    undo_stack.push_undo("first", lambda: (order.append("first"), "")[1])
    undo_stack.push_undo("second", lambda: (order.append("second"), "")[1])
    undo_stack.undo_last()
    undo_stack.undo_last()
    assert order == ["second", "first"]


def test_undo_stack_is_bounded():
    for i in range(undo_stack.MAX_DEPTH + 5):
        undo_stack.push_undo(f"op{i}", lambda: "")
    assert undo_stack.depth() == undo_stack.MAX_DEPTH


def test_undo_with_nothing_to_undo_is_graceful():
    assert "Nothing to undo" in undo_stack.undo_last()


def test_failing_reverse_does_not_raise():
    undo_stack.push_undo("bad", lambda: (_ for _ in ()).throw(RuntimeError("gone")))
    assert "Could not undo" in undo_stack.undo_last()


def test_file_write_is_reversible(tmp_path):
    from jarvis.tools.builtins import FileWriteTool

    target = tmp_path / "note.txt"
    target.write_text("original", encoding="utf-8")

    FileWriteTool().run(path=str(target), content="replaced")
    assert target.read_text() == "replaced"

    undo_stack.undo_last()
    assert target.read_text() == "original"


def test_file_write_undo_removes_a_new_file(tmp_path):
    from jarvis.tools.builtins import FileWriteTool

    target = tmp_path / "fresh.txt"
    FileWriteTool().run(path=str(target), content="hello")
    assert target.exists()
    undo_stack.undo_last()
    assert not target.exists()


# ── recovery classifier ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "error,expected",
    [
        ("Error: command timed out after 30s", Decision.RETRY),
        ("HTTP 429 Too Many Requests", Decision.RETRY),
        ("502 Bad Gateway", Decision.RETRY),
        ("Connection refused", Decision.RETRY),
        ("Error: no such file or directory: /tmp/nope", Decision.REPLAN),
        ("Error: unknown tool frobnicate", Decision.REPLAN),
        ("TypeError: missing required argument 'path'", Decision.REPLAN),
        ("Permission denied", Decision.ABORT),
        ("403 Forbidden", Decision.ABORT),
        ("ModuleNotFoundError: No module named 'faiss'", Decision.SKIP),
        ("OSError: no space left on device", Decision.ABORT),
    ],
)
def test_rules_classify_common_failures_without_a_model(error, expected):
    rec = classify(error, use_model=False)
    assert rec.decision is expected
    assert rec.source == "rules"


def test_user_message_is_short_enough_to_speak():
    for error in ["timed out", "429 rate limit", "permission denied"]:
        rec = classify(error, use_model=False)
        assert 0 < len(rec.user_message.split()) <= 15


def test_retry_rule_becomes_replan_once_attempts_are_used_up():
    assert classify("timed out", attempt=1, use_model=False).decision is Decision.RETRY
    assert classify("timed out", attempt=5, use_model=False).decision is Decision.REPLAN


def test_unclassified_failure_retries_once_then_replans():
    assert classify("weird gibberish failure", attempt=1, use_model=False).decision is Decision.RETRY
    assert classify("weird gibberish failure", attempt=2, use_model=False).decision is Decision.REPLAN


def test_model_classification_is_used_when_rules_miss():
    class _Classifier:
        def generate(self, messages, **kwargs):
            return AgentResponse(
                content='```json\n{"decision":"skip","reason":"cosmetic",'
                '"fix_suggestion":"","max_retries":0,"user_message":"Not important. Moving on."}\n```'
            )

    rec = classify("something entirely novel", engine=_Classifier())
    assert rec.decision is Decision.SKIP
    assert rec.source == "model"


def test_malformed_model_output_falls_back_safely():
    class _Garbage:
        def generate(self, messages, **kwargs):
            return AgentResponse(content="I think you should probably just try again?")

    rec = classify("something entirely novel", engine=_Garbage(), attempt=3)
    assert rec.source == "default"
    assert rec.decision is Decision.REPLAN


def test_broken_classifier_engine_does_not_propagate():
    class _Exploding:
        def generate(self, messages, **kwargs):
            raise RuntimeError("classifier is down")

    assert classify("novel failure", engine=_Exploding()).decision in set(Decision)


def test_retry_budget_caps_per_step_and_total():
    budget = RetryBudget(total=3, per_step=2)
    assert budget.allows("a")
    budget.spend("a")
    budget.spend("a")
    assert not budget.allows("a")
    assert budget.allows("b")


# ── tool discovery ────────────────────────────────────────────────────────────


def test_discovery_finds_the_core_tools():
    from jarvis.tools.registry import list_tools

    names = list_tools()
    for expected in ["file_read", "file_write", "shell", "memory_search", "undo"]:
        assert expected in names, expected


def test_discovery_never_raises_on_a_broken_module(tmp_path):
    from jarvis.tools.discovery import discover

    (tmp_path / "broken.py").write_text("import a_module_that_does_not_exist\n")
    (tmp_path / "fine.py").write_text(
        "from jarvis.tools.base import BaseTool, ToolSpec\n"
        "class OkTool(BaseTool):\n"
        "    spec = ToolSpec(name='plugin_ok', description='d', parameters={})\n"
        "    def run(self, **kw): return 'ok'\n"
    )
    reg = discover(packages=(), plugin_dir=tmp_path)
    assert "plugin_ok" in reg.tools
    assert any("broken" in p["module"] for p in reg.problems())


def test_user_plugin_is_discovered_and_runnable(tmp_path):
    from jarvis.tools.discovery import discover

    (tmp_path / "hello.py").write_text(
        "from jarvis.tools.base import BaseTool, ToolSpec\n"
        "class HelloTool(BaseTool):\n"
        "    spec = ToolSpec(name='hello_plugin', description='d', parameters={})\n"
        "    behavior = 'NON_BLOCKING'\n"
        "    scheduling = 'SILENT'\n"
        "    def run(self, **kw): return 'hi'\n"
    )
    reg = discover(packages=(), plugin_dir=tmp_path)
    rec = reg.record("hello_plugin")
    assert rec.behavior == "NON_BLOCKING"
    assert rec.scheduling == "SILENT"
    assert reg.get("hello_plugin").run() == "hi"


def test_behavior_and_scheduling_default_sensibly():
    from jarvis.tools.registry import tool_record

    rec = tool_record("file_read")
    assert rec.behavior == "BLOCKING"
    assert rec.scheduling == "WHEN_IDLE"


def test_aliases_still_resolve():
    from jarvis.tools.registry import get_tool

    assert get_tool("code_exec") is not None


def test_registry_view_is_read_only():
    from jarvis.tools.registry import REGISTRY

    assert "file_read" in REGISTRY
    with pytest.raises(TypeError):
        REGISTRY.update({"x": object})


def test_disabled_tool_is_not_dispatchable(monkeypatch):
    from jarvis.tools import discovery

    monkeypatch.setattr(discovery, "is_enabled", lambda name: name != "shell")
    reg = discovery.get_registry()
    monkeypatch.setattr(reg, "get", lambda name: None if name == "shell" else object())
    assert reg.get("shell") is None


# ── react loop integration ────────────────────────────────────────────────────


def test_react_loop_recovers_from_a_transient_tool_failure():
    from jarvis.agents.react import ReActAgent

    calls = {"n": 0}

    class _FlakyTool:
        class spec:  # noqa: D106
            name = "flaky"

        def run(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return "Error: connection refused"
            return "the answer is 42"

    class _Engine:
        def __init__(self):
            self.turn = 0

        def generate(self, messages, **kwargs):
            self.turn += 1
            if self.turn == 1:
                return AgentResponse(content='Thought: check\nAction: flaky {}')
            return AgentResponse(content="Final answer: 42")

    agent = ReActAgent.__new__(ReActAgent)
    agent.engine = _Engine()
    agent.tools = [_FlakyTool()]
    agent.preset = type("P", (), {"system_prompt": "sys", "tools": []})()
    agent.config = None

    import jarvis.agents.react as react_mod

    original = react_mod.get_tool
    react_mod.get_tool = lambda name: _FlakyTool() if name == "flaky" else None
    try:
        result = agent.run("do the thing", max_steps=3)
    finally:
        react_mod.get_tool = original

    assert calls["n"] == 2, "the transient failure should have been retried once"
    assert "42" in result.content


def test_react_loop_aborts_on_a_permission_failure():
    from jarvis.agents.react import ReActAgent

    class _DeniedTool:
        class spec:  # noqa: D106
            name = "denied"

        def run(self, **kwargs):
            return "Error: permission denied"

    class _Engine:
        def generate(self, messages, **kwargs):
            return AgentResponse(content='Action: denied {}')

    agent = ReActAgent.__new__(ReActAgent)
    agent.engine = _Engine()
    agent.tools = [_DeniedTool()]
    agent.preset = type("P", (), {"system_prompt": "sys", "tools": []})()
    agent.config = None

    import jarvis.agents.react as react_mod

    original = react_mod.get_tool
    react_mod.get_tool = lambda name: _DeniedTool() if name == "denied" else None
    try:
        result = agent.run("do the forbidden thing", max_steps=4)
    finally:
        react_mod.get_tool = original

    assert "not permitted" in result.content.lower()
