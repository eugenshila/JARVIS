from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_packaged_uvicorn_entrypoints_disable_default_formatter_config():
    """Frozen Windows launchers must not initialize Uvicorn's default formatter."""
    entrypoints = (
        ROOT / "src/jarvis/cli/desktop_gui.py",
        ROOT / "src/jarvis/startup/windows_boot.py",
        ROOT / "src/jarvis/cli/hud_launcher.py",
        ROOT / "src/jarvis/cli/main.py",
        ROOT / "src/jarvis/server/api.py",
    )

    for entrypoint in entrypoints:
        source = entrypoint.read_text(encoding="utf-8")
        assert "log_config=None" in source, f"Uvicorn formatter guard missing in {entrypoint}"


def test_msi_smoke_test_launches_frozen_desktop_executable():
    """CI must actually run the installed exe, not just check files exist.

    The original 0.2.0 MSI shipped a jarvis-desktop.exe that crashed with
    "Unable to configure formatter 'default'" although every file was present.
    """
    desktop = (ROOT / "src/jarvis/cli/desktop_gui.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/windows-msi.yml").read_text(encoding="utf-8")

    assert "--selftest" in desktop
    assert "def _selftest" in desktop
    assert "'--selftest'" in workflow
    assert "failed its startup selftest" in workflow
