"""``jarvis web`` — launch the holographic interface: brain, bridge and face.

The interface in ``web/`` is the Iron Man browser UI (React + Three.js + GLSL)
ported from github.com/adewaskar/jarvis (MIT). Upstream it is driven by Claude
Code through a small Node bridge; here the bridge can also be driven by this
repository's own Python brain, so the same face works with OpenAI, Ollama or
fully offline with the mock engine.

    jarvis web                    # our Python brain (default), opens on :5173
    jarvis web --brain claude     # Claude Code, headless (upstream behaviour)
    jarvis web --engine openai    # pick the engine the Python brain uses
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

console = Console()


def find_web_dir() -> Path | None:
    """Locate ``web/`` in a checkout, an installed payload, or a frozen bundle."""
    candidates: list[Path] = []
    here = Path(__file__).resolve()
    candidates.append(here.parent.parent.parent.parent / "web")  # repo checkout
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates += [exe_dir / "web", exe_dir / "payload" / "web"]
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "web")
    candidates.append(Path.cwd() / "web")
    for path in candidates:
        if (path / "package.json").is_file() and (path / "bridge" / "server.mjs").is_file():
            return path
    return None


def node_ok() -> tuple[bool, str]:
    node = shutil.which("node")
    if not node:
        return False, "Node.js 20+ is required — install it from https://nodejs.org"
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=15)
        version = out.stdout.strip()
        major = int(version.lstrip("v").split(".")[0])
        if major < 20:
            return False, f"Node.js {version} is too old — 20 or newer is required"
        return True, version
    except Exception as exc:  # noqa: BLE001
        return False, f"could not run node: {exc}"


@click.command()
@click.option("--brain", type=click.Choice(["jarvis", "claude", "auto"]), default="jarvis",
              help="Which brain answers: our Python stack, Claude Code, or auto-detect")
@click.option("--agent", default="ironman", help="Agent the Python brain uses (ironman, business_os, ...)")
@click.option("--engine", default=None, help="Engine override: openai, ollama, auto, mock")
@click.option("--port", default=5173, help="Port for the interface")
@click.option("--bridge-port", default=8787, help="Port for the bridge")
@click.option("--api-port", default=8000, help="Port for the JARVIS API (the brain)")
@click.option("--host", default="0.0.0.0", help="Interface bind address")
@click.option("--allow-origin", multiple=True, help="Extra browser origins for the bridge (wildcards allowed)")
@click.option("--writes", is_flag=True, help="Allow effectful tools (phone, browser, sending)")
@click.option("--no-api", is_flag=True, help="Do not start the Python API (already running)")
@click.option("--install", is_flag=True, help="Run npm install first")
def web(brain: str, agent: str, engine: str | None, port: int, bridge_port: int, api_port: int,
        host: str, allow_origin: tuple[str, ...], writes: bool, no_api: bool, install: bool):
    """Launch the holographic web interface (brain + bridge + face)."""
    web_dir = find_web_dir()
    if web_dir is None:
        console.print(
            Panel.fit(
                "[red]The web interface was not found.[/]\n\n"
                "Expected a [bold]web/[/] folder next to this installation.\n"
                "In a checkout: [bold]git pull[/]. From an MSI: reinstall — the\n"
                "installer ships the complete source payload.",
                border_style="red",
            )
        )
        raise SystemExit(1)

    ok, note = node_ok()
    if not ok:
        console.print(Panel.fit(f"[red]{note}[/]", border_style="red"))
        raise SystemExit(1)

    if install or not (web_dir / "node_modules").is_dir():
        console.print("[cyan]Installing web dependencies (first run only)…[/]")
        rc = subprocess.call(["npm", "install", "--no-audit", "--no-fund"], cwd=web_dir)
        if rc != 0:
            console.print("[red]npm install failed[/]")
            raise SystemExit(rc)

    api_url = f"http://127.0.0.1:{api_port}"
    env = os.environ.copy()
    env.update(
        {
            "JARVIS_BRAIN": brain,
            "JARVIS_AGENT": agent,
            "JARVIS_API_URL": api_url,
            "JARVIS_BRIDGE_PORT": str(bridge_port),
            "PORT": str(port),
        }
    )
    if engine:
        env["JARVIS_ENGINE"] = engine
    if writes:
        env["JARVIS_ALLOW_WRITES"] = "1"

    origins = [
        f"http://localhost:{port}",
        f"http://127.0.0.1:{port}",
        *allow_origin,
    ]
    env["JARVIS_ALLOWED_ORIGINS"] = ",".join(
        dict.fromkeys([*origins, *filter(None, env.get("JARVIS_ALLOWED_ORIGINS", "").split(","))])
    )

    children: list[subprocess.Popen] = []

    def stop(*_args):
        for child in children:
            try:
                child.terminate()
            except Exception:  # noqa: BLE001
                pass
        time.sleep(0.3)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    if not no_api and brain != "claude":
        console.print(f"[cyan]brain[/]  JARVIS API on {api_url} (agent {agent})")
        children.append(
            subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "jarvis.server.api:app",
                 "--host", "127.0.0.1", "--port", str(api_port)],
                env=env,
            )
        )

        # Let the API answer before the bridge probes it, otherwise the banner
        # reports a brain that is merely slow to boot as one that is missing.
        import urllib.request

        for _ in range(40):
            try:
                with urllib.request.urlopen(f"{api_url}/health", timeout=1):
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.25)

    console.print(f"[cyan]bridge[/] ws://localhost:{bridge_port} · brain {brain}")
    children.append(subprocess.Popen(["node", "bridge/server.mjs"], cwd=web_dir, env=env))

    console.print(f"[cyan]face[/]   http://localhost:{port}")
    children.append(
        subprocess.Popen(
            ["node", "node_modules/vite/bin/vite.js", "--host", host, "--port", str(port)],
            cwd=web_dir,
            env=env,
        )
    )

    console.print(
        Panel.fit(
            f"[bold cyan]J.A.R.V.I.S — SHILATECH[/]\n\n"
            f"Open [bold]http://localhost:{port}[/] in a real Chrome or Edge window,\n"
            "click INITIALISE, allow the microphone and say [bold]\"Hey Jarvis\"[/].\n\n"
            "Embedded preview panes block the microphone — the interface will look\n"
            "alive and never hear you. Ctrl-C stops everything.",
            border_style="cyan",
        )
    )

    try:
        while True:
            for child in children:
                if child.poll() is not None:
                    console.print(f"[yellow]a process exited ({child.returncode}); shutting down[/]")
                    stop()
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop()
