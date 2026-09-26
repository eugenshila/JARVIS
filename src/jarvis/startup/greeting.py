"""Morning greeting — Good morning Eugene, tasks alignment, personalized.

Like Iron Man: "Good morning, Sir. It's 8am, you have 3 meetings..."
But personalized: "Good morning Eugene" + ADHD-aware task alignment.

Data sources:
- Calendar tool (mock or real)
- ADHD tasks (MITs, inbox, plans)
- Memory
- Energy pattern
- Weather (if available)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

from jarvis.core.config import get_home


class MorningGreeting:
    def __init__(self, user_name: str | None = None):
        self.home = get_home()
        self.user_name = user_name or self._get_user_name()
        self.adhd_dir = self.home / "adhd"
        self.adhd_dir.mkdir(parents=True, exist_ok=True)

    def _get_user_name(self) -> str:
        # Try env, config, file, default
        if os.environ.get("JARVIS_USER"):
            return os.environ["JARVIS_USER"]
        
        # Try config file
        name_file = self.home / "user_name.txt"
        if name_file.exists():
            try:
                return name_file.read_text().strip() or "Sir"
            except:
                pass
        
        # Try git config
        try:
            import subprocess
            result = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=2)
            if result.returncode == 0 and result.stdout.strip():
                # First name only
                return result.stdout.strip().split()[0]
        except:
            pass
        
        return "Eugene"  # Default as per user request example

    def set_user_name(self, name: str):
        self.user_name = name
        (self.home / "user_name.txt").write_text(name)

    def get_greeting(self, include_tasks: bool = True, include_energy: bool = True, include_weather: bool = False) -> str:
        now = datetime.now()
        hour = now.hour
        
        if hour < 5:
            time_greet = "You're up late" if hour < 3 else "Early morning"
        elif hour < 12:
            time_greet = "Good morning"
        elif hour < 17:
            time_greet = "Good afternoon"
        elif hour < 21:
            time_greet = "Good evening"
        else:
            time_greet = "Good evening"

        # Arc reactor status (fun)
        import random
        arc = 94 + random.random()*6
        
        lines = [
            f"{time_greet}, {self.user_name}. It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}.",
            "",
            f"Arc reactor at {arc:.1f}% — kidding, Sir, we're at 100%. All systems nominal. Lab secure, perimeter clear.",
            "",
        ]

        if include_tasks:
            tasks_section = self._get_tasks_alignment()
            lines.append(tasks_section)
            lines.append("")

        if include_energy:
            energy_section = self._get_energy_suggestion()
            lines.append(energy_section)
            lines.append("")

        lines.extend([
            f"What would you like to do first, {self.user_name}?",
            "",
            "• Say 'Show my tasks' for full list",
            "• 'Focus on [MIT 1]' to start Pomodoro with body double",
            "• 'Brain dump' if mind feels full",
            "• 'System diagnostics' for full report",
            "• 'Plan my day' to re-align",
        ])

        return "\n".join(lines)

    def _get_tasks_alignment(self) -> str:
        """Get today's tasks aligned — ADHD 3 MITs + calendar + inbox."""
        tasks = []
        mits = []
        inbox_count = 0
        overdue = []

        # Load ADHD data
        def load_json(name):
            p = self.adhd_dir / name
            if p.exists():
                try:
                    return json.loads(p.read_text())
                except:
                    return []
            return []

        # MITs from plans
        plans = load_json("plans.json")
        today_str = datetime.now().date().isoformat()
        today_plans = [p for p in plans if p.get("date") == today_str]
        if today_plans:
            latest = today_plans[-1]
            mits = latest.get("mits", [])[:3]
        
        # If no MITs today, check quick inbox
        inbox = load_json("quick_inbox.json")
        inbox_count = len([i for i in inbox if not i.get("processed")])
        
        # Wins yesterday
        wins = load_json("wins.json")
        yesterday = (datetime.now() - timedelta(days=1)).date().isoformat()
        yesterday_wins = [w for w in wins if w["time"].startswith(yesterday)]
        
        # Calendar mock (in real, would use calendar tool)
        calendar_events = self._get_calendar_today()

        # Build alignment
        out = ["**Today's Alignment — 3 MITs to make today a win:**"]
        
        if mits:
            for i, mit in enumerate(mits, 1):
                out.append(f"{i}. {mit}")
        else:
            # Suggest MITs from inbox or generic
            if inbox:
                # Take top 3 from inbox
                recent_inbox = inbox[-5:]
                suggested = [item["thought"] for item in recent_inbox[:3]]
                out.append("(No MITs set yet — suggested from inbox:)")
                for i, s in enumerate(suggested, 1):
                    out.append(f"{i}. {s}")
            else:
                out.append("(No MITs set — let's pick 3 tiny wins to make today count)")
                out.append("1. Open Q4 doc (30 sec)")
                out.append("2. Reply to 1 email (5 min)")
                out.append("3. 5-min desk tidy (5 min)")

        out.append("")
        
        if calendar_events:
            out.append(f"**Schedule:** You have {len(calendar_events)} events today:")
            for ev in calendar_events[:3]:
                out.append(f"  • {ev}")
            if len(calendar_events) > 3:
                out.append(f"  • +{len(calendar_events)-3} more")
            out.append("")

        if inbox_count > 0:
            out.append(f"**Inbox:** {inbox_count} unprocessed thoughts — say 'brain dump' to organize")
            out.append("")

        if yesterday_wins:
            out.append(f"**Yesterday:** {len(yesterday_wins)} wins — {yesterday_wins[-1]['win'] if yesterday_wins else ''} (last win)")
            out.append("")

        return "\n".join(out)

    def _get_calendar_today(self) -> List[str]:
        """Mock calendar — in real would call calendar tool."""
        # Try to load from file if exists
        cal_file = self.home / "calendar_today.json"
        if cal_file.exists():
            try:
                return json.loads(cal_file.read_text())
            except:
                pass
        
        # Mock data for demo
        return [
            "10:00 AM — Q4 Planning (2 PM prep needed)",
            "2:00 PM — Q4 Planning Meeting",
            "4:30 PM — Client Call"
        ]

    def _get_energy_suggestion(self) -> str:
        """Energy pattern suggestion."""
        def load_json(name):
            p = self.adhd_dir / name
            if p.exists():
                try:
                    return json.loads(p.read_text())
                except:
                    return []
            return []

        energy_logs = load_json("energy_log.json")
        
        if energy_logs:
            # Simple pattern: avg last 3
            recent = energy_logs[-3:]
            avg_e = sum(e.get("energy", 5) for e in recent) / len(recent)
            avg_f = sum(e.get("focus", 5) for e in recent) / len(recent)
            
            if avg_e >= 7 and avg_f >= 7:
                return "**Energy:** You're usually high focus this time. Recommend tackling MIT 1 now, 45-min blocks with break alarms."
            elif avg_e <= 3:
                return "**Energy:** Pattern shows low energy mornings — start with tiny MIT (5-min tidy) + dopamine menu, then MIT 1 after walk."
            else:
                return "**Energy:** Based on pattern, steady state — Pomodoro 25/5, MIT 1 at 10-11am works well for you."
        else:
            # Default ADHD-friendly
            hour = datetime.now().hour
            if hour < 10:
                return "**Energy:** Morning — good for hardest MIT while fresh. 25-min focus, phone in other room, Sir."
            elif hour < 14:
                return "**Energy:** Midday — second wind after lunch. Good for MIT 2 or admin."
            else:
                return "**Energy:** Afternoon — energy dips normal. Tiny MIT or dopamine menu, then MIT 3 as bonus win."

    def get_evening_greeting(self) -> str:
        now = datetime.now()
        return f"Good evening, {self.user_name}. It's {now.strftime('%I:%M %p')}. Day winding down — want shutdown ritual? Log wins, preview tomorrow's MITs, permission to stop, Sir."


def get_greeting(user_name: str | None = None) -> MorningGreeting:
    return MorningGreeting(user_name=user_name)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="JARVIS Morning Greeting")
    parser.add_argument("--name", help="User name")
    parser.add_argument("--set-name", help="Set user name permanently")
    parser.add_argument("--evening", action="store_true", help="Evening greeting")
    args = parser.parse_args()

    greeting = get_greeting(args.name)
    
    if args.set_name:
        greeting.set_user_name(args.set_name)
        print(f"Name set to {args.set_name}")
    
    if args.evening:
        print(greeting.get_evening_greeting())
    else:
        print(greeting.get_greeting())
