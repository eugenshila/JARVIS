"""Business OS CLI — Teach JARVIS your goals, priorities, business, workflows, rules, standards + persistent memory."""

import click
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from jarvis.core.business_profile import get_business_profile, BusinessProfile, ensure_business_profile
from jarvis.core.config import get_home

console = Console()

@click.group()
def business():
    """Business OS — Goals, priorities, workflows, rules, standards, persistent memory — SHILATECH."""
    pass

@business.command(name="init")
@click.option("--name", default="Eugene", help="Your name")
@click.option("--business-name", default="SHILATECH", help="Business name")
@click.option("--north-star", default="", help="North star goal")
@click.option("--force", is_flag=True, help="Force overwrite existing profile")
def business_init(name: str, business_name: str, north_star: str, force: bool):
    """Initialize business profile — teaches JARVIS your business."""
    profile = get_business_profile()
    if profile.path.exists() and not force:
        console.print(f"[yellow]Business profile exists at {profile.path}. Use --force to overwrite.[/]")
        console.print(Panel(profile.to_context(), title="Current Profile", border_style="blue"))
        return
    
    # Create new
    new_profile = BusinessProfile()
    new_profile.user_name = name
    new_profile.business.name = business_name
    if north_star:
        new_profile.goals.north_star = north_star
    new_profile.save()
    
    console.print(Panel.fit(f"[bold green]Business Profile Initialized — SHILATECH[/]\n\nUser: {name}\nBusiness: {business_name}\nNorth Star: {new_profile.goals.north_star}\n\nFile: {new_profile.path}\n\nJARVIS now knows your business, Sir.", border_style="green"))
    console.print(Panel(new_profile.to_context(), title="Business Profile", border_style="blue"))

@business.command(name="profile")
@click.option("--action", default="show", help="Action: show, path, reset, edit")
@click.option("--north-star", default="", help="Set north star")
@click.option("--user-name", default="", help="Set user name")
@click.option("--business-name", default="", help="Set business name")
@click.option("--mission", default="", help="Set mission")
def business_profile_cmd(action: str, north_star: str, user_name: str, business_name: str, mission: str):
    """Show or update business profile."""
    from jarvis.tools.registry import get_tool
    tool = get_tool("business_profile")
    if tool:
        result = tool.run(action=action, north_star=north_star, user_name=user_name, business_name=business_name, mission=mission)
        console.print(Panel(Markdown(result), title=f"Business Profile — {action}", border_style="blue"))
    else:
        profile = get_business_profile()
        console.print(Panel(profile.to_context(), title="Business Profile", border_style="blue"))

@business.command(name="goals")
@click.option("--action", default="show", help="Action: show, add, set_north_star")
@click.option("--goal", default="", help="Goal text")
@click.option("--timeframe", default="90d", help="Timeframe: 1y, 90d, 30d, personal, north_star")
def business_goals_cmd(action: str, goal: str, timeframe: str):
    """Manage goals — north star, long term, short term."""
    from jarvis.tools.registry import get_tool
    tool = get_tool("business_goals")
    if tool:
        result = tool.run(action=action, goal=goal, timeframe=timeframe)
        console.print(Panel(Markdown(result), title=f"Goals — {action}", border_style="green"))
    else:
        profile = get_business_profile()
        console.print(Panel(f"North Star: {profile.goals.north_star}\n\n1Y: {profile.goals.long_term_1y}\n\n90D: {profile.goals.short_term_90d}", title="Goals"))

@business.command(name="priorities")
@click.option("--action", default="show", help="Action: show, set_mits, add_pillar")
@click.option("--priority", default="", help="Priority text or MIT1,MIT2,MIT3")
def business_priorities_cmd(action: str, priority: str):
    """Manage priorities — MITs today, pillars."""
    from jarvis.tools.registry import get_tool
    tool = get_tool("business_priorities")
    if tool:
        result = tool.run(action=action, priority=priority)
        console.print(Panel(Markdown(result), title=f"Priorities — {action}", border_style="magenta"))
    else:
        profile = get_business_profile()
        console.print(Panel(f"MITs: {profile.priorities.mit_today}", title="Priorities"))

@business.command(name="workflows")
@click.option("--action", default="show", help="Action: show, add")
@click.option("--workflow", default="", help="Workflow text")
@click.option("--type", "wf_type", default="daily", help="Type: daily, weekly, sop_dev, sop_biz")
def business_workflows_cmd(action: str, workflow: str, wf_type: str):
    """Manage workflows — daily, weekly, SOPs."""
    from jarvis.tools.registry import get_tool
    tool = get_tool("business_workflows")
    if tool:
        result = tool.run(action=action, workflow=workflow, type=wf_type)
        console.print(Panel(Markdown(result), title=f"Workflows — {action}", border_style="cyan"))
    else:
        profile = get_business_profile()
        console.print(Panel(f"Daily: {profile.workflows.daily_routine[:2]}", title="Workflows"))

@business.command(name="rules")
@click.option("--action", default="show", help="Action: show, add")
@click.option("--rule", default="", help="Rule text")
@click.option("--type", "rule_type", default="business", help="Type: coding, business, communication, decision")
def business_rules_cmd(action: str, rule: str, rule_type: str):
    """Manage rules and standards."""
    from jarvis.tools.registry import get_tool
    tool = get_tool("business_rules")
    if tool:
        result = tool.run(action=action, rule=rule, type=rule_type)
        console.print(Panel(Markdown(result), title=f"Rules — {action}", border_style="yellow"))
    else:
        profile = get_business_profile()
        console.print(Panel(f"Business Rules: {profile.rules.business_rules[:3]}", title="Rules"))

@business.command(name="memory")
@click.option("--action", default="search", help="Action: save, search, list, stats, clear")
@click.option("--query", default="", help="Query for search")
@click.option("--content", default="", help="Content to save")
@click.option("--confirm", is_flag=True, help="Confirm clear")
def business_memory_cmd(action: str, query: str, content: str, confirm: bool):
    """Business persistent memory — vector search."""
    from jarvis.tools.registry import get_tool
    tool = get_tool("business_memory")
    if tool:
        result = tool.run(action=action, query=query, content=content, confirm=confirm)
        console.print(Panel(Markdown(result), title=f"Business Memory — {action}", border_style="green"))
    else:
        console.print("[red]Business memory tool not available[/]")

@business.command(name="teach")
@click.option("--interactive", is_flag=True, default=True, help="Interactive teaching")
def business_teach_cmd(interactive: bool):
    """Teach JARVIS your business — interactive onboarding."""
    profile = ensure_business_profile()
    
    console.print(Panel.fit(
        f"[bold green]Teach JARVIS Your Business — SHILATECH Business OS[/]\n\n"
        f"Current Profile: {profile.business.name} — {profile.user_name}\n"
        f"North Star: {profile.goals.north_star}\n\n"
        f"This will teach JARVIS your goals, priorities, business, workflows, rules, standards\n"
        f"and save to persistent memory with vector search.\n\n"
        f"File: {profile.path}\n"
        f"Memory: {get_home() / 'memory'}",
        border_style="green"
    ))
    
    if not interactive:
        console.print(Panel(profile.to_context(), title="Current Business Profile", border_style="blue"))
        return
    
    # Interactive
    console.print("\n[bold cyan]Step 1: Goals[/]")
    north_star = click.prompt("North Star (1 sentence ultimate goal)", default=profile.goals.north_star)
    if north_star != profile.goals.north_star:
        profile.goals.north_star = north_star
        console.print(f"[green]North Star set: {north_star}[/]")
    
    console.print("\n[bold cyan]Step 2: MITs Today (3 Most Important Tasks)[/]")
    mit1 = click.prompt("MIT #1", default=profile.priorities.mit_today[0] if profile.priorities.mit_today else "Ship Business OS")
    mit2 = click.prompt("MIT #2", default=profile.priorities.mit_today[1] if len(profile.priorities.mit_today) > 1 else "Fix HUD")
    mit3 = click.prompt("MIT #3", default=profile.priorities.mit_today[2] if len(profile.priorities.mit_today) > 2 else "Setup OpenAI")
    profile.priorities.mit_today = [mit1, mit2, mit3]
    
    console.print("\n[bold cyan]Step 3: Business[/]")
    biz_name = click.prompt("Business name", default=profile.business.name)
    mission = click.prompt("Mission (1 sentence)", default=profile.business.mission)
    profile.business.name = biz_name
    profile.business.mission = mission
    
    console.print("\n[bold cyan]Step 4: Workflows — Daily Routine[/]")
    daily = click.prompt("Daily routine (e.g., 06:00 Good morning + 3 MITs)", default=profile.workflows.daily_routine[0] if profile.workflows.daily_routine else "06:00 Good morning Eugene + 3 MITs")
    if daily not in profile.workflows.daily_routine:
        profile.workflows.daily_routine.insert(0, daily)
    
    console.print("\n[bold cyan]Step 5: Rules — One Business Rule[/]")
    rule = click.prompt("Business rule (e.g., Always SHILATECH, never Stark)", default=profile.rules.business_rules[0] if profile.rules.business_rules else "Always SHILATECH, never Stark Industries")
    if rule not in profile.rules.business_rules:
        profile.rules.business_rules.append(rule)
    
    # Save
    from datetime import datetime
    profile.updated_at = datetime.now().isoformat()
    profile.save()
    
    console.print(Panel.fit(
        f"[bold green]Business Profile Updated — SHILATECH Secure[/]\n\n"
        f"North Star: {profile.goals.north_star}\n"
        f"MITs: {', '.join(profile.priorities.mit_today)}\n"
        f"Business: {profile.business.name} — {profile.business.mission}\n\n"
        f"Saved to {profile.path}\n"
        f"And to persistent memory vector store\n\n"
        f"JARVIS now knows your business, Sir. Try:\n"
        f"  jarvis ask --agent business_os 'What should I work on today?'\n"
        f"  jarvis business memory --action search --query goals",
        border_style="green"
    ))
    
    console.print(Panel(profile.to_context(), title="Updated Business Profile", border_style="blue"))

@business.command(name="openai")
@click.option("--api-key", default="", help="OpenAI API key (or set OPENAI_API_KEY env)")
@click.option("--model", default="gpt-4o-mini", help="Model: gpt-4o-mini, gpt-4o, gpt-4-turbo")
@click.option("--show", is_flag=True, help="Show current config")
def business_openai_cmd(api_key: str, model: str, show: bool):
    """Setup OpenAI as primary brain for Business OS."""
    from jarvis.core.config import JarvisConfig
    from jarvis.core.types import EngineType
    import os
    
    cfg = JarvisConfig.load()
    
    if show:
        has_key = bool(os.environ.get("OPENAI_API_KEY") or cfg.engine.api_key)
        console.print(Panel.fit(
            f"[bold cyan]OpenAI Config — Business OS Brain[/]\n\n"
            f"Engine: {cfg.engine.type.value}\n"
            f"Model: {cfg.engine.model}\n"
            f"API Key Set: {'✅ Yes' if has_key else '❌ No — set OPENAI_API_KEY env'}\n"
            f"API URL: {cfg.engine.api_url}\n\n"
            f"For Business OS, recommended:\n"
            f"  Engine: openai\n"
            f"  Model: gpt-4o-mini (fast, cheap) or gpt-4o (best)\n\n"
            f"Set via:\n"
            f"  export OPENAI_API_KEY=sk-...\n"
            f"  jarvis business openai --model gpt-4o-mini\n"
            f"  jarvis init business-os --force\n",
            border_style="cyan"
        ))
        return
    
    if api_key:
        # Save to env file? For now just set config
        cfg.engine.api_key = api_key
        # Also write to .env suggestion
        console.print(f"[green]API key set in config (will be read from env next time). For persistence, set env:[/]\n  export OPENAI_API_KEY={api_key[:10]}... \n  echo 'OPENAI_API_KEY={api_key}' >> ~/.bashrc")
    
    cfg.engine.type = EngineType.OPENAI
    cfg.engine.model = model
    cfg.preset = "business-os"
    cfg.save()
    
    console.print(Panel.fit(
        f"[bold green]OpenAI Brain Enabled — Business OS[/]\n\n"
        f"Engine: openai\n"
        f"Model: {model}\n"
        f"Preset: business-os\n"
        f"Config: {cfg.config_path}\n\n"
        f"Now JARVIS uses OpenAI as primary brain, Sir.\n"
        f"Offline fallback: mock/ollama when no internet\n"
        f"Persistent memory: vector FAISS + keyword\n\n"
        f"Try:\n"
        f"  jarvis ask --agent business_os 'Good morning, what should I work on today?'\n"
        f"  jarvis chat --agent business_os --engine openai\n"
        f"  jarvis business memory --action stats\n",
        border_style="green"
    ))

@business.command(name="harness")
@click.option("--install", is_flag=True, default=True, help="Install agentic harness")
def business_harness_cmd(install: bool):
    """Install agentic harness — agents, tools, memory, engines."""
    console.print(Panel.fit(
        "[bold green]Agentic Harness — JARVIS Business OS[/]\n\n"
        "Installing: agents, tools, engines, memory, business profile\n",
        border_style="green"
    ))
    
    # Check deps
    from jarvis.engine.registry import list_engines
    from jarvis.agents.registry import list_agents
    from jarvis.tools.registry import list_tools
    import shutil
    
    table = Table(title="Agentic Harness Status")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Details")
    
    # Engines
    engines = list_engines()
    table.add_row("Engines", "✅", ", ".join(engines))
    
    # Agents
    agents = list_agents()
    table.add_row("Agents", "✅", f"{len(agents)} agents: {', '.join(agents[:5])}...")
    
    # Tools
    tools = list_tools()
    table.add_row("Tools", "✅", f"{len(tools)} tools: business_profile, business_goals, memory, etc")
    
    # Memory
    try:
        import faiss
        mem_status = "✅ FAISS vector"
    except ImportError:
        mem_status = "⚠️ Keyword fallback (install faiss)"
    try:
        import sentence_transformers
        mem_status += " + ST"
    except ImportError:
        mem_status += " (no ST)"
    table.add_row("Memory", mem_status, "Persistent in ~/.jarvis/memory/")
    
    # Business Profile
    profile = get_business_profile()
    table.add_row("Business Profile", "✅ Exists" if profile.path.exists() else "⚠️ Not yet", str(profile.path))
    
    # OpenAI
    import os
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    table.add_row("OpenAI", "✅ Set" if has_openai else "⚠️ Not set", "OPENAI_API_KEY env for Business OS brain")
    
    # Ollama
    ollama_bin = shutil.which("ollama")
    table.add_row("Ollama", "✅ Found" if ollama_bin else "⚠️ Not found", ollama_bin or "https://ollama.com for offline LLM")
    
    console.print(table)
    
    console.print("\n[bold]Install Commands:[/]")
    console.print("- Full harness: [cyan]pip install -e .[server,memory,tools-search,voice][/]")
    console.print("- Vector memory: [cyan]pip install -e .[memory]  # FAISS + sentence-transformers[/]")
    console.print("- OpenAI: [cyan]export OPENAI_API_KEY=sk-...[/] + [cyan]jarvis business openai --model gpt-4o-mini[/]")
    console.print("- Business profile: [cyan]jarvis business init --name Eugene --business-name SHILATECH --north-star 'Build personal AI'[/]")
    console.print("- Teach: [cyan]jarvis business teach[/] (interactive)")
    console.print("- Test: [cyan]jarvis ask --agent business_os 'What should I work on today?'[/]")
    
    if install:
        # Ensure dirs
        from jarvis.core.paths import ensure_dirs
        ensure_dirs()
        # Ensure business profile
        ensure_business_profile()
        console.print(f"\n[green]✅ Harness installed, Sir. Business profile at {get_business_profile().path}[/]")
        console.print(f"[green]✅ Memory at {get_home() / 'memory'}[/]")
        console.print(f"[green]✅ Config at {get_home() / 'config.toml'}[/]")
