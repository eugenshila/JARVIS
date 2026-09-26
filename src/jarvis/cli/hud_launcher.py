"""Single-process entry point for the Windows JARVIS HUD installer."""

from __future__ import annotations

import os
import socket
import threading
import time
import webbrowser
from pathlib import Path

from jarvis.startup.hud_companion import listen_for_claps, speak
from jarvis.server.api import app

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}"


def _responding() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.5):
            return True
    except OSError:
        return False


def _run_server() -> None:
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")


def main() -> None:
    # The installed startup shortcut passes no arguments. A second launch
    # simply brings up the existing local HUD without starting another server.
    if _responding():
        webbrowser.open(URL)
        return

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

    os.environ["JARVIS_HUD_URL"] = URL
    webbrowser.open(URL)
    speak("JARVIS online. Good day, Eugene.")
    try:
        listen_for_claps()
    except (OSError, RuntimeError, ValueError) as exc:
        # A machine without a working microphone still gets the HUD.
        log_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JARVIS"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "hud.log").write_text(f"Clap wake unavailable: {exc}\n", encoding="utf-8")
        while thread.is_alive():
            time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        log_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JARVIS"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "hud.log").write_text(f"JARVIS startup failed: {error}\n", encoding="utf-8")
        raise
