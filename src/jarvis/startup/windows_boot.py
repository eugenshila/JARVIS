"""Windows boot launcher for the packaged JARVIS experience.

Starts Ollama, the local JARVIS API/HUD, then the hands-free voice companion.
The same executable can be launched with --hands-free by the parent process.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser


HOST = os.environ.get("JARVIS_HOST", "127.0.0.1")
PORT = int(os.environ.get("JARVIS_PORT", "8765"))
HUD_URL = f"http://{HOST}:{PORT}"


def _ollama_ready() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2):
            return True
    except (OSError, urllib.error.URLError):
        return False


def _model_ready() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=3) as response:
            import json
            data = json.load(response)
        return any(
            model.get("name") == "qwen2.5:3b" or model.get("model") == "qwen2.5:3b"
            for model in data.get("models", [])
        )
    except (OSError, ValueError, urllib.error.URLError):
        return False


def start_ollama() -> subprocess.Popen | None:
    if _ollama_ready():
        return None
    ollama = shutil.which("ollama")
    if not ollama:
        print("Ollama was not found in PATH. Install Ollama to enable Qwen2.5:3B.", flush=True)
        return None
    process = subprocess.Popen(
        [ollama, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    for _ in range(30):
        if _ollama_ready():
            break
        time.sleep(1)
    if not _model_ready():
        try:
            subprocess.run(
                [ollama, "pull", "qwen2.5:3b"],
                timeout=1800,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    return process


def start_api() -> threading.Thread:
    import uvicorn
    from jarvis.server.api import app

    def run() -> None:
        uvicorn.run(app, host=HOST, port=PORT, log_level="warning")

    thread = threading.Thread(target=run, name="jarvis-api", daemon=True)
    thread.start()
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{HUD_URL}/health", timeout=1):
                return thread
        except (OSError, urllib.error.URLError):
            time.sleep(0.5)
    return thread


def start_companion() -> subprocess.Popen | None:
    if os.environ.get("JARVIS_DISABLE_HANDS_FREE") == "1":
        return None
    env = os.environ.copy()
    env["JARVIS_HUD_URL"] = HUD_URL
    command = [sys.executable, "--hands-free"]
    return subprocess.Popen(
        command,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hands-free", action="store_true")
    args = parser.parse_args()

    if args.hands_free:
        from jarvis.startup.hud_companion import listen_for_hands_free
        listen_for_hands_free()
        return

    start_ollama()
    start_api()
    webbrowser.open(HUD_URL)
    print("JARVIS online. HUD ready at", HUD_URL, flush=True)
    companion = start_companion()
    if companion:
        print("Hands-free voice companion started.", flush=True)
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
