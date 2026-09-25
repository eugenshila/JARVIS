"""Path helpers."""

from pathlib import Path
from jarvis.core.config import get_home

def ensure_dirs():
    home = get_home()
    for p in [home, home / "data", home / "memory", home / "skills", home / "telemetry", home / "models"]:
        p.mkdir(parents=True, exist_ok=True)
    return home

def memory_dir() -> Path:
    return get_home() / "memory"

def skills_dir() -> Path:
    return get_home() / "skills"

def data_dir() -> Path:
    return get_home() / "data"
