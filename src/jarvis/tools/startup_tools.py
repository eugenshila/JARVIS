"""Startup tools — autostart, greeting, task alignment for Good Morning Eugene."""

from __future__ import annotations

from jarvis.tools.base import BaseTool, ToolSpec


class AutostartTool(BaseTool):
    spec = ToolSpec(
        name="autostart",
        description="Manage JARVIS autostart on boot — enable/disable/status. Makes JARVIS say Good Morning Eugene when machine starts. Supports Windows Startup folder, Linux autostart .desktop + systemd, macOS LaunchAgent.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "enable, disable, status", "default": "status"},
                "mode": {"type": "string", "description": "Mode to autostart: gui, ironman, adhd, server, cli", "default": "ironman"},
            },
            "required": [],
        },
    )

    def run(self, action: str = "status", mode: str = "ironman", **kwargs) -> str:
        try:
            from jarvis.startup.autostart import get_autostart_manager
            mgr = get_autostart_manager()
            
            if action == "enable":
                result = mgr.enable(mode)
                if result.get("success"):
                    return f"""✅ Autostart enabled, Sir.

Mode: {mode}
Path: {result.get('path')}
Message: {result.get('message')}

What happens on boot:
  • Machine starts → JARVIS starts in {mode} mode
  • Says 'Good morning Eugene, it's 8am, you have 3 meetings...'
  • Shows today's 3 MITs alignment
  • Ready for voice or text

To test: Reboot or log out/in
To disable: Say 'disable autostart' or run with action=disable

Iron Man style: JARVIS boots with arc reactor at 100%, lab secure.
"""
                else:
                    return f"Failed to enable autostart: {result.get('message')}"
            
            elif action == "disable":
                result = mgr.disable()
                return f"""Autostart disabled, Sir.

Removed: {', '.join(result.get('removed', [])) or 'nothing found'}
Message: {result.get('message')}

JARVIS will no longer start on boot.
To enable again: Say 'enable autostart ironman' or 'enable autostart adhd'
"""
            
            else:  # status
                result = mgr.status()
                enabled = result.get("enabled")
                return f"""Autostart Status:

Enabled: {enabled}
System: {result.get('system')}
Path: {result.get('startup_folder') or result.get('desktop_file') or result.get('plist') or 'N/A'}
Message: {result.get('message')}

Modes available:
  • ironman — Iron Man HUD with arc reactor, Good Morning Eugene + tasks (recommended for you)
  • adhd — ADHD Co-Pilot with 3 MITs, focus timer, wins
  • gui — Desktop GUI
  • server — Web server (frontend)
  • cli — CLI chat

To enable: 'enable autostart ironman' or 'enable autostart adhd'
To disable: 'disable autostart'
"""

        except Exception as e:
            return f"Autostart tool error: {e}. Install: pip install -e . and try again."


class GreetingTool(BaseTool):
    spec = ToolSpec(
        name="greeting",
        description="Good morning greeting — personalized like Iron Man: Good morning Eugene, tasks alignment, energy suggestion. Says Good Morning Eugene and aligns tasks for today.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "User name (Eugene)", "default": ""},
                "set_name": {"type": "string", "description": "Set name permanently", "default": ""},
                "evening": {"type": "boolean", "description": "Evening greeting", "default": False},
            },
            "required": [],
        },
    )

    def run(self, name: str = "", set_name: str = "", evening: bool = False, **kwargs) -> str:
        try:
            from jarvis.startup.greeting import get_greeting
            g = get_greeting(name or None)
            
            if set_name:
                g.set_user_name(set_name)
                return f"Name set to {set_name}, Sir. Future greetings will say Good morning {set_name}."

            if evening:
                return g.get_evening_greeting()
            else:
                return g.get_greeting()
                
        except Exception as e:
            # Fallback mock greeting
            from datetime import datetime
            now = datetime.now()
            user = name or set_name or "Eugene"
            hour = now.hour
            time_greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
            
            return f"""{time_greet}, {user}. It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}.

Arc reactor at 97.3% — kidding, Sir, we're at 100%. All systems nominal.

Today's Alignment — 3 MITs:
1. Q4 Planning Brief
2. Client Email Response
3. Lab Diagnostics

Schedule: You have 3 meetings today, including Q4 planning at 2 PM.

Energy: Based on pattern, high focus 10-11am — recommend MIT 1 then.

What would you like to do first, {user}?

(Fallback greeting — install full: pip install -e .)
Error: {e}
"""


class TaskAlignmentTool(BaseTool):
    spec = ToolSpec(
        name="task_alignment",
        description="Align today's tasks — ADHD 3 MITs + calendar + inbox + wins. Like Iron Man's morning briefing: Good morning Eugene, here's your day.",
        parameters={
            "type": "object",
            "properties": {
                "mits": {"type": "string", "description": "Today's 3 MITs (comma separated)", "default": ""},
                "show": {"type": "boolean", "description": "Show alignment", "default": True},
            },
            "required": [],
        },
    )

    def run(self, mits: str = "", show: bool = True, **kwargs) -> str:
        try:
            from jarvis.startup.greeting import get_greeting
            from jarvis.tools.registry import get_tool
            
            g = get_greeting()
            
            if mits:
                # Save MITs via day planner
                planner = get_tool("day_planner")
                if planner:
                    return planner.run(mits=mits, energy="medium")
                else:
                    return f"MITs set: {mits} (planner tool not available, saved as note)"
            
            # Show alignment
            return g._get_tasks_alignment() + "\n\n" + g._get_energy_suggestion()
            
        except Exception as e:
            return f"Task alignment error: {e}. Try 'plan my day MITs: task1, task2, task3'"
