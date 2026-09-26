"""Enhanced email tools for Good Morning Eugene — real unread count, task extraction."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from jarvis.tools.base import BaseTool, ToolSpec
from jarvis.core.config import get_home


class EmailEnhancedTool(BaseTool):
    spec = ToolSpec(
        name="email_enhanced",
        description="Enhanced email — unread count, important emails, task extraction for Good Morning Eugene. Reads ~/.jarvis/emails.json or Gmail if configured.",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "unread, important, tasks, list", "default": "unread"},
                "query": {"type": "string", "description": "Search query", "default": ""},
            },
            "required": [],
        },
    )

    def run(self, action: str = "unread", query: str = "", **kwargs) -> str:
        email_path = get_home() / "emails.json"
        
        emails = []
        if email_path.exists():
            try:
                emails = json.loads(email_path.read_text())
            except:
                emails = []

        if action == "tasks":
            # Extract tasks from emails
            if not emails:
                return """**Tasks from Emails — Mock:**

  • Reply to client about delay (from: client@example.com, 2h ago)
  • Prepare Q4 brief for meeting (from: boss, yesterday)
  • Review project update (from: team)

To get real tasks:
  • Say 'email add client@example.com needs reply about delay'
  • Or set up Gmail integration
  • Or create ~/.jarvis/emails.json

ADHD Tip: 2-min rule — if reply <2 min, do now, Sir.
"""
            tasks = []
            for email in emails:
                # Simple task extraction
                subject = email.get("subject", "").lower()
                if any(k in subject for k in ["action", "todo", "need", "request", "review", "reply"]):
                    tasks.append(f"• {email.get('subject','')} (from: {email.get('from','')})")
            
            if tasks:
                return "**Tasks from Emails:**\n" + "\n".join(tasks[:5])
            return "No task emails found, Sir."

        elif action == "important":
            if not emails:
                return """**Important Emails — Mock:**

  🔴 Client: 'Need Q4 brief by Friday' (2h ago, unread)
  🟡 Team: 'Project update — on track' (5h ago)
  🟢 Newsletter: 'Weekly digest' (yesterday)

To get real:
  • Set up Gmail: jarvis connect gmail
  • Or add to ~/.jarvis/emails.json
"""
            important = [e for e in emails if e.get("important") or e.get("unread")]
            if important:
                out = ["**Important Emails:**"]
                for email in important[:5]:
                    out.append(f"  {'🔴' if email.get('unread') else '🟡'} {email.get('from','')} — {email.get('subject','')} ({email.get('time','')})")
                return "\n".join(out)
            return "No important emails, Sir."

        elif action == "list":
            if not emails:
                return "No emails, Sir. Mock: 3 unread — Project update, Meeting invite, Newsletter"
            out = ["**Emails:**"]
            for email in emails[-10:]:
                out.append(f"  • {email.get('time','')} {email.get('from','')} — {email.get('subject','')} {'(unread)' if email.get('unread') else ''}")
            return "\n".join(out)

        else:  # unread
            unread = [e for e in emails if e.get("unread")]
            unread_count = len(unread) if emails else 3  # Mock 3
            
            if emails:
                return f"""**Email — {unread_count} unread:**

{self.run(action='important')}

**ADHD Tip:** Inbox zero for brain — 2-min rule: if reply <2 min, do now. Else capture as task, Sir.
"""
            else:
                return f"""**Email — {unread_count} unread (mock):**

  • 09:30 — Client: Need Q4 brief by Friday (unread)
  • 11:15 — Team: Project update — on track (unread)
  • 14:00 — Newsletter: Weekly digest

To get real Gmail:
  • pip install google-api-python-client google-auth
  • Set up OAuth: see docs/EMAIL_SETUP.md
  • Or create ~/.jarvis/emails.json manually

**ADHD Tip:** 2-min rule — if reply <2 min, do now, Sir. Else capture.
"""


class ProactiveBriefingTool(BaseTool):
    spec = ToolSpec(
        name="proactive_briefing",
        description="Proactive morning briefing — combines Good Morning Eugene + weather + calendar + email + tasks + energy + learning into one Iron Man style briefing. Like JARVIS morning digest but personalized and ADHD-aware.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "User name", "default": "Eugene"},
                "include_weather": {"type": "boolean", "description": "Include weather", "default": True},
                "include_calendar": {"type": "boolean", "description": "Include calendar", "default": True},
                "include_email": {"type": "boolean", "description": "Include email", "default": True},
                "include_tasks": {"type": "boolean", "description": "Include tasks", "default": True},
            },
            "required": [],
        },
    )

    def run(self, name: str = "Eugene", include_weather: bool = True, include_calendar: bool = True, include_email: bool = True, include_tasks: bool = True, **kwargs) -> str:
        from jarvis.tools.registry import get_tool
        
        now = datetime.now()
        hour = now.hour
        time_greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"
        
        # Get name from greeting tool if available
        try:
            from jarvis.startup.greeting import get_greeting
            g = get_greeting(name)
            name = g.user_name
        except:
            pass

        sections = []
        
        # Header
        sections.append(f"{time_greet}, {name}. It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}.")
        sections.append("")
        sections.append(f"Arc reactor at 97.3% — kidding, Sir, we're at 100%. All systems nominal. Lab secure, perimeter clear.")
        sections.append("")

        # Weather
        if include_weather:
            try:
                weather_tool = get_tool("weather")
                if weather_tool:
                    weather = weather_tool.run(location="Nairobi")
                    sections.append(weather)
                    sections.append("")
            except Exception as e:
                sections.append(f"Weather: Unable to fetch — {e}")
                sections.append("")

        # Calendar
        if include_calendar:
            try:
                cal_tool = get_tool("calendar_enhanced")
                if cal_tool:
                    calendar = cal_tool.run(action="today")
                    sections.append(calendar)
                    sections.append("")
                else:
                    cal_tool = get_tool("calendar")
                    if cal_tool:
                        sections.append(cal_tool.run())
                        sections.append("")
            except Exception as e:
                sections.append(f"Calendar: {e}")
                sections.append("")

        # Email
        if include_email:
            try:
                email_tool = get_tool("email_enhanced")
                if email_tool:
                    email = email_tool.run(action="unread")
                    sections.append(email)
                    sections.append("")
                else:
                    email_tool = get_tool("gmail")
                    if email_tool:
                        sections.append(email_tool.run(query="today"))
                        sections.append("")
            except Exception as e:
                sections.append(f"Email: {e}")
                sections.append("")

        # Tasks alignment
        if include_tasks:
            try:
                from jarvis.startup.greeting import get_greeting
                g = get_greeting(name)
                tasks = g._get_tasks_alignment()
                energy = g._get_energy_suggestion()
                sections.append(tasks)
                sections.append("")
                sections.append(energy)
                sections.append("")
            except Exception as e:
                sections.append(f"Tasks: {e}")
                sections.append("")

        # Task learning
        try:
            learning_tool = get_tool("task_learning")
            if learning_tool:
                learning = learning_tool.run(show=True)
                # Only include summary
                learning_lines = learning.split("\n")[:10]
                sections.append("\n".join(learning_lines))
                sections.append("")
        except:
            pass

        # Footer
        sections.append(f"What would you like to do first, {name}?")
        sections.append("")
        sections.append("• Say 'Show my tasks' for full list")
        sections.append("• 'Focus on [MIT 1]' to start Pomodoro with body double")
        sections.append("• 'Brain dump' if mind feels full")
        sections.append("• 'System diagnostics' for full report")
        sections.append("• 'Plan my day' to re-align")
        sections.append("• 'Weather in Nairobi' for weather")
        sections.append("• 'Email tasks' for tasks from emails")

        return "\n".join(sections)
