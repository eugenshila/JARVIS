"""Native launcher for the JARVIS circular web HUD.

The desktop executable used to draw a separate Tkinter approximation of the HUD.
That meant the MSI could build successfully while installing a UI that did not
match the React interface.  This launcher serves the production frontend and the
JARVIS API from one local process, then hosts it in WebView2 (with Edge/browser
fallbacks).  The interface and the development frontend are therefore the same
code.
"""

from __future__ import annotations

import logging
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

APP_TITLE = "J.A.R.V.I.S — SHILATECH"
HOST = "127.0.0.1"


def _configure_logging() -> logging.Logger:
    log_dir = Path.home() / ".jarvis"
    log_dir.mkdir(parents=True, exist_ok=True)
    log = logging.getLogger("jarvis.desktop")
    if not log.handlers:
        log.setLevel(logging.INFO)
        handler = logging.FileHandler(log_dir / "desktop.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        log.addHandler(handler)
    return log


LOG = _configure_logging()


def frontend_candidates() -> list[Path]:
    """Return production frontend locations for source and frozen installs."""
    paths: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        paths.append(Path(meipass) / "frontend" / "dist")

    here = Path(__file__).resolve()
    # src/jarvis/cli/desktop_gui.py -> repository root
    if len(here.parents) >= 4:
        paths.append(here.parents[3] / "frontend" / "dist")

    exe_dir = Path(sys.executable).resolve().parent
    paths.extend(
        [
            exe_dir / "frontend" / "dist",
            exe_dir / "payload" / "frontend" / "dist",
            Path.cwd() / "frontend" / "dist",
        ]
    )
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(path.resolve() for path in paths))


def find_frontend() -> Path:
    for path in frontend_candidates():
        if (path / "index.html").is_file() and (path / "assets").is_dir():
            return path
    searched = "\n".join(f"  - {path}" for path in frontend_candidates())
    raise FileNotFoundError(
        "The compiled JARVIS interface is missing. Expected frontend/dist in one of:\n"
        f"{searched}\nBuild it with: cd frontend && npm ci && npm run build"
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def create_app(frontend: Path):
    """Attach the compiled single-page app after all API routes."""
    from fastapi.staticfiles import StaticFiles
    from jarvis.server.api import app

    # PyInstaller or test reloads can import this module more than once.
    if not any(getattr(route, "name", None) == "jarvis_frontend" for route in app.routes):
        app.mount("/", StaticFiles(directory=str(frontend), html=True), name="jarvis_frontend")
    return app


def _start_server(frontend: Path):
    import uvicorn

    port = _free_port()
    config = uvicorn.Config(
        create_app(frontend), host=HOST, port=port, log_level="warning", access_log=False
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="jarvis-local-server", daemon=True)
    thread.start()

    base_url = f"http://{HOST}:{port}"
    for _ in range(120):
        if not thread.is_alive():
            raise RuntimeError("The local JARVIS server stopped during startup")
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=0.5) as response:
                if response.status == 200:
                    # The API intentionally owns `/`; loading index.html avoids
                    # its JSON root while static assets and API calls stay same-origin.
                    return server, thread, f"{base_url}/index.html"
        except Exception:  # server is still starting
            time.sleep(0.1)
    server.should_exit = True
    raise TimeoutError("The local JARVIS server did not become ready")


def _run_webview(url: str) -> bool:
    """Run a real native WebView2 window. Return False if pywebview is absent."""
    try:
        import webview
    except Exception as exc:
        LOG.warning("WebView2 host unavailable: %s", exc)
        return False

    webview.create_window(
        APP_TITLE,
        url,
        width=1440,
        height=900,
        min_size=(1100, 700),
        background_color="#020208",
        text_select=True,
    )
    # Edge Chromium is available on supported Windows 10/11 installations.
    webview.start(gui="edgechromium", debug=False, private_mode=False)
    return True


def _edge_path() -> str | None:
    found = shutil.which("msedge")
    if found:
        return found
    for root_name in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        root = os.environ.get(root_name)
        if not root:
            continue
        path = Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        if path.is_file():
            return str(path)
    return None


def _run_browser_fallback(url: str) -> None:
    edge = _edge_path()
    if edge:
        profile = Path.home() / ".jarvis" / "edge-profile"
        profile.mkdir(parents=True, exist_ok=True)
        process = subprocess.Popen(
            [
                edge,
                f"--app={url}",
                "--start-maximized",
                "--no-first-run",
                f"--user-data-dir={profile}",
            ]
        )
        process.wait()
        return

    webbrowser.open(url, new=1)
    # No portable API tells us when a default browser tab closes. Keep the local
    # brain alive until this launcher is stopped.
    while True:
        time.sleep(1)


def _show_error(message: str) -> None:
    LOG.exception(message)
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "JARVIS could not initialise",
            f"{message}\n\nDiagnostic log:\n{Path.home() / '.jarvis' / 'desktop.log'}",
        )
        root.destroy()
    except Exception:
        # The windowed executable has no console, but source runs still benefit.
        print(message, file=sys.stderr)


def main() -> int:
    server = None
    try:
        frontend = find_frontend()
        LOG.info("Using interface at %s", frontend)
        server, thread, url = _start_server(frontend)
        LOG.info("JARVIS initialised at %s", url)
        if not _run_webview(url):
            _run_browser_fallback(url)
        return 0
    except Exception as exc:  # never disappear without telling the user why
        _show_error(str(exc))
        return 1
    finally:
        if server is not None:
            server.should_exit = True


if __name__ == "__main__":
    raise SystemExit(main())
