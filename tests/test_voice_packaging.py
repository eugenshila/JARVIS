from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_msi_build_bundles_neural_voice_and_offline_whisper_assets():
    builder = (ROOT / "deploy/windows/build_msi.ps1").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/windows-msi.yml").read_text(encoding="utf-8")

    assert '"--add-data", "voice;voice"' in builder
    assert '"--add-data", "piper;piper"' in builder
    assert '"--add-data", "whisper-model;whisper-model"' in builder
    assert "jgkawell/jarvis" in workflow
    assert "piper_windows_amd64.zip" in workflow
    assert "Systran/faster-whisper-tiny.en" in builder


def test_dashboard_voice_preview_uses_local_api_before_legacy_audio():
    dashboard = (ROOT / "frontend/src/pages/JarvisDashboard.tsx").read_text(encoding="utf-8")
    assert "fetch('/hud/speak'" in dashboard
    assert "not the old static MP3 samples" in dashboard
