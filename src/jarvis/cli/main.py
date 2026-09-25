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
@click.option("--agent", "-a", default=None, help="Agent: simple, react, orchestrator, morning_digest, deep_research, code_assistant")
@click.option("--engine", "-e", default=None, help="Engine: openai, ollama, mock, vllm, mlx, litellm, gemma_cpp")
@click.option("--context", "-c", default="", help="Additional context")
@click.option("--mock", is_flag=True, help="Use mock engine (offline demo)")
def ask(prompt: str | None, agent: str | None, engine: str | None, context: str, mock: bool):
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
            console.print(f"[red]Unknown engine {engine}. Available: openai, ollama, mock[/]")
            return

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
            console.print("[yellow]Tip: set OPENAI_API_KEY or use --mock or --engine ollama[/]")


@cli.command()
@click.option("--agent", "-a", default=None, help="Agent preset")
@click.option("--engine", "-e", default=None, help="Engine type")
def chat(agent: str | None, engine: str | None):
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

    ag = get_agent(agent or cfg.preset, config=cfg)
    console.print(Panel(f"Chatting with [bold]{ag.name}[/] via [cyan]{cfg.engine.type.value}[/] ({cfg.engine.model}). Type /exit to quit, /clear to clear.", title="JARVIS Chat"))

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
    # Simple mock audit
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


if __name__ == "__main__":
    cli()
