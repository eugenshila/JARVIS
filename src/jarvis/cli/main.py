"""JARVIS CLI — inspired by OpenJarvis."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from jarvis.core.config import JarvisConfig, PRESETS, get_home
from jarvis.core.paths import ensure_dirs
from jarvis import __version__

console = Console()


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="jarvis")
@click.option("--verbose", is_flag=True, help="Verbose logging")
@click.pass_context
def cli(ctx: click.Context, verbose: bool):
    """JARVIS — Personal AI, On Personal Devices."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ensure_dirs()
    if ctx.invoked_subcommand is None:
        # Default: chat
        console.print(
            Panel.fit(
                f"[bold green]JARVIS v{__version__}[/]\nPersonal AI, On Personal Devices\n\n"
                "Run [cyan]jarvis chat[/] to start chatting\n"
                "Run [cyan]jarvis --help[/] for all commands\n"
                "Run [cyan]jarvis doctor[/] to check setup",
                border_style="green",
            )
        )


@cli.command()
@click.argument("prompt", required=False)
@click.option("--agent", "-a", default=None, help="Agent: simple, react, orchestrator, morning_digest, deep_research, code_assistant, ironman, adhd_coach")
@click.option("--engine", "-e", default=None, help="Engine: openai, ollama, mock, vllm, mlx, litellm, gemma_cpp, auto (hybrid online/offline)")
@click.option("--online-engine", default=None, help="Online engine for auto: auto, openai, ollama, vllm, mock")
@click.option("--offline-engine", default=None, help="Offline engine for auto: mock, ollama")
@click.option("--context", "-c", default="", help="Additional context")
@click.option("--mock", is_flag=True, help="Use mock engine (offline demo)")
@click.option("--interactive", is_flag=True, help="Interactive decision when online: Full Stack vs Basic")
def ask(prompt: str | None, agent: str | None, engine: str | None, online_engine: str | None, offline_engine: str | None, context: str, mock: bool, interactive: bool):
    """Ask JARVIS a question (single-turn)."""
    from jarvis.agents.registry import get_agent
    from jarvis.core.types import EngineType

    cfg = JarvisConfig.load()
    if mock or engine == "mock":
        cfg.engine.type = EngineType.MOCK
    elif engine:
        try:
            cfg.engine.type = EngineType(engine)
        except ValueError:
            if engine == "auto":
                cfg.engine.type = EngineType.AUTO
            else:
                console.print(f"[red]Unknown engine {engine}. Available: openai, ollama, mock, auto[/]")
                return
        if engine == "auto":
            if online_engine:
                cfg.auto.online_engine = online_engine
            if offline_engine:
                cfg.auto.offline_engine = offline_engine
            try:
                from jarvis.core.network import get_auto_status
                status = get_auto_status()
                console.print(f"[dim]🌐 Network: {'Online' if status['network']['online'] else 'Offline'} via {status['network']['method']} | Selected: {status['selected']['engine']} — {status['selected']['mode']} | Reason: {status['selected']['reason']}[/]")

                # Interactive decision when online — stays interactive like offline
                if interactive and status["network"]["online"]:
                    console.print(Panel.fit(
                        f"[bold cyan]🌐 ONLINE — Interactive Decision — SHILATECH[/]\n\n"
                        f"Network: Online via {status['network']['method']} {status['network'].get('latency_ms','')}ms\n"
                        f"Current Auto Pick: {status['selected']['engine']} — {status['selected']['mode']}\n\n"
                        f"[bold]You are online, Sir. JARVIS stays interactive like offline — you decide:[/]\n\n"
                        f"[green]1. Full Stack Online[/] — {status['prefs']['online_engine']} → best: openai > ollama\n"
                        f"   • If OPENAI_API_KEY set → openai — prompt to OpenAI API HTTPS, best quality, no RAM for 8GB\n"
                        f"   • If Ollama running → ollama — LLM stays local even online, only search online\n"
                        f"   • Full search + memory, best quality\n\n"
                        f"[yellow]2. Basic Offline Local[/] — {status['prefs']['offline_engine']} → mock/ollama local\n"
                        f"   • Nothing leaves device, 100% private, SHILATECH secure\n"
                        f"   • mock always works or ollama tinyllama 1.1B offline\n"
                        f"   • Same circular interface, only badge changes\n\n"
                        f"For your i5-6300U 8GB: Online openai best, Offline mock/tinyllama",
                        border_style="cyan"
                    ))
                    choice = click.prompt("Decide — 1 for Full Stack Online, 2 for Basic Offline Local (even though online)", type=click.Choice(["1", "2", "full", "basic", "online", "offline"]), default="1", show_choices=True)
                    if choice in ["2", "basic", "offline"]:
                        # Force offline engine even though online
                        cfg.engine.type = EngineType.MOCK if cfg.auto.offline_engine == "mock" else EngineType(cfg.auto.offline_engine) if cfg.auto.offline_engine in ["ollama", "mock"] else EngineType.MOCK
                        console.print(f"[yellow]You chose: Basic Offline Local ({cfg.engine.type.value}) even though online — private, local only, Sir.[/]")
                    else:
                        console.print(f"[green]You chose: Full Stack Online ({status['selected']['engine']}) — {status['selected']['mode']}, Sir.[/]")

            except Exception as e:
                console.print(f"[dim]Auto status failed: {e}[/]")

    if agent:
        cfg.preset = agent

    if not prompt:
        prompt = click.prompt("You")

    agent_name = agent or cfg.preset
    console.print(f"[dim]Agent: {agent_name} | Engine: {cfg.engine.type.value} | Model: {cfg.engine.model}[/]")

    ag = get_agent(agent_name, config=cfg)
    try:
        resp = ag.run(prompt, context=context)
        console.print(Panel(Markdown(resp.content), title=f"JARVIS ({resp.model})", border_style="blue"))
        if resp.usage:
            console.print(f"[dim]Usage: {resp.usage}[/]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        if "OPENAI_API_KEY" in str(e):
            console.print("[yellow]Tip: set OPENAI_API_KEY or use --mock or --engine ollama or --engine auto[/]")


@cli.command()
@click.option("--agent", "-a", default=None, help="Agent preset")
@click.option("--engine", "-e", default=None, help="Engine type: openai, ollama, mock, auto")
@click.option("--online-engine", default=None, help="Online engine for auto")
@click.option("--offline-engine", default=None, help="Offline engine for auto")
@click.option("--interactive", is_flag=True, help="Interactive decision when online")
def chat(agent: str | None, engine: str | None, online_engine: str | None, offline_engine: str | None, interactive: bool):
    """Start interactive chat."""
    from jarvis.agents.registry import get_agent
    from jarvis.core.types import EngineType, Message, Role

    cfg = JarvisConfig.load()
    if engine:
        try:
            cfg.engine.type = EngineType(engine)
        except ValueError:
            pass
    if agent:
        cfg.preset = agent

    if interactive:
        try:
            from jarvis.core.network import get_auto_status
            status = get_auto_status()
            if status["network"]["online"]:
                console.print(Panel.fit(f"[bold cyan]ONLINE Interactive — SHILATECH[/] Full Stack vs Basic, Sir. Auto: {status['selected']['engine']} {status['selected']['mode']}", border_style="cyan"))
                ch = click.prompt("1=Full Stack Online, 2=Basic Offline Local even online", type=click.Choice(["1","2"]), default="1")
                if ch == "2":
                    cfg.engine.type = EngineType.MOCK
                    console.print("[yellow]Basic Offline Local forced even though online, Sir — SHILATECH private.[/]")
        except Exception as e:
            console.print(f"[dim]Interactive check: {e}[/]")

    ag = get_agent(agent or cfg.preset, config=cfg)
    console.print(Panel(f"Chatting with [bold]{ag.name}[/] via [cyan]{cfg.engine.type.value}[/] ({cfg.engine.model}). Type /exit /clear /mode /online /offline to quit or decide.", title="JARVIS Chat"))

    history: list[Message] = []
    while True:
        try:
            user_input = console.input("[bold green]You:[/] ")
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input.strip():
            continue
        if user_input.strip() in ("/exit", "/quit", "exit", "quit"):
            break
        if user_input.strip() == "/clear":
            history.clear()
            console.clear()
            continue
        if user_input.startswith("/agent "):
            new_agent = user_input.split(" ", 1)[1].strip()
            ag = get_agent(new_agent, config=cfg)
            console.print(f"[dim]Switched to {ag.name}[/]")
            continue
        if user_input.strip() in ("/mode", "/online", "/offline", "/decision"):
            try:
                from jarvis.core.network import get_auto_status, check_online
                from jarvis.tools.network_tools import HybridModeTool
                status = get_auto_status()
                tool = HybridModeTool()
                if not status["network"]["online"]:
                    console.print(Panel.fit(f"[yellow]Offline, Sir — {status['selected']['engine']} {status['selected']['mode']}[/]", border_style="yellow"))
                else:
                    if user_input.strip() == "/online":
                        r = tool._run(action="decide", choice="1")
                        console.print(Panel(r, title="Full Stack Online", border_style="green"))
                    elif user_input.strip() == "/offline":
                        r = tool._run(action="decide", choice="2")
                        console.print(Panel(r, title="Basic Offline Local", border_style="yellow"))
                        cfg.engine.type = __import__("jarvis.core.types", fromlist=["EngineType"]).EngineType.MOCK
                        ag = get_agent(agent or cfg.preset, config=cfg)
                    else:
                        r = tool._run(action="interactive")
                        console.print(Panel(r, title="Interactive Decision SHILATECH", border_style="cyan"))
                        ch = click.prompt("Decide 1=Full Stack Online 2=Basic Offline Local", type=click.Choice(["1","2"]), default="1")
                        r2 = tool._run(action="decide", choice=ch)
                        console.print(Panel(r2, border_style="cyan"))
                        if ch == "2":
                            cfg.engine.type = __import__("jarvis.core.types", fromlist=["EngineType"]).EngineType.MOCK
                            ag = get_agent(agent or cfg.preset, config=cfg)
            except Exception as e:
                console.print(f"[red]Decision error: {e}[/]")
            continue

        try:
            # Build context from history
            ctx_text = ""
            if history:
                ctx_text = "\n".join([f"{m.role}: {m.content}" for m in history[-6:]])
            resp = ag.run(user_input, context=ctx_text)
            console.print(Panel(Markdown(resp.content), title="JARVIS", border_style="blue"))
            history.append(Message(role=Role.USER, content=user_input))
            history.append(Message(role=Role.ASSISTANT, content=resp.content))
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind")
@click.option("--port", default=8000, help="Port to bind")
@click.option("--reload", is_flag=True, help="Auto reload")
def serve(host: str, port: int, reload: bool):
    """Start API server."""
    import uvicorn

    console.print(f"[green]Starting JARVIS server at http://{host}:{port}[/]")
    console.print(f"Docs at http://{host}:{port}/docs")
    uvicorn.run("jarvis.server.api:app", host=host, port=port, reload=reload)


@cli.command()
@click.argument("preset", required=False)
@click.option("--force", is_flag=True, help="Overwrite existing config")
@click.option("--list", "list_presets", is_flag=True, help="List presets")
def init(preset: str | None, force: bool, list_presets: bool):
    """Initialize JARVIS config with a preset."""
    if list_presets or not preset:
        table = Table(title="Available Presets")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Tools", style="dim")
        for name, p in PRESETS.items():
            table.add_row(name, p.description, ", ".join(p.tools) or "-")
        console.print(table)
        if not preset:
            return

    if preset not in PRESETS:
        console.print(f"[red]Unknown preset {preset}. Use --list to see available.[/]")
        return

    cfg = JarvisConfig.load()
    if cfg.config_path.exists() and not force:
        console.print(f"[yellow]Config exists at {cfg.config_path}. Use --force to overwrite.[/]")
        return

    cfg.preset = preset
    cfg.save()
    console.print(f"[green]Initialized {preset} at {cfg.config_path}[/]")


@cli.command()
def doctor():
    """Check system health and setup."""
    from jarvis.engine.registry import list_engines
    import shutil

    table = Table(title="JARVIS Doctor — Full Stack")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Details")

    cfg = JarvisConfig.load()
    home = get_home()

    # Config
    exists = cfg.config_path.exists()
    table.add_row("Config", "✅ Found" if exists else "⚠️ Missing", str(cfg.config_path))

    # Home
    table.add_row("Home dir", "✅ Exists" if home.exists() else "❌ Missing", str(home))

    # API keys
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    has_tavily = bool(os.environ.get("TAVILY_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    table.add_row("OPENAI_API_KEY", "✅ Set" if has_openai else "⚠️ Not set", "Cloud inference")
    table.add_row("TAVILY_API_KEY", "✅ Set" if has_tavily else "⚠️ Not set (free DDGS fallback)", "Real web search")
    table.add_row("ANTHROPIC_API_KEY", "✅ Set" if has_anthropic else "⚠️ Not set", "Claude via LiteLLM")

    # Ollama
    ollama_bin = shutil.which("ollama")
    table.add_row("Ollama", "✅ Found" if ollama_bin else "⚠️ Not found", ollama_bin or "https://ollama.com")

    # Python
    table.add_row("Python", f"✅ {sys.version.split()[0]}", sys.executable)

    # Engines
    table.add_row("Engines", "✅", ", ".join(list_engines()))

    # Memory deps
    try:
        import faiss
        faiss_status = "✅ FAISS"
    except ImportError:
        faiss_status = "⚠️ No FAISS (keyword fallback)"
    try:
        import sentence_transformers
        st_status = "✅ ST"
    except ImportError:
        st_status = "⚠️ No ST"
    table.add_row("Vector Memory", f"{faiss_status}, {st_status}", "pip install -e .[memory]")

    # Search deps
    try:
        import tavily, ddgs
        search_status = "✅ Tavily+DDGS"
    except ImportError:
        try:
            import ddgs
            search_status = "✅ DDGS (free)"
        except ImportError:
            search_status = "⚠️ Mock only"
    table.add_row("Web Search", search_status, "pip install -e .[tools-search]")

    # Memory
    mem_dir = home / "memory"
    table.add_row("Memory", "✅ Exists" if mem_dir.exists() else "⚠️ Empty", str(mem_dir))

    # GPU
    try:
        import torch
        if torch.cuda.is_available():
            gpu = f"✅ CUDA {torch.cuda.get_device_name(0)}"
        else:
            gpu = "⚠️ No CUDA (CPU only)"
    except ImportError:
        gpu = "⚠️ torch not installed (CPU)"
    table.add_row("GPU", gpu, "For vLLM")

    # Platform for MLX
    import platform
    is_mac = platform.system() == "Darwin"
    is_arm = platform.machine() == "arm64"
    mlx_ready = "✅ Apple Silicon" if (is_mac and is_arm) else "⚠️ Not Mac ARM (MLX needs M1/M2/M3)"
    table.add_row("MLX", mlx_ready, "For mlx engine")

    console.print(table)

    # Recommendations
    console.print("\n[bold]Recommendations:[/]")
    if not has_openai and not ollama_bin:
        console.print("- Set OPENAI_API_KEY or install Ollama for local models")
        console.print("- Or run [cyan]jarvis ask --mock 'hello'[/] for offline demo")
    if not exists:
        console.print("- Run [cyan]jarvis init --list[/] and [cyan]jarvis init chat-simple --force[/]")
    console.print("- For semantic memory: [cyan]pip install -e .[memory][/]")
    console.print("- For real web search: [cyan]pip install -e .[tools-search][/] + set TAVILY_API_KEY")
    console.print("- For high-perf local: [cyan]pip install -e .[inference-vllm][/] (NVIDIA) or [inference-mlx] (Mac)")
    console.print("- Full laptop guide: [cyan]docs/install/LAPTOP_SETUP.md[/]")


@cli.command()
@click.argument("query", required=False)
@click.option("--top-k", default=5, help="Top K results")
def memory(query: str | None, top_k: int):
    """Search or list local memory."""
    from jarvis.memory.store import MemoryStore

    store = MemoryStore()
    if query:
        results = store.search(query, top_k=top_k)
        if not results:
            console.print("[dim]No memories found.[/]")
            return
        for r in results:
            console.print(Panel(r.content, title=f"Score {r.score:.2f} | {r.entry.id}", border_style="dim"))
    else:
        entries = store.list(limit=top_k)
        if not entries:
            console.print("[dim]No memories yet. Use 'jarvis memory' with add via API or tool.[/]")
            return
        for e in entries:
            console.print(f"[cyan]{e.id}[/]: {e.content[:200]}")


@cli.command()
@click.argument("content")
def remember(content: str):
    """Save a fact to memory."""
    from jarvis.memory.store import MemoryStore

    store = MemoryStore()
    entry = store.add(content)
    console.print(f"[green]Saved memory {entry.id}[/]: {content}")


@cli.command()
@click.option("--list", "list_skills", is_flag=True, help="List skills")
@click.argument("name", required=False)
def skill(name: str | None, list_skills: bool):
    """List or show skills."""
    from jarvis.skills.registry import SkillRegistry

    reg = SkillRegistry()
    if list_skills or not name:
        table = Table(title="Skills")
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        table.add_column("Tags")
        for s in reg.list():
            table.add_row(s.name, s.description, ", ".join(s.tags))
        console.print(table)
        return

    s = reg.get(name)
    if not s:
        console.print(f"[red]Skill {name} not found[/]")
        return
    console.print(Panel(s.prompt, title=f"Skill: {s.name}", subtitle=s.description))


@cli.command()
@click.option("--fresh", is_flag=True, help="Force fresh digest")
def digest(fresh: bool):
    """Generate morning digest."""
    from jarvis.agents.registry import get_agent

    cfg = JarvisConfig.load()
    ag = get_agent("morning_digest", config=cfg)
    console.print("[dim]Generating morning digest...[/]")
    try:
        resp = ag.run("Generate my morning digest", context="")
        console.print(Panel(Markdown(resp.content), title="Morning Digest", border_style="green"))
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")


@cli.command()
def agents():
    """List available agents."""
    from jarvis.agents.registry import list_agents, REGISTRY

    table = Table(title="Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    for name in list_agents():
        cls = REGISTRY[name]
        table.add_row(name, cls.description)
    console.print(table)


@cli.command()
@click.argument("prompt")
@click.option("--agent", "-a", default="deep_research")
def research(prompt: str, agent: str):
    """Deep research query."""
    from jarvis.agents.registry import get_agent

    cfg = JarvisConfig.load()
    ag = get_agent(agent, config=cfg)
    console.print(f"[dim]Researching with {ag.name}...[/]")
    resp = ag.run(prompt)
    console.print(Panel(Markdown(resp.content), title="Research Report", border_style="blue"))


@cli.command()
@click.argument("path", type=click.Path(exists=True), required=False)
def scan(path: str | None):
    """Scan for data boundary issues (privacy check)."""
    console.print("[bold]Data Boundary Scan[/]")
    checks = [
        ("Config exposes API key on disk", False),
        ("Memory contains PII", False),
        ("Tools have excessive permissions", False),
        ("Telemetry enabled without consent", False),
    ]
    table = Table()
    table.add_column("Check")
    table.add_column("Result")
    for name, failed in checks:
        table.add_row(name, "❌ Issue" if failed else "✅ OK")
    console.print(table)
    console.print("[green]Scan complete — no critical issues (mock audit).[/]")
    console.print("[dim]For full audit, see OpenJarvis security docs.[/]")


@cli.command()
@click.option("--engine", "-e", default=None, help="Engine: openai, ollama, mock, vllm, mlx, litellm")
@click.option("--voice", is_flag=True, help="Enable voice I/O (STT+TTS)")
@click.option("--wake-word", default="jarvis", help="Wake word for voice mode")
def ironman(engine: str | None, voice: bool, wake_word: str):
    """Interactive AI like Iron Man's JARVIS — witty, voice-ready, device control."""
    from jarvis.agents.registry import get_agent
    from jarvis.core.types import EngineType

    cfg = JarvisConfig.load()
    if engine:
        try:
            cfg.engine.type = EngineType(engine)
        except ValueError:
            pass

    console.print(Panel.fit(
        f"[bold green]JARVIS Iron Man Mode[/]\n"
        f"Personal AI, On Personal Devices\n"
        f"Engine: {cfg.engine.type.value} | Model: {cfg.engine.model}\n"
        f"Voice: {'Enabled' if voice else 'Text only (use --voice for STT/TTS)'}\n"
        f"Wake word: {wake_word}\n\n"
        f"Try: 'Good morning JARVIS', 'Turn off the lights', 'What should I work on today?', 'I am Iron Man'",
        border_style="green"
    ))

    ag = get_agent("ironman", config=cfg)

    if voice:
        try:
            from jarvis.speech.voice_io import interactive_voice_loop
            interactive_voice_loop(ag, wake_word=wake_word, tts=True)
            return
        except ImportError as e:
            console.print(f"[yellow]Voice deps missing: {e}. Falling back to text. Install with: pip install -e .[voice][/]")
        except Exception as e:
            console.print(f"[red]Voice mode failed: {e}. Falling back to text.[/]")

    # Text interactive loop with Iron Man personality
    try:
        greeting = ag.get_greeting()
    except Exception:
        greeting = "Good evening, Sir. JARVIS online."

    console.print(Panel(greeting, title="JARVIS", border_style="blue"))

    while True:
        try:
            user_input = console.input("[bold green]You:[/] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Shutting down, Sir. Always a pleasure.[/]")
            break

        if not user_input.strip():
            continue
        if user_input.strip().lower() in ("/exit", "/quit", "exit", "quit", "goodbye", "shutdown"):
            console.print(Panel("Shutting down, Sir. Always a pleasure.", title="JARVIS", border_style="green"))
            break

        try:
            resp = ag.run(user_input, context="")
            console.print(Panel(Markdown(resp.content), title="JARVIS", border_style="blue"))
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


@cli.command()
@click.option("--engine", "-e", default=None, help="Engine: openai, ollama, mock, vllm, mlx")
@click.option("--mits", default="", help="Comma-separated 3 MITs")
@click.option("--energy", default="medium", help="Energy: low, medium, high")
def adhd(engine: str | None, mits: str, energy: str):
    """ADHD co-pilot — task breakdown, 3 MITs, focus + body double, wins."""
    from jarvis.agents.registry import get_agent
    from jarvis.core.types import EngineType

    cfg = JarvisConfig.load()
    if engine:
        try:
            cfg.engine.type = EngineType(engine)
        except ValueError:
            pass

    console.print(Panel.fit(
        f"[bold magenta]JARVIS ADHD Co-Pilot[/]\n"
        f"For executive dysfunction, time blindness, overwhelm\n"
        f"Engine: {cfg.engine.type.value} | Model: {cfg.engine.model}\n"
        f"Energy: {energy}\n\n"
        f"Commands:\n"
        f"  brain dump [everything] — dump messy brain\n"
        f"  break down [task] — atomize scary task\n"
        f"  plan my day — 3 MITs + time blocking\n"
        f"  focus on [task] — Pomodoro + body double\n"
        f"  log win [what] — dopamine hit\n"
        f"  energy check — match tasks to energy\n"
        f"  overwhelm — SOS grounding + ONE step\n"
        f"  capture [thought] — zero-friction inbox\n",
        border_style="magenta"
    ))

    ag = get_agent("adhd_coach", config=cfg)

    # If MITs provided via flag, run planner immediately
    if mits:
        try:
            resp = ag.run(f"plan my day MITs: {mits} energy: {energy}", context="")
            console.print(Panel(Markdown(resp.content), title="Day Plan", border_style="magenta"))
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")

    # Interactive loop
    console.print(Panel("Good morning, Sir. ADHD co-pilot online. No shame, only tiny wins. What's on your mind?", title="JARVIS ADHD", border_style="blue"))

    while True:
        try:
            user_input = console.input("[bold magenta]You:[/] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Shutting down, Sir. Remember: any progress counts.[/]")
            break

        if not user_input.strip():
            continue
        if user_input.strip().lower() in ("/exit", "/quit", "exit", "quit", "goodbye", "shutdown"):
            console.print(Panel("Shutting down, Sir. Log one win before you go? You did something today.", title="JARVIS ADHD", border_style="magenta"))
            break

        try:
            resp = ag.run(user_input, context="")
            console.print(Panel(Markdown(resp.content), title="JARVIS ADHD", border_style="blue"))
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


@cli.command()
@click.option("--engine", "-e", default=None, help="Engine type")
def voice(engine: str | None):
    """Voice chat mode — STT + TTS + Iron Man personality."""
    from jarvis.cli.main import ironman
    # Delegate to ironman with voice enabled
    import click
    ctx = click.get_current_context()
    ctx.invoke(ironman, engine=engine, voice=True, wake_word="jarvis")


@cli.command()
@click.argument("thought", required=False)
@click.option("--tag", default="task", help="Tag: task, idea, worry, remember")
def capture(thought: str | None, tag: str):
    """Quick capture — zero friction inbox for ADHD brain."""
    from jarvis.tools.registry import get_tool

    if not thought:
        thought = console.input("[bold magenta]Capture:[/] ")

    tool = get_tool("quick_capture")
    if tool:
        console.print(Panel(tool.run(thought=thought, tag=tag), title="Captured", border_style="magenta"))
    else:
        console.print("[red]Quick capture tool not available[/]")


@cli.command()
@click.argument("task", required=False)
def breakdown(task: str | None):
    """Break down big scary task into tiny 2-min steps."""
    from jarvis.tools.registry import get_tool

    if not task:
        task = console.input("[bold magenta]Break down:[/] ")

    tool = get_tool("task_breakdown")
    if tool:
        console.print(Panel(Markdown(tool.run(task=task)), title="Atomized", border_style="magenta"))
    else:
        console.print("[red]Task breakdown tool not available[/]")


@cli.command()
@click.argument("task", required=False)
@click.option("--duration", "-d", default=25, help="Focus minutes")
def focus(task: str | None, duration: int):
    """Focus session with body doubling — Pomodoro++ for ADHD."""
    from jarvis.tools.registry import get_tool

    if not task:
        task = console.input("[bold magenta]Focus on:[/] ")

    tool = get_tool("focus")
    if tool:
        console.print(Panel(Markdown(tool.run(task=task, duration=duration)), title=f"Focus {duration}min", border_style="magenta"))
        # Simple timer
        console.print(f"[dim]Timer {duration}min — Say 'log win' when done. Press Ctrl+C to stop early.[/]")
        try:
            import time
            for i in range(duration * 60, 0, -1):
                if i % 60 == 0:
                    console.print(f"[magenta]{i//60} min left — stay with '{task}', Sir[/]")
                time.sleep(1)
            console.print(Panel(f"🎉 Focus done, Sir! You stayed with '{task}' for {duration} min — log win?", title="Done", border_style="green"))
        except KeyboardInterrupt:
            console.print("\n[dim]Focus paused. Any progress counts, Sir.[/]")
    else:
        console.print("[red]Focus tool not available[/]")


@cli.command(name="log-win")
@click.argument("win", required=False)
@click.option("--show", is_flag=True, help="Show wins")
def log_win(win: str | None, show: bool):
    """Log tiny win for dopamine — ADHD brain needs this."""
    from jarvis.tools.registry import get_tool

    if not win and not show:
        win = console.input("[bold magenta]Log win:[/] ")

    tool = get_tool("win_tracker")
    if tool:
        if show:
            console.print(Panel(Markdown(tool.run(show=True)), title="Wins", border_style="green"))
        else:
            console.print(Panel(tool.run(win=win or ""), title="Win!", border_style="green"))
    else:
        console.print("[red]Win tracker not available[/]")


@cli.command()
@click.option("--enable", is_flag=True, help="Enable autostart on boot")
@click.option("--disable", is_flag=True, help="Disable autostart")
@click.option("--status", "show_status", is_flag=True, help="Show autostart status")
@click.option("--mode", default="ironman", help="Mode: ironman, adhd, gui, server, cli")
def autostart(enable: bool, disable: bool, show_status: bool, mode: str):
    """Manage JARVIS autostart — Good morning Eugene on boot."""
    from jarvis.tools.registry import get_tool

    tool = get_tool("autostart")
    if not tool:
        console.print("[red]Autostart tool not available[/]")
        return

    if enable:
        console.print(Panel(Markdown(tool.run(action="enable", mode=mode)), title="Autostart Enabled", border_style="green"))
    elif disable:
        console.print(Panel(Markdown(tool.run(action="disable")), title="Autostart Disabled", border_style="yellow"))
    else:
        console.print(Panel(Markdown(tool.run(action="status", mode=mode)), title="Autostart Status", border_style="blue"))


@cli.command()
@click.option("--name", default="", help="Your name (Eugene)")
@click.option("--set-name", default="", help="Set name permanently")
@click.option("--evening", is_flag=True, help="Evening greeting")
def greeting(name: str, set_name: str, evening: bool):
    """Good morning greeting — Good morning Eugene + tasks alignment."""
    from jarvis.tools.registry import get_tool

    tool = get_tool("greeting")
    if tool:
        console.print(Panel(Markdown(tool.run(name=name, set_name=set_name, evening=evening)), title="JARVIS Greeting", border_style="green"))
    else:
        # Fallback
        from jarvis.startup.greeting import get_greeting
        g = get_greeting(name or None)
        if set_name:
            g.set_user_name(set_name)
        if evening:
            console.print(Panel(g.get_evening_greeting(), title="Good Evening", border_style="blue"))
        else:
            console.print(Panel(g.get_greeting(), title=f"Good Morning {g.user_name}", border_style="green"))


@cli.command()
@click.option("--mits", default="", help="Today's 3 MITs comma separated")
def align(mits: str):
    """Align today's tasks — Good morning Eugene + 3 MITs + schedule."""
    from jarvis.tools.registry import get_tool

    tool = get_tool("task_alignment")
    if tool:
        if mits:
            console.print(Panel(Markdown(tool.run(mits=mits)), title="Tasks Aligned", border_style="green"))
        else:
            console.print(Panel(Markdown(tool.run(show=True)), title="Today's Alignment", border_style="blue"))
    else:
        console.print("[red]Task alignment tool not available[/]")


@cli.command()
@click.option("--mode", default="ironman", help="Mode: ironman, adhd, hud, gui, server")
@click.option("--name", default="Eugene", help="User name")
@click.option("--engine", default="mock", help="Engine: mock, ollama, openai")
@click.option("--no-voice", is_flag=True, help="Disable voice greeting")
def daemon(mode: str, name: str, engine: str, no_voice: bool):
    """JARVIS Daemon — autostart + Good Morning Eugene + system tray + ADHD check-ins."""
    try:
        from jarvis.startup.daemon import JARVISDaemon
        console.print(Panel.fit(
            f"[bold green]JARVIS Daemon — Always On Like Iron Man[/]\n"
            f"Mode: {mode} | User: {name} | Engine: {engine} | Voice: {not no_voice}\n\n"
            f"Features:\n"
            f"  • Good morning {name} with TTS + notification on boot\n"
            f"  • System tray icon (arc reactor)\n"
            f"  • Periodic ADHD check-ins every 25m\n"
            f"  • Show HUD, tasks, focus from tray\n"
            f"  • Stays running, Sir\n",
            border_style="green"
        ))
        daemon = JARVISDaemon(mode=mode, user_name=name, engine=engine, voice=not no_voice)
        daemon.start()
    except ImportError as e:
        console.print(f"[red]Daemon deps missing: {e}. Install: pip install pystray Pillow[/]")
        # Fallback: just greeting + loop
        try:
            from jarvis.startup.daemon import JARVISDaemon
            daemon = JARVISDaemon(mode=mode, user_name=name, engine=engine, voice=False)
            daemon.morning_greeting()
            daemon.run_loop()
        except Exception as e2:
            console.print(f"[red]Daemon failed: {e2}[/]")


@cli.command()
@click.option("--action", default="status", help="Action: status, check, engines")
def online(action: str):
    """Check hybrid online/offline status — auto engine selection."""
    from jarvis.tools.registry import get_tool

    tool = get_tool("network_status")
    if tool:
        console.print(Panel(Markdown(tool.run(action=action)), title="Hybrid Online/Offline Status", border_style="green"))
    else:
        try:
            from jarvis.core.network import get_auto_status
            status = get_auto_status()
            console.print(Panel(f"Network: {'Online' if status['network']['online'] else 'Offline'} via {status['network']['method']}\nSelected: {status['selected']['engine']} — {status['selected']['mode']}\nReason: {status['selected']['reason']}", title="Hybrid Status"))
        except Exception as e:
            console.print(f"[red]Failed: {e}[/]")


@cli.command(name="network")
@click.option("--action", default="status", help="Action: status, check, engines")
def network_cmd(action: str):
    """Network status — same as online."""
    from jarvis.tools.registry import get_tool

    tool = get_tool("network_status")
    if tool:
        console.print(Panel(Markdown(tool.run(action=action)), title="Network Status", border_style="blue"))
    else:
        console.print("[red]Network tool not available[/]")


@cli.command(name="hybrid")
@click.option("--action", default="status", help="Action: status, set, enable, disable")
@click.option("--online-engine", default="auto", help="Online engine: auto, openai, ollama, vllm, mock")
@click.option("--offline-engine", default="mock", help="Offline engine: mock, ollama")
def hybrid_cmd(action: str, online_engine: str, offline_engine: str):
    """Hybrid mode config — online full stack vs offline basic."""
    from jarvis.tools.registry import get_tool

    tool = get_tool("hybrid_mode")
    if tool:
        console.print(Panel(Markdown(tool.run(action=action, online_engine=online_engine, offline_engine=offline_engine)), title="Hybrid Mode", border_style="cyan"))
    else:
        console.print("[red]Hybrid tool not available[/]")


@cli.command()
@click.option("--name", default="Eugene", help="User name")
@click.option("--include-weather", is_flag=True, default=True, help="Include weather")
@click.option("--include-calendar", is_flag=True, default=True, help="Include calendar")
@click.option("--include-email", is_flag=True, default=True, help="Include email")
@click.option("--include-tasks", is_flag=True, default=True, help="Include tasks")
def briefing(name: str, include_weather: bool, include_calendar: bool, include_email: bool, include_tasks: bool):
    """Proactive morning briefing — Good Morning Eugene + weather + calendar + email + tasks + energy."""
    from jarvis.tools.registry import get_tool

    tool = get_tool("proactive_briefing")
    if tool:
        console.print(Panel(Markdown(tool.run(name=name, include_weather=include_weather, include_calendar=include_calendar, include_email=include_email, include_tasks=include_tasks)), title=f"Proactive Briefing — Good Morning {name}", border_style="green"))
    else:
        console.print("[red]Proactive briefing tool not available[/]")


@cli.command()
@click.argument("location", required=False, default="Nairobi")
def weather(location: str):
    """Weather for task planning — Good Morning Eugene weather."""
    from jarvis.tools.registry import get_tool

    tool = get_tool("weather")
    if tool:
        console.print(Panel(Markdown(tool.run(location=location)), title=f"Weather — {location}", border_style="blue"))
    else:
        console.print("[red]Weather tool not available[/]")


if __name__ == "__main__":
    cli()
