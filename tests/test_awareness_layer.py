"""Tier 3: capture budget & consent, wake-word discipline, echo suppression,
proactive gating, topic monitoring, and frozen/writable path handling."""

from __future__ import annotations

import time
from datetime import datetime

import pytest

# ── capture: consent and budget ───────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _capture_home(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("JARVIS_ALLOW_CAPTURE", raising=False)
    from jarvis.core import capture as capture_core

    capture_core.set_consent(None)
    yield
    capture_core.set_consent(None)


def test_capture_is_off_by_default():
    from jarvis.core import capture as capture_core

    assert capture_core.has_consent() is False
    with pytest.raises(capture_core.CaptureError) as excinfo:
        capture_core.capture_screen()
    assert "passwords" in str(excinfo.value), "refusal should say why, not just no"


def test_consent_can_be_granted_and_revoked():
    from jarvis.core import capture as capture_core

    capture_core.set_consent(True)
    assert capture_core.has_consent() is True
    capture_core.set_consent(False)
    assert capture_core.has_consent() is False


def test_env_var_grants_consent(monkeypatch):
    from jarvis.core import capture as capture_core

    monkeypatch.setenv("JARVIS_ALLOW_CAPTURE", "1")
    capture_core.set_consent(None)
    assert capture_core.has_consent() is True


def test_capture_is_downscaled_to_the_budget(tmp_path):
    pytest.importorskip("PIL")
    from PIL import Image

    from jarvis.core import capture as capture_core

    big = Image.new("RGB", (3840, 2160), (120, 30, 200))
    destination = tmp_path / "out.jpg"
    width, height, size = capture_core._downscale_and_save(big, destination)

    assert width <= capture_core.MAX_WIDTH and height <= capture_core.MAX_HEIGHT
    assert width == 640 and height == 360, "aspect ratio should be preserved"
    assert size < 200_000, "a 4K grab must not travel as megabytes"


def test_pruning_keeps_only_the_newest(tmp_path, monkeypatch):
    from jarvis.core import capture as capture_core
    from jarvis.core import paths

    captures = tmp_path / "caps"
    captures.mkdir()
    monkeypatch.setattr(paths, "captures_dir", lambda: captures)
    for i in range(8):
        f = captures / f"screen-{i}.jpg"
        f.write_bytes(b"x")
        import os

        os.utime(f, (i, i))
    removed = capture_core.prune(keep=3)
    assert removed == 5
    assert len(list(captures.glob("*.jpg"))) == 3


def test_capture_tool_reports_refusal_rather_than_raising():
    from jarvis.tools.capture_tools import ScreenCaptureTool

    out = ScreenCaptureTool().run(question="what is this")
    assert out.startswith("Error:")
    assert "JARVIS_ALLOW_CAPTURE" in out


def test_capture_tools_require_approval():
    from jarvis.tools.capture_tools import CameraCaptureTool, ScreenCaptureTool

    assert ScreenCaptureTool.spec.requires_approval is True
    assert CameraCaptureTool.spec.requires_approval is True


def test_capture_settings_tool_toggles_consent():
    from jarvis.core import capture as capture_core
    from jarvis.tools.capture_tools import CaptureSettingsTool

    tool = CaptureSettingsTool()
    tool.run(action="enable")
    assert capture_core.has_consent() is True
    assert "cannot see" in tool.run(action="disable")
    assert capture_core.has_consent() is False


# ── wake word: the two disciplines ────────────────────────────────────────────


def test_openwakeword_is_not_imported_at_module_load():
    import sys

    sys.modules.pop("openwakeword", None)
    import importlib

    import jarvis.speech.wake as wake

    importlib.reload(wake)
    assert "openwakeword" not in sys.modules, "the dep must cost nothing when unused"


def test_feed_never_blocks_and_drops_oldest_when_full():
    from jarvis.speech.wake import QUEUE_BLOCKS, WakeWordListener

    listener = WakeWordListener(on_wake=lambda name, score: None)
    started = time.monotonic()
    for i in range(QUEUE_BLOCKS * 3):
        listener.feed([i])
    elapsed = time.monotonic() - started

    assert elapsed < 0.5, "the audio callback must never wait"
    assert listener.dropped_blocks > 0
    assert listener._queue.qsize() <= QUEUE_BLOCKS
    # The newest block survived; the oldest were discarded.
    assert listener._queue.queue[-1] == [QUEUE_BLOCKS * 3 - 1]


def test_start_reports_missing_dependency_without_raising():
    from jarvis.speech.wake import WakeWordListener

    listener = WakeWordListener(on_wake=lambda n, s: None)
    if listener.start():
        listener.stop()
        pytest.skip("openwakeword is installed in this environment")
    assert "openwakeword" in listener.error
    assert listener.running is False


def test_detection_fires_the_callback_on_the_worker_thread():
    from jarvis.speech.wake import WakeWordListener

    heard = []
    listener = WakeWordListener(on_wake=lambda name, score: heard.append((name, score)))

    class _Model:
        def predict(self, block):
            return {"hey_jarvis": 0.9}

    listener._model = _Model()
    import threading

    listener._stop.clear()
    listener._thread = threading.Thread(target=listener._run, daemon=True)
    listener._thread.start()
    listener.feed([0.0])
    time.sleep(0.4)
    listener.stop()

    assert heard and heard[0][0] == "hey_jarvis"
    assert listener.detections == 1


def test_a_throwing_callback_does_not_kill_the_listener():
    import threading

    from jarvis.speech.wake import WakeWordListener

    listener = WakeWordListener(on_wake=lambda n, s: 1 / 0)

    class _Model:
        def predict(self, block):
            return {"hey_jarvis": 0.99}

    listener._model = _Model()
    listener._stop.clear()
    listener._thread = threading.Thread(target=listener._run, daemon=True)
    listener._thread.start()
    listener.feed([0.0])
    time.sleep(0.3)
    alive = listener.running
    listener.stop()
    assert alive is True


# ── echo suppression ──────────────────────────────────────────────────────────

np = pytest.importorskip("numpy")


def _tone(freq: float, seconds: float = 0.1, rate: int = 16000, amp: float = 0.5):
    t = np.arange(int(rate * seconds)) / rate
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def test_our_own_voice_coming_back_is_recognised_as_echo():
    from jarvis.speech.echo import EchoSuppressor

    suppressor = EchoSuppressor()
    output = _tone(300, amp=0.5)
    suppressor.note_output(output)
    # The mic hears the same sound, attenuated by the room.
    verdict = suppressor.classify(output * 0.4)
    assert verdict.is_echo is True


def test_a_different_voice_survives_cancellation():
    from jarvis.speech.echo import EchoSuppressor

    suppressor = EchoSuppressor()
    suppressor.note_output(_tone(300, amp=0.5))
    # A second speaker: energy in bands where ours was weak.
    verdict = suppressor.classify(_tone(2200, amp=0.5))
    assert verdict.is_echo is False
    assert "survives" in verdict.reason


def test_a_loud_interruption_is_not_mistaken_for_echo():
    """The case a plain loudness threshold gets wrong: same level, different voice."""
    from jarvis.speech.echo import EchoSuppressor

    suppressor = EchoSuppressor()
    suppressor.note_output(_tone(300, amp=0.5))
    assert suppressor.classify(_tone(2500, amp=0.5)).is_echo is False


def test_nothing_played_recently_means_never_echo():
    from jarvis.speech.echo import EchoSuppressor

    suppressor = EchoSuppressor()
    assert suppressor.classify(_tone(300), now=time.monotonic() + 30).is_echo is False


def test_echo_gain_calibrates_itself_to_the_room():
    from jarvis.speech.echo import EchoSuppressor

    suppressor = EchoSuppressor()
    assert suppressor.status()["calibrated"] is False
    output = _tone(300, amp=0.5)
    for _ in range(3):
        suppressor.note_output(output)
        suppressor.classify(output * 0.3)
    assert suppressor.status()["calibrated"] is True, "should learn the room, not need tuning"


def test_should_listen_is_the_inverse_of_classify():
    from jarvis.speech.echo import EchoSuppressor

    suppressor = EchoSuppressor()
    suppressor.note_output(_tone(300, amp=0.5))
    assert suppressor.should_listen(_tone(2200, amp=0.5)) is True


# ── proactive gating ──────────────────────────────────────────────────────────


def _engine(enabled=True, **kwargs):
    from jarvis.agents.proactive import ProactiveConfig, ProactiveEngine

    return ProactiveEngine(config=ProactiveConfig(enabled=enabled, **kwargs))


_NOON = datetime(2026, 3, 2, 12, 0)


def test_proactive_is_off_by_default():
    from jarvis.agents.proactive import ProactiveEngine

    allowed, why = ProactiveEngine().should_speak(0.0, now=10_000, wall_clock=_NOON)
    assert allowed is False and "off" in why


def test_silence_gate_blocks_an_active_user():
    engine = _engine()
    now = 10_000.0
    allowed, why = engine.should_speak(now - 30, now=now, wall_clock=_NOON)
    assert allowed is False and "active" in why


def test_speaks_after_long_silence():
    engine = _engine()
    now = 10_000.0
    allowed, _ = engine.should_speak(now - 1000, now=now, wall_clock=_NOON)
    assert allowed is True


def test_cooldown_blocks_a_second_message():
    engine = _engine()
    now = 10_000.0
    engine.mark_spoken("hello", now=now)
    allowed, why = engine.should_speak(now - 1000, now=now + 60, wall_clock=_NOON)
    assert allowed is False and "cooldown" in why


def test_quiet_hours_are_respected():
    engine = _engine()
    now = 10_000.0
    midnight = datetime(2026, 3, 2, 2, 30)
    allowed, why = engine.should_speak(now - 5000, now=now, wall_clock=midnight)
    assert allowed is False and "quiet hours" in why


def test_busy_assistant_does_not_interrupt_itself():
    engine = _engine()
    now = 10_000.0
    allowed, why = engine.should_speak(now - 5000, now=now, wall_clock=_NOON, busy=True)
    assert allowed is False and "busy" in why


def test_daily_limit_is_enforced():
    engine = _engine(max_per_day=2, cooldown=0)
    now = 10_000.0
    for _ in range(2):
        engine.mark_spoken("x", now=now, wall_clock=_NOON)
    allowed, why = engine.should_speak(now - 5000, now=now + 100_000, wall_clock=_NOON)
    assert allowed is False and "daily limit" in why


def test_focus_rotates_so_nudges_differ():
    from jarvis.agents.proactive import FOCUS_AREAS

    engine = _engine()
    seen = []
    for _ in range(len(FOCUS_AREAS)):
        seen.append(engine.focus)
        engine.mark_spoken("m")
    assert len(set(seen)) == len(FOCUS_AREAS)


def test_repeated_message_is_detected():
    engine = _engine()
    engine.mark_spoken("You have three things due today.")
    assert engine.is_repeat("you   have THREE things due today.") is True
    assert engine.is_repeat("Something else entirely.") is False


def test_model_can_decline_to_say_anything():
    from jarvis.agents.proactive import ProactiveEngine

    assert ProactiveEngine.is_declined("NOTHING") is True
    assert ProactiveEngine.is_declined("  nothing. ") is True
    assert ProactiveEngine.is_declined("Your build finished.") is False


def test_prompt_includes_focus_and_declination_route():
    engine = _engine()
    prompt = engine.build_prompt(profile_text="name: Eugene", monitors=["fintech rules"])
    assert engine.focus in prompt
    assert "NOTHING" in prompt
    assert "Eugene" in prompt and "fintech rules" in prompt


# ── topic monitor ─────────────────────────────────────────────────────────────


def test_crypto_topics_are_refused_in_several_spellings():
    from jarvis.tools.monitor_tools import TopicMonitorTool, is_blocked

    for topic in ["bitcoin price", "KRIPTO haberleri", "best altcoin", "day trading tips"]:
        assert is_blocked(topic), topic
    out = TopicMonitorTool().run(action="add", topic="bitcoin price")
    assert "will not monitor" in out


def test_a_normal_topic_is_accepted_and_listed():
    from jarvis.tools.monitor_tools import TopicMonitorTool

    tool = TopicMonitorTool()
    assert "Following" in tool.run(action="add", topic="Kenyan fintech licensing")
    assert "Kenyan fintech licensing" in tool.run(action="list")


def test_topics_can_be_removed():
    from jarvis.tools.monitor_tools import TopicMonitorTool

    tool = TopicMonitorTool()
    tool.run(action="add", topic="rainfall data")
    assert "Stopped following" in tool.run(action="remove", topic="rainfall data")
    assert "not following any" in tool.run(action="list")


def test_topic_count_is_capped():
    from jarvis.tools.monitor_tools import MAX_TOPICS, TopicMonitorTool

    tool = TopicMonitorTool()
    for i in range(MAX_TOPICS):
        tool.run(action="add", topic=f"topic number {i}")
    assert "the limit" in tool.run(action="add", topic="one too many")


def test_headlines_are_deduplicated_by_hash(monkeypatch):
    import jarvis.tools.monitor_tools as mt

    tool = mt.TopicMonitorTool()
    tool.run(action="add", topic="solar policy")
    monkeypatch.setattr(mt, "_search", lambda topic, limit=5: ["Solar tariffs cut by a third"])

    first = tool.run(action="check", topic="solar policy")
    assert "Solar tariffs cut" in first

    # Same story, different whitespace/case — must not be reported twice.
    monkeypatch.setattr(mt, "_search", lambda topic, limit=5: ["solar   tariffs CUT by a third"])
    second = tool.run(action="check", topic="solar policy")
    assert "Nothing new" in second


def test_check_respects_the_daily_interval(monkeypatch):
    import jarvis.tools.monitor_tools as mt

    tool = mt.TopicMonitorTool()
    tool.run(action="add", topic="rail expansion")
    monkeypatch.setattr(mt, "_search", lambda topic, limit=5: ["A new line opens"])
    tool.run(action="check")
    assert mt.due_topics() == [], "a freshly checked topic is not due again"


def test_nothing_is_monitored_implicitly():
    from jarvis.tools.monitor_tools import load_monitors

    assert load_monitors() == {}, "monitors must only ever be added explicitly"


# ── paths: frozen builds and writable directories ─────────────────────────────


def test_base_dir_follows_the_executable_when_frozen(monkeypatch, tmp_path):
    import jarvis.core.paths as paths

    fake_exe = tmp_path / "dist" / "jarvis.exe"
    fake_exe.parent.mkdir(parents=True)
    fake_exe.write_text("", encoding="utf-8")
    monkeypatch.setattr("sys.frozen", True, raising=False)
    monkeypatch.setattr("sys.executable", str(fake_exe))

    assert paths.is_frozen() is True
    assert paths.base_dir() == fake_exe.parent


def test_resource_dir_uses_meipass_when_present(monkeypatch, tmp_path):
    import jarvis.core.paths as paths

    monkeypatch.setattr("sys._MEIPASS", str(tmp_path), raising=False)
    assert paths.resource_dir() == tmp_path


def test_source_checkout_resolves_the_repo_root():
    import jarvis.core.paths as paths

    assert (paths.base_dir() / "src" / "jarvis").is_dir()


def test_uploads_falls_through_to_a_writable_directory(monkeypatch, tmp_path):
    import jarvis.core.paths as paths

    good = tmp_path / "third-choice"
    monkeypatch.setattr(
        paths, "_writable", lambda p: str(p) == str(good)
    )
    assert paths.first_writable([tmp_path / "a", tmp_path / "b", good]) == good


def test_uploads_uses_a_temp_dir_when_nothing_is_writable(monkeypatch, tmp_path):
    import jarvis.core.paths as paths

    monkeypatch.setattr(paths, "_writable", lambda p: False)
    result = paths.first_writable([tmp_path / "a"], fallback_name="jarvis-test")
    assert result.exists()


def test_writability_is_tested_not_assumed(tmp_path):
    import jarvis.core.paths as paths

    assert paths._writable(tmp_path / "new") is True
    assert not list((tmp_path / "new").glob(".jarvis_write_test")), "probe must be cleaned up"


def test_uploads_dir_honours_the_override(monkeypatch, tmp_path):
    import jarvis.core.paths as paths

    target = tmp_path / "custom uploads"
    monkeypatch.setenv("JARVIS_UPLOADS_DIR", str(target))
    assert paths.uploads_dir() == target


def test_describe_reports_the_environment():
    from jarvis.core.paths import describe

    info = describe()
    assert set(info) >= {"frozen", "base_dir", "home", "uploads", "captures"}
