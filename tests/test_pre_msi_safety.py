from pathlib import Path


def test_adhd_state_is_support_mode_not_diagnosis(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.tools.adhd_state import ADHDStateTool, classify_support_state

    state = classify_support_state(energy=2, focus=2, stress=7, sleep_hours=4, mood="tired")
    assert state["mode"] in {"Low Battery", "Overwhelm SOS", "Scattered Guardrails"}
    assert 0 <= state["support_load"] <= 10

    result = ADHDStateTool().run(action="assess", energy=4, focus=3, stress=8, sleep_hours=5, mood="anxious")
    assert "not a medical ADHD diagnosis" in result
    assert (tmp_path / "adhd" / "state_log.json").exists()


def test_app_launcher_blocks_scripts_and_requires_confirmation(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "home"))
    from jarvis.tools.app_launcher import AppLauncherTool

    tool = AppLauncherTool()
    script = tmp_path / "unsafe.bat"
    script.write_text("echo nope")
    assert "Blocked" in tool.run(action="add", name="Unsafe", path=str(script))

    executable = tmp_path / "safeapp"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o755)
    added = tool.run(action="add", name="Safe", path=str(executable))
    assert "Added" in added

    # An unconfirmed launch must not start anything. The gate is no longer a
    # `confirm` tool parameter (the model writes those) — the request is parked
    # in jarvis/core/confirm.py until a human resolves it in the interface.
    from jarvis.core import confirm as confirm_gate

    confirm_gate.clear()
    response = tool.run(action="launch", app="Safe", confirm=False)
    assert "confirmation" in response.lower()
    assert len(confirm_gate.pending()) == 1, "launch should be parked, not run"
    confirm_gate.clear()


def test_connections_status_uses_local_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.tools.connection_tools import ConnectionStatusTool

    result = ConnectionStatusTool().run(action="status")
    assert "Google Calendar/Gmail" in result
    assert str(tmp_path / "calendar.json") in result
    assert "Read-only" in result
