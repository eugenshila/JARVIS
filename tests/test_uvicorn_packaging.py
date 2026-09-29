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
