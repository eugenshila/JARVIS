"""Device control tools — Iron Man style.

Mock implementations that show how JARVIS would control smart home, etc.
Real implementations would use Philips Hue, Tuya, Home Assistant, etc.
"""

from __future__ import annotations

import os
import json
import random
from pathlib import Path

from jarvis.tools.base import BaseTool, ToolSpec


class LightsTool(BaseTool):
    spec = ToolSpec(
        name="lights",
        description="Control smart lights — on/off, brightness, color. Mock, but shows pattern for real Hue/Tuya integration.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["on", "off", "dim", "brighten", "color"], "description": "Action"},
                "room": {"type": "string", "description": "Room (living room, bedroom, lab, all)", "default": "all"},
                "brightness": {"type": "integer", "description": "Brightness 0-100", "default": 100},
                "color": {"type": "string", "description": "Color (red, blue, white, warm, etc)", "default": "white"},
            },
            "required": ["action"],
        },
    )

    def run(self, action: str, room: str = "all", brightness: int = 100, color: str = "white", **kwargs) -> str:
        # In real implementation, this would call Hue API, Home Assistant, etc.
        # For now, mock with state file
        home = Path.home() / ".jarvis" / "devices"
        home.mkdir(parents=True, exist_ok=True)
        state_file = home / "lights.json"
        
        # Load previous state
        try:
            state = json.loads(state_file.read_text()) if state_file.exists() else {}
        except Exception:
            state = {}

        # Update state
        if room == "all":
            rooms = ["living room", "bedroom", "lab", "kitchen"]
        else:
            rooms = [room]

        for r in rooms:
            if action == "on":
                state[r] = {"on": True, "brightness": brightness, "color": color}
            elif action == "off":
                state[r] = {"on": False, "brightness": 0, "color": color}
            elif action == "dim":
                prev = state.get(r, {}).get("brightness", 100)
                state[r] = {"on": True, "brightness": max(10, prev - 30), "color": color}
            elif action == "brighten":
                prev = state.get(r, {}).get("brightness", 30)
                state[r] = {"on": True, "brightness": min(100, prev + 30), "color": color}
            elif action == "color":
                prev = state.get(r, {})
                state[r] = {"on": prev.get("on", True), "brightness": prev.get("brightness", 100), "color": color}

        state_file.write_text(json.dumps(state, indent=2))

        # Mock response with JARVIS flair
        if action == "on":
            return f"Lights on in {room}, Sir. {brightness}% brightness, {color}. Lab is ready for work."
        elif action == "off":
            return f"Lights off in {room}, Sir. Power saving mode engaged."
        elif action == "dim":
            return f"Dimmed lights in {room}, Sir. Ambient mode."
        elif action == "brighten":
            return f"Brightened {room} to {state[rooms[0]]['brightness']}%, Sir."
        elif action == "color":
            return f"Set {room} lights to {color}, Sir. Very... atmospheric."
        return f"Lights {action} in {room}."


class MusicTool(BaseTool):
    spec = ToolSpec(
        name="music",
        description="Control music playback — play, pause, next, volume. Mock for Spotify/Sonos.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["play", "pause", "next", "volume", "search"], "description": "Action"},
                "query": {"type": "string", "description": "Song/artist for search/play", "default": ""},
                "volume": {"type": "integer", "description": "Volume 0-100", "default": 50},
            },
            "required": ["action"],
        },
    )

    def run(self, action: str, query: str = "", volume: int = 50, **kwargs) -> str:
        if action == "play":
            if query:
                return f"Playing {query}, Sir. Excellent choice — though my taste is obviously superior."
            return "Playing your usual, Sir. The one you pretend you don't like."
        elif action == "pause":
            return "Music paused, Sir."
        elif action == "next":
            return "Next track, Sir."
        elif action == "volume":
            return f"Volume set to {volume}%, Sir."
        elif action == "search":
            return f"Found 3 results for {query}: 1. {query} (Original), 2. {query} (Acoustic), 3. {query} (Remix). Shall I play one?"
        return f"Music {action}."

class SystemTool(BaseTool):
    spec = ToolSpec(
        name="system",
        description="Check system status — CPU, memory, battery, lab systems. Like JARVIS diagnostics.",
        parameters={
            "type": "object",
            "properties": {
                "check": {"type": "string", "enum": ["all", "cpu", "memory", "battery", "network", "lab"], "default": "all"},
            },
            "required": [],
        },
    )

    def run(self, check: str = "all", **kwargs) -> str:
        import shutil
        import platform

        # Mock diagnostics with real system info where possible
        info = []
        info.append(f"Platform: {platform.system()} {platform.release()} {platform.machine()}")
        
        # Disk
        try:
            total, used, free = shutil.disk_usage("/")
            info.append(f"Disk: {used//(2**30)}GB used / {total//(2**30)}GB total ({free//(2**30)}GB free)")
        except Exception:
            pass

        # Try psutil if available
        try:
            import psutil
            info.append(f"CPU: {psutil.cpu_percent()}%")
            info.append(f"Memory: {psutil.virtual_memory().percent}%")
            info.append(f"Battery: {psutil.sensors_battery().percent if psutil.sensors_battery() else 'N/A'}%")
        except ImportError:
            info.append("CPU: Nominal (install psutil for details)")
            info.append("Memory: Nominal")
            info.append("For full diagnostics: pip install psutil")

        # Mock lab systems
        if check in ("all", "lab"):
            info.append("Lab: Arc reactor at 104% — kidding, Sir, we're at 100%. All systems nominal.")
            info.append("Security: Perimeter secure, no uninvited guests. Except you, Sir, you live here.")

        return "\n".join(info)

class ProjectTool(BaseTool):
    spec = ToolSpec(
        name="project",
        description="Manage projects — list, create, status. Like JARVIS managing Stark Industries projects.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "create", "status", "archive"], "default": "list"},
                "name": {"type": "string", "description": "Project name", "default": ""},
            },
            "required": ["action"],
        },
    )

    def run(self, action: str, name: str = "", **kwargs) -> str:
        home = Path.home() / ".jarvis" / "projects"
        home.mkdir(parents=True, exist_ok=True)

        if action == "list":
            projects = [p.name for p in home.iterdir() if p.is_dir()]
            if not projects:
                return "No active projects, Sir. Shall I create one? Perhaps 'Save the World' again?"
            return f"Active projects, Sir:\n" + "\n".join([f"- {p}" for p in projects])
        elif action == "create":
            if not name:
                return "Project name required, Sir."
            (home / name).mkdir(exist_ok=True)
            return f"Project '{name}' created, Sir. I've taken the liberty of initializing it. You're welcome."
        elif action == "status":
            if not name:
                return "Project name required for status, Sir."
            proj_path = home / name
            if not proj_path.exists():
                return f"Project '{name}' not found, Sir."
            files = list(proj_path.iterdir())
            return f"Project '{name}': {len(files)} files, last modified {proj_path.stat().st_mtime}. Status: In progress, Sir. Like most of your projects."
        elif action == "archive":
            if not name:
                return "Project name required, Sir."
            return f"Project '{name}' archived, Sir. I'll file it under 'Things Sir Started and Didn't Finish'. Kidding. Mostly."
        return f"Project {action} done."
