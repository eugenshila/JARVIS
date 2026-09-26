"""Calendar and weather tools for Good Morning Eugene — real task alignment."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from jarvis.tools.base import BaseTool, ToolSpec
from jarvis.core.config import get_home


class CalendarToolEnhanced(BaseTool):
    spec = ToolSpec(
        name="calendar_enhanced",
        description="Enhanced calendar — today's events, task alignment, Good Morning Eugene schedule. Reads from ~/.jarvis/calendar.json or Google Calendar if configured.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "today, add, list", "default": "today"},
                "event": {"type": "string", "description": "Event to add", "default": ""},
                "time": {"type": "string", "description": "Event time e.g. 2pm", "default": ""},
            },
            "required": [],
        },
    )

    def run(self, action: str = "today", event: str = "", time: str = "", **kwargs) -> str:
        cal_path = get_home() / "calendar.json"
        
        # Load calendar
        events = []
        if cal_path.exists():
            try:
                events = json.loads(cal_path.read_text())
            except:
                events = []

        if action == "add" and event:
            new_event = {
                "time": time or datetime.now().strftime("%I:%M %p"),
                "title": event,
                "date": datetime.now().date().isoformat(),
                "created": datetime.now().isoformat()
            }
            events.append(new_event)
            cal_path.write_text(json.dumps(events[-100:], indent=2))
            return f"Added to calendar: {time} — {event}"

        elif action == "list":
            if not events:
                return "No calendar events, Sir."
            out = ["**Calendar Events:**"]
            for ev in events[-10:]:
                out.append(f"  • {ev.get('date','')} {ev.get('time','')} — {ev.get('title','')}")
            return "\n".join(out)

        else:  # today
            today_str = datetime.now().date().isoformat()
            today_events = [e for e in events if e.get("date") == today_str]
            
            if not today_events:
                # Check if Google Calendar configured
                if os.environ.get("GOOGLE_CALENDAR_ID"):
                    return self._get_google_calendar()
                
                # Mock for demo
                return """**Today's Schedule — Mock (set up real calendar):**

  • 10:00 AM — Q4 Planning Prep (need 30m before 2pm meeting)
  • 2:00 PM — Q4 Planning Meeting (with team, 60m)
  • 4:30 PM — Client Call (follow-up on delay)

To add real calendar:
  • Say 'calendar add Q4 meeting at 2pm'
  • Or set GOOGLE_CALENDAR_ID env + google calendar integration
  • Or create ~/.jarvis/calendar.json

**ADHD Tip:** Time block 45m for Q4 prep before 2pm meeting, Sir. Add 10m buffer.
"""
            
            out = [f"**Today's Schedule — {len(today_events)} events:**", ""]
            for ev in today_events:
                out.append(f"  • {ev.get('time','')} — {ev.get('title','')}")
            return "\n".join(out)

    def _get_google_calendar(self) -> str:
        """Try Google Calendar API."""
        try:
            # This would need google-api-python-client
            return "Google Calendar integration — needs google-api-python-client + credentials. For now using local calendar.json"
        except Exception as e:
            return f"Google Calendar failed: {e}, using local"


class WeatherTool(BaseTool):
    spec = ToolSpec(
        name="weather",
        description="Weather for Good Morning Eugene — today's weather for task planning. Uses wttr.in (no key) or OpenWeatherMap if OPENWEATHER_API_KEY set.",
        parameters={
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Location e.g. Nairobi", "default": "Nairobi"},
            },
            "required": [],
        },
    )

    def run(self, location: str = "Nairobi", **kwargs) -> str:
        # Try wttr.in (free, no key, works offline-ish)
        try:
            import httpx
            # wttr.in returns text
            resp = httpx.get(f"https://wttr.in/{location}?format=%C+%t+%w+%h", timeout=5)
            if resp.status_code == 200:
                weather_text = resp.text.strip()
                return f"**Weather in {location}:** {weather_text}\n\nADHD Tip: If sunny, walk outside for dopamine before MIT 1, Sir."
        except Exception as e:
            print(f"wttr.in failed: {e}")

        # Try OpenWeatherMap if key
        api_key = os.environ.get("OPENWEATHER_API_KEY")
        if api_key:
            try:
                import httpx
                resp = httpx.get(f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    temp = data["main"]["temp"]
                    desc = data["weather"][0]["description"]
                    return f"**Weather in {location}:** {desc}, {temp}°C"
            except Exception as e:
                return f"Weather API failed: {e}"

        # Fallback mock
        return f"""**Weather in {location}:** Mock — Sunny 24°C, light breeze

To get real weather:
  • Free: Uses wttr.in automatically (no key needed, needs internet)
  • Or set OPENWEATHER_API_KEY env for OpenWeatherMap

ADHD Tip: Sunny day — 5-min walk outside before MIT 1 for dopamine, Sir.
"""


class TaskLearningTool(BaseTool):
    spec = ToolSpec(
        name="task_learning",
        description="Learns your energy patterns and task completion — suggests best MIT time, focus length, what works for you. Like JARVIS learning Tony's patterns.",
        parameters={
            "type": "object",
            "properties": {
                "show": {"type": "boolean", "description": "Show learned patterns", "default": True},
            },
            "required": [],
        },
    )

    def run(self, show: bool = True, **kwargs) -> str:
        adhd_dir = get_home() / "adhd"
        
        def load_json(name):
            p = adhd_dir / name
            if p.exists():
                try:
                    return json.loads(p.read_text())
                except:
                    return []
            return []

        wins = load_json("wins.json")
        energy_logs = load_json("energy_log.json")
        focus_sessions = load_json("focus_sessions.json")
        plans = load_json("plans.json")

        if not wins and not energy_logs:
            return """**Task Learning — Not enough data yet, Sir.**

Start logging and I'll learn your patterns:

  • Log wins: `log win opened doc` — I track when you win
  • Energy checks: `energy check 5 6 calm` — I learn your rhythm
  • Focus sessions: `focus on Q4 brief` — I learn best focus length
  • Day plans: `plan my day MITs: ...` — I learn what MITs work

After 1 week, I'll tell you:
  • Best time for MIT 1 (usually 10-11am for most)
  • Best focus length (15, 25, or 45 min for you)
  • Top distractions and how to fix
  • Energy pattern (high mornings? low afternoons?)

ADHD brain has rhythm, Sir. Not random. Let's find yours.
"""

        # Analyze
        from collections import Counter
        from datetime import datetime
        
        # Energy by hour
        hour_energy = {}
        for log in energy_logs:
            try:
                hour = datetime.fromisoformat(log["time"]).hour
                if hour not in hour_energy:
                    hour_energy[hour] = []
                hour_energy[hour].append(log.get("energy", 5))
            except:
                pass
        
        best_hour = None
        if hour_energy:
            avg_by_hour = {h: sum(v)/len(v) for h, v in hour_energy.items()}
            best_hour = max(avg_by_hour, key=avg_by_hour.get)
        
        # Focus length success
        focus_lengths = [f.get("duration", 25) for f in focus_sessions]
        most_common_focus = Counter(focus_lengths).most_common(1)
        
        # Wins by day of week
        wins_by_dow = Counter()
        for w in wins:
            try:
                dow = datetime.fromisoformat(w["time"]).strftime("%A")
                wins_by_dow[dow] += 1
            except:
                pass

        out = [
            f"🧠 **Task Learning — Your Patterns, Sir**\n",
            f"**Data:** {len(wins)} wins, {len(energy_logs)} energy checks, {len(focus_sessions)} focus sessions",
            "",
        ]

        if best_hour is not None:
            out.append(f"**Best Energy Hour:** {best_hour}:00 — {best_hour+1}:00 (avg {avg_by_hour[best_hour]:.1f}/10)")
            out.append(f"  → Schedule MIT 1 then, Sir.")
            out.append("")

        if most_common_focus:
            out.append(f"**Best Focus Length:** {most_common_focus[0][0]} min (used {most_common_focus[0][1]} times)")
            out.append(f"  → Your brain likes {most_common_focus[0][0]} min sprints")
            out.append("")

        if wins_by_dow:
            best_day = wins_by_dow.most_common(1)[0]
            out.append(f"**Best Day:** {best_day[0]} ({best_day[1]} wins)")
            out.append("")

        out.extend([
            "**Recommendations for You:**",
            "  • Based on data, not guesswork",
        ])

        if best_hour and best_hour < 11:
            out.append("  • You're morning person — MIT 1 at 10am, MIT 2 after lunch")
        elif best_hour and best_hour >= 14:
            out.append("  • You're afternoon person — admin morning, MITs afternoon")

        out.extend([
            "",
            "**Next:** Keep logging wins + energy checks. I'll get smarter, Sir.",
            "Say `weekly review` for full weekly patterns.",
        ])

        return "\n".join(out)
