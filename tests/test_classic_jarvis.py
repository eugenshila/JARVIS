"""Tests for the ported classic assistant (jarvis.classic).

These deliberately avoid the network, the microphone and the real power
commands: what is worth testing is that the intent ladder routes correctly,
that follow-up questions resume, and that nothing irreversible can happen
without a human.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from jarvis.classic import skills
from jarvis.classic.router import COMMANDS, ClassicRouter, normalize


@pytest.fixture()
def router(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_NO_BROWSER", "1")
    return ClassicRouter()


# ── normalisation ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Jarvis, tell me a joke!", "tell me a joke"),
        ("HEY JARVIS what time is it?", "what time is it"),
        ("  play   some  music  ", "play some music"),
        # The wake word is only stripped from the front — upstream's bare
        # replace() also ate it mid-sentence.
        ("who is jarvis", "who is jarvis"),
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


# ── intent routing ───────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "command,intent",
    [
        ("hello", "greet"),
        ("are you there", "check"),
        ("what time is it", "time"),
        ("tell me a joke", "joke"),
        ("help", "help"),
        ("ram usage", "ram"),
        ("battery status", "battery"),
        ("goodbye", "quit"),
    ],
)
def test_routes_to_expected_intent(router, command, intent):
    assert router.handle(command).intent == intent


def test_unknown_command_is_polite_and_suggests(router, monkeypatch):
    monkeypatch.delenv("WOLFRAM_APP_ID", raising=False)
    reply = router.handle("please reticulate the splines")
    assert reply.intent == "unknown"
    assert reply.data["suggestions"]


def test_every_listed_command_example_is_understood(router, monkeypatch):
    """The sidebar in the HUD lists COMMANDS; a chip that answers 'I cannot
    understand you' would be a broken button."""
    monkeypatch.delenv("WOLFRAM_APP_ID", raising=False)
    monkeypatch.setattr(skills, "weather", lambda city: f"Weather in {city}.")
    monkeypatch.setattr(skills, "translate", lambda text, dest="en", src="auto": "ok")
    monkeypatch.setattr(skills, "screenshot", lambda name="": "captured")
    monkeypatch.setattr(skills, "play_music", lambda: "playing")
    for item in COMMANDS:
        reply = ClassicRouter().handle(item["example"])
        assert reply.intent != "unknown", item["example"]


# ── follow-up questions ──────────────────────────────────────────────────────

def test_weather_asks_for_a_city_then_uses_the_answer(router, monkeypatch):
    monkeypatch.setattr(skills, "weather", lambda city: f"Weather status in {city} is fine.")
    first = router.handle("check weather")
    assert first.expects == "weather"
    second = router.handle("Reykjavik")
    assert second.intent == "weather"
    assert "reykjavik" in second.speech.lower()


def test_inline_city_skips_the_question(router, monkeypatch):
    monkeypatch.setattr(skills, "weather", lambda city: f"[{city}]")
    reply = router.handle("weather in oslo")
    assert reply.expects is None
    assert reply.data["city"] == "oslo"


def test_cpu_follow_up_asks_about_cores(router, monkeypatch):
    seen = {}
    monkeypatch.setattr(skills, "cpu_usage", lambda per_core=False: seen.setdefault("per_core", per_core) or "ok")
    assert router.handle("cpu usage").expects == "cpu"
    router.handle("yes")
    assert seen["per_core"] is True


# ── notes round-trip ─────────────────────────────────────────────────────────

def test_note_is_written_and_listed(router, tmp_path):
    reply = router.handle("make a note buy a new arc reactor")
    assert reply.intent == "note"
    files = list((tmp_path / "notes").glob("*-note.txt"))
    assert len(files) == 1
    assert "arc reactor" in files[0].read_text(encoding="utf-8")
    assert "arc reactor" in router.handle("read my notes").speech


def test_note_without_text_asks_first(router):
    assert router.handle("make a note").expects == "note"


# ── safety: nothing irreversible happens on a transcript alone ───────────────

def test_shutdown_never_executes_directly(router, monkeypatch):
    def explode(*args, **kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("classic router ran a power command without a human")

    monkeypatch.setattr(skills, "run_power_command", explode)
    monkeypatch.setattr(skills.subprocess, "Popen", explode)
    reply = router.handle("shut down")
    assert reply.intent == "shutdown"
    assert reply.confirm_token or reply.expects == "shutdown"
    assert "shutdown" in " ".join(reply.data["command"]).lower()


def test_shutdown_confirmation_token_is_resolvable_by_a_human(router):
    from jarvis.core import confirm as confirm_gate

    reply = router.handle("shut down")
    assert reply.confirm_token
    assert any(p["token"] == reply.confirm_token for p in confirm_gate.pending())
    assert confirm_gate.cancel(reply.confirm_token) is True


def test_power_command_is_platform_aware(monkeypatch):
    monkeypatch.setattr(skills.platform, "system", lambda: "Windows")
    assert skills.power_command("shutdown")[:2] == ["shutdown", "/s"]
    assert skills.power_command("restart")[:2] == ["shutdown", "/r"]


# ── skills that must work with zero optional dependencies ────────────────────

def test_joke_always_returns_something():
    assert skills.joke().strip()


def test_greeting_matches_time_of_day():
    assert "morning" in skills.greet(datetime(2026, 1, 1, 9, 5)).lower()
    assert "afternoon" in skills.greet(datetime(2026, 1, 1, 14, 5)).lower()
    assert "evening" in skills.greet(datetime(2026, 1, 1, 21, 5)).lower()


def test_hardware_skills_degrade_instead_of_raising(monkeypatch):
    monkeypatch.setattr(skills, "_psutil", lambda: None)
    for text in (skills.ram_usage(), skills.battery_status(), skills.cpu_usage()):
        assert "psutil" in text


def test_ocr_reports_a_missing_file(tmp_path):
    assert "no image" in skills.extract_text(str(tmp_path / "nope.png")).lower()


def test_search_builds_the_expected_urls(monkeypatch):
    monkeypatch.setenv("JARVIS_NO_BROWSER", "1")
    url, _ = skills.search("youtube", "arc reactor")
    assert url == "https://www.youtube.com/results?search_query=arc%20reactor"


def test_wolfram_is_skipped_without_a_key(monkeypatch):
    monkeypatch.delenv("WOLFRAM_APP_ID", raising=False)
    assert skills.wolfram("2+2") is None


# ── the tool wrapper the agents see ──────────────────────────────────────────

def test_classic_tool_is_discoverable_and_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    from jarvis.tools.registry import get_tool, list_tools

    assert "classic_command" in list_tools()
    tool = get_tool("classic_command")
    assert tool is not None
    assert tool.run(command="what time is it").strip()
    assert "weather" in get_tool("classic_commands").run()
