"""
core/paths.py — where things live, including when we are a frozen executable.

TWO PROBLEMS THIS SOLVES

    FROZEN BUILDS. Under PyInstaller (the Windows MSI), ``__file__`` points
    inside a temporary extraction directory that is deleted when the process
    exits. Any code that resolves a bundled resource relative to ``__file__``
    works in a source checkout and silently breaks in the MSI — the classic
    "works on my machine" packaging bug. :func:`base_dir` handles both cases,
    and :func:`is_frozen` lets callers branch explicitly.

    WRITABLE DIRECTORIES. "Just write to the app directory" fails on a real
    install: ``C:\\Program Files`` is not writable by a standard user, and a
    .app bundle on macOS is signed. :func:`uploads_dir` walks a fallback chain
    and verifies each candidate is *actually* writable before returning it,
    rather than assuming.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from jarvis.core.config import get_home


def is_frozen() -> bool:
    """True when running from a PyInstaller-style bundle."""
    return bool(getattr(sys, "frozen", False))


def base_dir() -> Path:
    """The directory to resolve bundled resources against.

    Frozen: the folder holding the executable. Source: the repository root.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    # src/jarvis/core/paths.py -> repo root
    return Path(__file__).resolve().parents[3]


def resource_dir() -> Path:
    """Where read-only bundled data lives (``sys._MEIPASS`` when frozen)."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else base_dir()


def resource(*parts: str) -> Path:
    return resource_dir().joinpath(*parts)


def _writable(path: Path) -> bool:
    """Can we actually create files here? Ask the filesystem, do not guess."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".jarvis_write_test"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def first_writable(candidates: list[Path], fallback_name: str = "jarvis") -> Path:
    """First candidate we can genuinely write to; a temp dir as last resort."""
    for candidate in candidates:
        if _writable(candidate):
            return candidate
    last = Path(tempfile.gettempdir()) / fallback_name
    last.mkdir(parents=True, exist_ok=True)
    return last


def ensure_dirs() -> Path:
    home = get_home()
    for sub in ("", "data", "memory", "skills", "telemetry", "models", "plugins", "captures"):
        (home / sub if sub else home).mkdir(parents=True, exist_ok=True)
    return home


def memory_dir() -> Path:
    return get_home() / "memory"


def skills_dir() -> Path:
    return get_home() / "skills"


def data_dir() -> Path:
    return get_home() / "data"


def captures_dir() -> Path:
    """Screen and camera grabs. Under JARVIS_HOME so it is easy to purge."""
    path = get_home() / "captures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def uploads_dir() -> Path:
    """Where files sent to JARVIS land.

    Prefers somewhere the user can actually find in their file manager, and
    only falls back to application-managed locations. Overridable with
    ``JARVIS_UPLOADS_DIR``.
    """
    override = os.environ.get("JARVIS_UPLOADS_DIR", "").strip()
    if override:
        path = Path(override).expanduser()
        if _writable(path):
            return path

    home = Path.home()
    return first_writable(
        [
            home / "Downloads" / "JARVIS Uploads",
            home / "Documents" / "JARVIS Uploads",
            get_home() / "uploads",
            base_dir() / "uploads",
        ],
        fallback_name="jarvis-uploads",
    )


def describe() -> dict[str, str]:
    """Diagnostics for ``jarvis doctor`` and bug reports."""
    return {
        "frozen": str(is_frozen()),
        "base_dir": str(base_dir()),
        "resource_dir": str(resource_dir()),
        "home": str(get_home()),
        "uploads": str(uploads_dir()),
        "captures": str(captures_dir()),
    }
