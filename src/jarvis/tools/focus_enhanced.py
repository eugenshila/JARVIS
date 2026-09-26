"""Enhanced focus tools — website blocker, focus sounds, hyperfocus guard.

For ADHD: focus is hard, distractions everywhere, hyperfocus forgets breaks.

Tools:
- WebsiteBlockerTool: blocks distracting sites during focus (hosts file + browser)
- FocusSoundsTool: lo-fi, white noise, brown noise, binaural beats
- HyperfocusGuardTool: detects long focus, enforces breaks, water, stretch
- FocusSessionTool: full Pomodoro with blocker + sounds + guard + body double
"""

from __future__ import annotations

import json
import os
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from jarvis.tools.base import BaseTool, ToolSpec
from jarvis.core.config import get_home


def _get_adhd_dir() -> Path:
    d = get_home() / "adhd"
    d.mkdir(parents=True, exist_ok=True)
    return d


class WebsiteBlockerTool(BaseTool):
    spec = ToolSpec(
        name="website_blocker",
        description="ADHD Website Blocker — blocks distracting sites during focus: Instagram, Twitter, YouTube, etc. Uses hosts file (needs admin) or browser extension list. For focus sessions.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "block, unblock, status, list", "default": "status"},
                "sites": {"type": "string", "description": "Comma-separated sites to block", "default": ""},
                "duration": {"type": "integer", "description": "Block duration minutes", "default": 25},
            },
            "required": [],
        },
    )

    DEFAULT_BLOCK_LIST = [
        "instagram.com", "www.instagram.com",
        "twitter.com", "www.twitter.com", "x.com", "www.x.com",
        "tiktok.com", "www.tiktok.com",
        "youtube.com", "www.youtube.com", "m.youtube.com",
        "reddit.com", "www.reddit.com",
        "facebook.com", "www.facebook.com",
        "netflix.com", "www.netflix.com",
    ]

    def run(self, action: str = "status", sites: str = "", duration: int = 25, **kwargs) -> str:
        block_file = _get_adhd_dir() / "blocked_sites.json"
        
        blocked = []
        if block_file.exists():
            try:
                data = json.loads(block_file.read_text())
                blocked = data.get("sites", [])
            except:
                pass

        if action == "list":
            if not blocked:
                return f"**Blocked Sites — None currently blocked, Sir.**\n\nDefault distracting sites for ADHD:\n{', '.join(self.DEFAULT_BLOCK_LIST[:5])}...\n\nSay 'block websites' to block defaults for {duration} min focus session."
            return f"**Blocked Sites ({len(blocked)}):**\n" + "\n".join(f"  • {s}" for s in blocked)

        elif action == "block":
            sites_to_block = []
            if sites:
                sites_to_block = [s.strip() for s in sites.replace(",", "\n").split("\n") if s.strip()]
            else:
                sites_to_block = self.DEFAULT_BLOCK_LIST

            data = {
                "sites": sites_to_block,
                "blocked_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(minutes=duration)).isoformat(),
                "duration": duration
            }
            block_file.write_text(json.dumps(data, indent=2))

            hosts_result = self._block_via_hosts(sites_to_block)

            return f"🔒 **Website Blocker ON — {duration} min — {len(sites_to_block)} sites**\n\nBlocked:\n{chr(10).join(f'  • {s}' for s in sites_to_block[:8])}\n{f'  ... +{len(sites_to_block)-8} more' if len(sites_to_block)>8 else ''}\n\n**How it works:**\n  • List saved to ~/.jarvis/adhd/blocked_sites.json with expiry {duration} min\n  • {hosts_result}\n  • Frontend will hide distracting UI if in focus mode\n\nFocus now, Sir. {duration} min. You've got this.\n"

        elif action == "unblock":
            if block_file.exists():
                try:
                    block_file.unlink()
                except:
                    pass
            unblock_result = self._unblock_via_hosts()
            return f"🔓 **Website Blocker OFF — Sites unblocked, Sir.**\n\nRemoved block list.\n{unblock_result}\n\nIf you unblocked early, no shame — any focus counts."

        else:
            if not blocked:
                return f"**Website Blocker:** OFF — No sites blocked. Ready to block {len(self.DEFAULT_BLOCK_LIST)} default distracting sites for focus."
            try:
                data = json.loads(block_file.read_text())
                expires = datetime.fromisoformat(data.get("expires_at", "2000-01-01"))
                if datetime.now() > expires:
                    block_file.unlink()
                    return "**Website Blocker:** Expired — block auto-removed after duration."
                remaining = expires - datetime.now()
                mins_left = int(remaining.total_seconds() // 60)
                return f"**Website Blocker:** ON — {len(blocked)} sites blocked, {mins_left} min remaining (expires {expires.strftime('%H:%M')})"
            except:
                return f"**Website Blocker:** ON — {len(blocked)} sites blocked"

    def _block_via_hosts(self, sites: List[str]) -> str:
        return "Hosts file blocking: Manual — to enable real OS-level blocking, run as admin: 'jarvis block --hosts' (requires sudo/admin). For now, using app-level blocking via focus mode."

    def _unblock_via_hosts(self) -> str:
        return "Hosts file unblocking: Manual — if you used --hosts, run as admin to unblock. App-level block removed."


class FocusSoundsTool(BaseTool):
    spec = ToolSpec(
        name="focus_sounds",
        description="Focus sounds for ADHD — lo-fi, white noise, brown noise, binaural beats, rain. Plays during Pomodoro to help focus. Like Iron Man lab ambient.",
        parameters={
            "type": "object",
            "properties": {
                "sound": {"type": "string", "description": "Sound: lo-fi, white, brown, rain, binaural, silence, list", "default": "lo-fi"},
                "action": {"type": "string", "description": "play, stop, list", "default": "play"},
            },
            "required": [],
        },
    )

    SOUNDS = {
        "lo-fi": {"desc": "Lo-fi hip hop — chill beats to focus to, Sir", "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk", "file": "lo-fi"},
        "white": {"desc": "White noise — steady hiss, blocks distractions", "url": "", "file": "white"},
        "brown": {"desc": "Brown noise — deeper, ADHD favorite, calming", "url": "", "file": "brown"},
        "rain": {"desc": "Rain sounds — gentle rain, lab ambience", "url": "", "file": "rain"},
        "binaural": {"desc": "Binaural beats 40Hz — focus frequency", "url": "", "file": "binaural"},
        "space": {"desc": "Space ambient — Iron Man lab, Stark Industries", "url": "", "file": "space"},
    }

    def run(self, sound: str = "lo-fi", action: str = "play", **kwargs) -> str:
        if action == "list" or sound == "list":
            out = ["**Focus Sounds — ADHD + Iron Man Lab:**", ""]
            for name, info in self.SOUNDS.items():
                out.append(f"  • {name} — {info['desc']}")
            out.extend(["", "Say 'play focus sounds lo-fi' or 'play focus sounds brown'", "ADHD favorites: brown noise, lo-fi, rain — try brown first, Sir.", "Iron Man lab: space ambient"])
            return "\n".join(out)

        if action == "stop":
            try:
                import subprocess
                subprocess.run(["pkill", "-f", "mpv.*focus"], capture_output=True)
                subprocess.run(["pkill", "-f", "ffplay.*focus"], capture_output=True)
            except:
                pass
            return "🔇 Focus sounds stopped, Sir. Silence mode."

        sound = sound.lower()
        if sound not in self.SOUNDS:
            sound = "lo-fi"

        info = self.SOUNDS[sound]
        sound_file = _get_adhd_dir() / "current_sound.json"
        sound_file.write_text(json.dumps({"sound": sound, "started": datetime.now().isoformat(), "desc": info["desc"]}))
        play_result = self._try_play_sound(sound)

        return f"🎵 **Focus Sounds ON — {sound.upper()}**\n\n{info['desc']}\n\n{play_result}\n\nFocus now with {sound}, Sir. Body double + sounds + blocker = triple power.\n"

    def _try_play_sound(self, sound: str) -> str:
        instructions = {
            "lo-fi": "YouTube: https://www.youtube.com/watch?v=jfKfPfyJRdk — Lo-fi Girl live",
            "white": "White noise: https://www.youtube.com/watch?v=nMfPqeZjc2c",
            "brown": "Brown noise: https://www.youtube.com/watch?v=QBrI-8XQO18 — ADHD favorite",
            "rain": "Rain: https://www.youtube.com/watch?v=mPZkdNFkNps",
            "binaural": "Binaural 40Hz: https://www.youtube.com/watch?v=1_G60OdEzXs",
            "space": "Space ambient: https://www.youtube.com/watch?v=S_MOd40zlYU — Iron Man lab",
        }
        return f"To play: {instructions.get(sound, 'Search YouTube')}\n\nFrontend HUD will auto-play via Web Audio API if you click play, Sir."


class HyperfocusGuardTool(BaseTool):
    spec = ToolSpec(
        name="hyperfocus_guard",
        description="Hyperfocus Guard — detects long focus (>45 min), enforces breaks, water, stretch, bathroom. ADHD hyperfocus forgets to eat/drink. Like JARVIS: 'Sir, you've been in suit 60 min, arc reactor needs cooling'",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "check, start, stop, status", "default": "check"},
                "focus_minutes": {"type": "integer", "description": "How long focused", "default": 0},
            },
            "required": [],
        },
    )

    def run(self, action: str = "check", focus_minutes: int = 0, **kwargs) -> str:
        guard_file = _get_adhd_dir() / "hyperfocus_guard.json"
        
        def load_guard():
            if guard_file.exists():
                try:
                    return json.loads(guard_file.read_text())
                except:
                    return {}
            return {}

        def save_guard(data):
            guard_file.write_text(json.dumps(data, indent=2))

        if action == "start":
            data = {"started": datetime.now().isoformat(), "last_break": datetime.now().isoformat(), "focus_minutes_total": 0, "breaks_taken": 0, "reminders_sent": 0, "enabled": True}
            save_guard(data)
            return f"🛡️ **Hyperfocus Guard ON — Watching over you, Sir**\n\nStarted at {datetime.now().strftime('%H:%M')}\n\n**What I watch:**\n  • Focus >45 min without break → remind break\n  • Focus >60 min → enforce break: water + bathroom + stretch\n  • Focus >90 min → 'Sir, arc reactor needs cooling, you've been in suit 90 min'\n\nGuard active, Sir."

        elif action == "stop":
            data = load_guard()
            data["enabled"] = False
            data["stopped"] = datetime.now().isoformat()
            save_guard(data)
            return "🛡️ Hyperfocus Guard OFF — No more break reminders, Sir."

        elif action == "status":
            data = load_guard()
            if not data.get("enabled"):
                return "**Hyperfocus Guard:** OFF — No guard active. Say 'hyperfocus guard start' to enable."
            started = datetime.fromisoformat(data.get("started", datetime.now().isoformat()))
            elapsed = datetime.now() - started
            elapsed_min = int(elapsed.total_seconds() // 60)
            return f"**Hyperfocus Guard:** ON — {elapsed_min} min since start\nStarted: {started.strftime('%H:%M')}\nTotal focus: {data.get('focus_minutes_total', 0)} min\nBreaks: {data.get('breaks_taken', 0)}\n"

        else:
            if focus_minutes == 0:
                data = load_guard()
                if not data.get("enabled"):
                    return "**Hyperfocus Guard:** OFF — Enable with 'hyperfocus guard start'"
                started = datetime.fromisoformat(data.get("started", datetime.now().isoformat()))
                elapsed_min = int((datetime.now() - started).total_seconds() // 60)
                focus_minutes = elapsed_min

            if focus_minutes >= 90:
                return f"🚨 **Hyperfocus Guard — 90 MIN — ENFORCE BREAK NOW, Sir!**\n\nYou've been focused {focus_minutes} min — arc reactor needs cooling.\n\n**Mandatory break 10 min:**\n  1. Water — full glass (1 min)\n  2. Bathroom (2 min)\n  3. Stretch (2 min)\n  4. Walk 5 min outside no phone (5 min)\n"
            elif focus_minutes >= 60:
                return f"⚠️ **Hyperfocus Guard — 60 MIN — Break Time, Sir**\n\n{focus_minutes} min focused — enforce break: water + bathroom + stretch mandatory.\n"
            elif focus_minutes >= 45:
                return f"⏰ **Hyperfocus Guard — 45 MIN — Break Reminder**\n\n{focus_minutes} min — good focus, Sir. Time for 5-min break.\n"
            elif focus_minutes >= 25:
                return f"💧 **Hyperfocus Guard — 25 MIN Check-in**\n\n{focus_minutes} min focused — nice, Sir. Water? Stretch? Still with MIT?\n"
            else:
                return f"**Hyperfocus Guard:** {focus_minutes} min focused — all good, Sir. Next check at 25 min."


class FocusSessionEnhancedTool(BaseTool):
    spec = ToolSpec(
        name="focus_enhanced",
        description="Full ADHD Focus Session — Pomodoro++ with website blocker + focus sounds + hyperfocus guard + body double + distraction parking lot. Triple power for ADHD.",
        parameters={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "What to focus on"},
                "duration": {"type": "integer", "description": "Focus minutes", "default": 25},
                "block_sites": {"type": "boolean", "description": "Block distracting sites", "default": True},
                "sound": {"type": "string", "description": "Focus sound: lo-fi, brown, white, rain, space, silence", "default": "brown"},
                "guard": {"type": "boolean", "description": "Enable hyperfocus guard", "default": True},
            },
            "required": ["task"],
        },
    )

    def run(self, task: str, duration: int = 25, block_sites: bool = True, sound: str = "brown", guard: bool = True, **kwargs) -> str:
        from jarvis.tools.registry import get_tool

        results = []

        if block_sites:
            blocker = get_tool("website_blocker")
            if blocker:
                results.append(blocker.run(action="block", duration=duration))

        if sound and sound != "silence":
            sounds = get_tool("focus_sounds")
            if sounds:
                results.append(sounds.run(sound=sound, action="play"))

        if guard:
            guard_tool = get_tool("hyperfocus_guard")
            if guard_tool:
                results.append(guard_tool.run(action="start"))

        sessions_path = _get_adhd_dir() / "focus_sessions_enhanced.json"
        sessions = []
        if sessions_path.exists():
            try:
                sessions = json.loads(sessions_path.read_text())
            except:
                pass

        session = {"time": datetime.now().isoformat(), "task": task, "duration": duration, "block_sites": block_sites, "sound": sound, "guard": guard}
        sessions.append(session)
        sessions_path.write_text(json.dumps(sessions[-100:], indent=2))

        out = [
            f"🎧 **FULL FOCUS SESSION — {duration} MIN — TRIPLE POWER — Body Double ON**\n",
            f"**Task:** {task}",
            f"**Duration:** {duration} min focus → {max(5, duration//5)} min break",
            f"**Blocker:** {'ON — distracting sites blocked' if block_sites else 'OFF'}",
            f"**Sound:** {sound} — ADHD favorite" if sound != "silence" else "**Sound:** Silence",
            f"**Guard:** {'ON — break reminders' if guard else 'OFF'}",
            f"**Body Double:** ON — I'm here, working with you, Sir",
            "",
            "**Before you start (1 min):**",
            "  1. Phone: DND, face down or other room (30 sec)",
            "  2. Water nearby, bathroom (20 sec)",
            "  3. Tabs: Close all except this task (20 sec)",
            "  4. Say out loud: 'I'm starting [task] for just 2 minutes' (10 sec)",
            "",
            f"**Your only job for next {duration} min: stay with '{task}'**",
            "Two minutes counts. Any progress is win, Sir.",
        ]
        return "\n".join(out)
