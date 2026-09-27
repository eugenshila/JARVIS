"""Single-process entry point for the Windows JARVIS HUD installer."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from jarvis.startup.hud_companion import listen_for_claps, speak
from jarvis.server.api import app

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"


def _log(message: str) -> None:
    directory = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JARVIS"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "hud.log").open("a", encoding="utf-8") as logfile:
        logfile.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")


def _responding() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.5):
            return True
    except OSError:
        return False


def _ollama_responding() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1.0):
            return True
    except (OSError, ValueError):
        return False


def _ensure_ollama() -> None:
    """Start local Ollama when installed but not already running."""
    if _ollama_responding():
        _log("Ollama already running")
        return
    executable = shutil.which("ollama")
    if not executable:
        _log("Ollama executable not found; HUD will show Ollama offline")
        return
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    try:
        subprocess.Popen([executable, "serve"], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=creationflags, close_fds=sys.platform != "win32")
        for _ in range(30):
            if _ollama_responding():
                _log("Ollama service started automatically")
                return
            time.sleep(0.5)
        _log("Ollama launched but did not become ready within 15 seconds")
    except OSError as exc:
        _log(f"Could not start Ollama: {type(exc).__name__}: {exc}")


def _run_server() -> None:
    import uvicorn

    try:
        uvicorn.run(app, host=HOST, port=PORT, log_level="warning", log_config=None)
    except BaseException as exc:
        _log(f"Local API failed: {type(exc).__name__}: {exc}")
        raise


def main() -> None:
    _log(f"Starting HUD, bundle={getattr(sys, '_MEIPASS', 'source')}, static={getattr(app, 'routes', [])[-1].path}")
    # The installed startup shortcut passes no arguments. A second launch
    # simply brings up the existing local HUD without starting another server.
    if _responding():
        webbrowser.open(URL)
        return

    _ensure_ollama()

    thread = threading.Thread(target=_run_server, daemon=True, name="jarvis-api")
    thread.start()
    for _ in range(100):
        if _responding():
            break
        if not thread.is_alive():
            raise RuntimeError("JARVIS local server failed to start.")
        time.sleep(0.1)
    else:
        raise RuntimeError("JARVIS local server did not become ready.")

    _log("Local API socket ready")

    os.environ["JARVIS_HUD_URL"] = URL
    webbrowser.open(URL)
    speak("JARVIS online. Good day, Eugene.")
    try:
        listen_for_claps()
    except (OSError, RuntimeError, ValueError) as exc:
        # A machine without a working microphone still gets the HUD.
        _log(f"Clap wake unavailable: {exc}")
        while thread.is_alive():
            time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        _log(f"JARVIS startup failed: {type(error).__name__}: {error}")
        raise
