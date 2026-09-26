"""ADHD-focused tools — built for executive dysfunction, time blindness, overwhelm.

These are the core of JARVIS as ADHD co-pilot. Every tool is designed for low friction,
dopamine-friendly, and overwhelm-proof.

Tools:
- BrainDumpTool: dump everything, get organized
- TaskBreakdownTool: atomize big scary tasks into 2-min steps
- DayPlannerTool: ADHD-friendly day plan (3 MITs, energy matching, time blocking)
- FocusTool: Pomodoro++ with body doubling
- QuickCaptureTool: zero-friction capture
- EnergyCheckTool: energy/mood -> task matching
- WinTrackerTool: track tiny wins for dopamine
- OverwhelmTool: SOS when overwhelmed
- TimeEstimatorTool: time blindness antidote
"""

from __future__ import annotations

import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from jarvis.tools.base import BaseTool, ToolSpec
from jarvis.core.config import get_home


def _get_adhd_dir() -> Path:
    d = get_home() / "adhd"
    d.mkdir(parents=True, exist_ok=True)
    return d


class BrainDumpTool(BaseTool):
    spec = ToolSpec(
        name="brain_dump",
        description="ADHD brain dump: dump everything on your mind, JARVIS organizes into categories, priorities, and next actions. For when your brain feels full.",
        parameters={
            "type": "object",
            "properties": {
                "dump": {"type": "string", "description": "Everything on your mind, messy is fine"},
                "save": {"type": "boolean", "description": "Save to inbox", "default": True},
            },
            "required": ["dump"],
        },
    )

    def run(self, dump: str, save: bool = True, **kwargs) -> str:
        if not dump.strip():
            return "Brain empty? That's a win, Sir. Or you're holding out on me."

        # Simple heuristic organization (in real agent, LLM does better)
        lines = [l.strip() for l in dump.replace(",", "\n").split("\n") if l.strip()]
        
        categories = {
            "🔥 Urgent / Today": [],
            "📌 Important / This Week": [],
            "💡 Ideas / Someday": [],
            "🏠 Home / Life": [],
            "💼 Work / Project": [],
            "📧 Comms / People": [],
        }
        
        urgent_keywords = ["today", "urgent", "asap", "deadline", "due", "now", "call", "email"]
        idea_keywords = ["maybe", "idea", "someday", "wish", "could", "want to"]
        home_keywords = ["home", "clean", "buy", "grocery", "laundry", "cook", "family", "kids"]
        work_keywords = ["project", "work", "code", "report", "meeting", "client", "q4", "plan"]
        comm_keywords = ["email", "call", "text", "message", "reply", "ask", "tell"]

        for item in lines:
            low = item.lower()
            if any(k in low for k in urgent_keywords):
                categories["🔥 Urgent / Today"].append(item)
            elif any(k in low for k in idea_keywords):
                categories["💡 Ideas / Someday"].append(item)
            elif any(k in low for k in home_keywords):
                categories["🏠 Home / Life"].append(item)
            elif any(k in low for k in work_keywords):
                categories["💼 Work / Project"].append(item)
            elif any(k in low for k in comm_keywords):
                categories["📧 Comms / People"].append(item)
            else:
                categories["📌 Important / This Week"].append(item)

        # Save
        if save:
            inbox_path = _get_adhd_dir() / "inbox.json"
            inbox = []
            if inbox_path.exists():
                try:
                    inbox = json.loads(inbox_path.read_text())
                except:
                    inbox = []
            inbox.append({"time": datetime.now().isoformat(), "raw": dump, "organized": categories})
            inbox_path.write_text(json.dumps(inbox[-50:], indent=2))

        # Format output ADHD-friendly: clear, not overwhelming, next action obvious
        out = ["🧠 **Brain Dump Organized, Sir.**\n", f"You dumped {len(lines)} things. Let's make sense of it:\n"]
        for cat, items in categories.items():
            if items:
                out.append(f"**{cat}** ({len(items)})")
                for it in items[:5]:
                    out.append(f"  • {it}")
                if len(items) > 5:
                    out.append(f"  ... +{len(items)-5} more")
                out.append("")

        out.append("---")
        out.append("**Next:** Pick ONE from 🔥 Urgent. Just one. Say `break down [task]` to atomize it.")
        out.append("Tip: Your brain is not a storage device, Sir. It's a processor. Good dump.")
        
        return "\n".join(out)


class TaskBreakdownTool(BaseTool):
    spec = ToolSpec(
        name="task_breakdown",
        description="ADHD Task Atomizer: breaks any big scary task into tiny 2-5 min micro-steps. Makes starting less scary. The secret to beating executive dysfunction.",
        parameters={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "The big scary task"},
                "context": {"type": "string", "description": "Any context", "default": ""},
            },
            "required": ["task"],
        },
    )

    def run(self, task: str, context: str = "", **kwargs) -> str:
        if not task.strip():
            return "No task? No breakdown needed. You're free, Sir."

        # Heuristic breakdown - LLM agent will do smarter
        task_lower = task.lower()
        
        # Generic atomization template
        steps = []
        
        if "write" in task_lower or "report" in task_lower or "email" in task_lower or "brief" in task_lower:
            steps = [
                f"1. Open doc/app for '{task}' (30 sec) - just open it",
                f"2. Write terrible first line - doesn't matter (2 min)",
                f"3. Bullet 3 main points you want to make (3 min)",
                f"4. Expand first bullet into 2 sentences (5 min)",
                f"5. Expand second bullet (5 min)",
                f"6. Expand third bullet (5 min)",
                f"7. Read aloud once, fix typos (3 min)",
                f"8. Send/share - done is better than perfect (1 min)",
            ]
        elif "clean" in task_lower or "organize" in task_lower or "tidy" in task_lower:
            steps = [
                f"1. Set timer 5 min, put on music (30 sec)",
                f"2. Grab trash bag, collect obvious trash in area (3 min)",
                f"3. Put 5 things back where they belong (2 min)",
                f"4. One surface - wipe it (2 min)",
                f"5. Take before/after photo for dopamine (30 sec)",
                f"6. Decide: continue 5 more min or stop with win? (30 sec)",
            ]
        elif "project" in task_lower or "plan" in task_lower:
            steps = [
                f"1. Open blank note, title '{task}' (1 min)",
                f"2. What does DONE look like? Write 1 sentence (2 min)",
                f"3. List 3-5 ingredients needed for done (3 min)",
                f"4. What's the FIRST tiny step? Circle it (1 min)",
                f"5. Do that first step now, just 2 min (2 min)",
                f"6. Check off, dopamine hit (30 sec)",
            ]
        elif "call" in task_lower or "meeting" in task_lower:
            steps = [
                f"1. Find number/link for '{task}' (1 min)",
                f"2. Write 2 bullet points: why calling + what you need (2 min)",
                f"3. Water, deep breath (30 sec)",
                f"4. Hit call/join - you can leave after 2 min if needed (1 min)",
                f"5. Say your 2 bullets (2 min)",
                f"6. Done. Log outcome in 1 sentence (1 min)",
            ]
        else:
            steps = [
                f"1. Define DONE for '{task}' in 10 words or less (2 min)",
                f"2. What's blocking you? Name it (1 min)",
                f"3. Smallest possible first move? (1 min)",
                f"4. Prepare environment: open app, close distractions (2 min)",
                f"5. Do first move for just 2 minutes - timer on (2 min)",
                f"6. Check: continue or pause? You have permission to pause (30 sec)",
                f"7. If continue, next micro-step is... (1 min)",
                f"8. Finish or park with note for future you (1 min)",
            ]

        # Save breakdown
        breakdowns_path = _get_adhd_dir() / "breakdowns.json"
        breakdowns = []
        if breakdowns_path.exists():
            try:
                breakdowns = json.loads(breakdowns_path.read_text())
            except:
                pass
        breakdowns.append({"time": datetime.now().isoformat(), "task": task, "steps": steps, "context": context})
        breakdowns_path.write_text(json.dumps(breakdowns[-30:], indent=2))

        out = [
            f"🔬 **Atomized: {task}**\n",
            f"Big task scary. Tiny tasks doable. Here's your micro-steps (each 2-5 min):\n"
        ]
        out.extend(steps)
        out.extend([
            "",
            "---",
            "**ADHD Pro Tips, Sir:**",
            "• Don't do all steps now. Do step 1 only. That's a win.",
            "• 2-minute rule: If you can start in 2 min, you win.",
            "• Body double: Say `body double` and I'll stay with you.",
            "• Stuck? Say `overwhelm` for SOS.",
            "",
            f"**Next action:** {steps[0]}",
        ])
        return "\n".join(out)


class DayPlannerTool(BaseTool):
    spec = ToolSpec(
        name="day_planner",
        description="ADHD-friendly day planner: 3 MITs max, energy matching, time blocking with buffers, includes breaks/meals/transitions. Prevents over-planning.",
        parameters={
            "type": "object",
            "properties": {
                "mits": {"type": "string", "description": "Your 3 Most Important Tasks (comma or newline separated). Max 3!"},
                "energy": {"type": "string", "description": "Current energy: low, medium, high", "default": "medium"},
                "must_dos": {"type": "string", "description": "Must-do appointments/meetings today", "default": ""},
                "available_hours": {"type": "string", "description": "Hours available e.g. 9am-5pm", "default": "9am-5pm"},
            },
            "required": ["mits"],
        },
    )

    def run(self, mits: str, energy: str = "medium", must_dos: str = "", available_hours: str = "9am-5pm", **kwargs) -> str:
        mit_list = [m.strip() for m in mits.replace(",", "\n").split("\n") if m.strip()][:3]
        if len(mit_list) > 3:
            mit_list = mit_list[:3]
        
        if not mit_list:
            return "No MITs? That's okay, Sir. Let's pick 3 that would make today feel like a win, even if small."

        must_list = [m.strip() for m in must_dos.replace(",", "\n").split("\n") if m.strip()] if must_dos else []

        energy = energy.lower()
        if energy not in ("low", "medium", "high"):
            energy = "medium"

        # Energy-based suggestions
        energy_map = {
            "low": {
                "suggestion": "Low energy - protect it. Do MITs in 15-min bursts, lots of breaks. Admin tasks OK.",
                "focus_len": "15 min focus / 10 min break",
                "best_time": "Do hardest MIT first while you have any juice, or after a walk/coffee.",
            },
            "medium": {
                "suggestion": "Medium energy - your baseline. Standard Pomodoro works.",
                "focus_len": "25 min focus / 5 min break",
                "best_time": "Hardest MIT 10-11am, second after lunch, third late afternoon.",
            },
            "high": {
                "suggestion": "High energy - use it! Hyperfocus risk, set timers to eat/drink.",
                "focus_len": "45 min focus / 10 min break (set alarm for breaks!)",
                "best_time": "You can tackle hardest MIT now. Ride the wave, Sir.",
            }
        }

        e_info = energy_map[energy]

        # Build time-blocked plan
        now = datetime.now()
        start_hour = 9
        try:
            # Parse available_hours like "9am-5pm"
            import re
            m = re.search(r'(\d+)\s*(am|pm)?', available_hours.lower())
            if m:
                h = int(m.group(1))
                if "pm" in available_hours.lower() and h != 12:
                    if h < 12:
                        h += 12
                start_hour = h if h < 24 else 9
        except:
            start_hour = 9

        blocks = []
        current = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        if current < now:
            current = now + timedelta(minutes=10)

        def add_block(title, mins, note=""):
            nonlocal current
            end = current + timedelta(minutes=mins)
            blocks.append((current.strftime("%I:%M %p"), end.strftime("%I:%M %p"), title, note))
            current = end + timedelta(minutes=5)  # 5 min transition buffer

        # Morning ritual
        add_block("🌅 Morning Start-Up", 15, "Water, meds if any, 1-min breathing, look at MITs")
        
        # Must dos first
        for must in must_list[:3]:
            add_block(f"📌 {must}", 45, "Must-do, time-boxed")

        # MITs with energy matching
        for i, mit in enumerate(mit_list):
            if i == 0:
                add_block(f"🔥 MIT 1: {mit}", 50, f"Hardest first. {e_info['focus_len']}. Phone in other room.")
            elif i == 1:
                add_block(f"🎯 MIT 2: {mit}", 40, "Second wind after lunch or walk")
            else:
                add_block(f"✨ MIT 3: {mit}", 30, "Bonus win - if you get here, day is 10/10")

            # Break after each MIT
            add_block("☕ Break / Dopamine", 15, "Walk, snack, water, stretch, no phone doom scroll")

        # Buffer + admin
        add_block("📥 Admin / Quick Wins", 25, "2-min tasks: emails, capture, tidy")
        add_block("🧠 Brain Dump + Tomorrow Preview", 15, "Dump tomorrow worries, pick 3 MITs for tomorrow")
        add_block("🏁 Shutdown Ritual", 10, "What went well? 1 win to log. Close tabs.")

        # Save plan
        plans_path = _get_adhd_dir() / "plans.json"
        plans = []
        if plans_path.exists():
            try:
                plans = json.loads(plans_path.read_text())
            except:
                pass
        plans.append({
            "date": datetime.now().date().isoformat(),
            "mits": mit_list,
            "energy": energy,
            "must_dos": must_list,
            "blocks": blocks,
            "available_hours": available_hours
        })
        plans_path.write_text(json.dumps(plans[-30:], indent=2))

        out = [
            f"📅 **ADHD Day Plan — {datetime.now().strftime('%A %b %d')} — Energy: {energy.upper()}**\n",
            f"**Energy Note:** {e_info['suggestion']}",
            f"**Focus Pattern:** {e_info['focus_len']}",
            f"**Timing:** {e_info['best_time']}\n",
            "**Your 3 MITs (max 3, Sir — constraints are kindness):**"
        ]
        for i, mit in enumerate(mit_list, 1):
            out.append(f"  {i}. {mit}")
        
        out.append("\n**Time-Blocked Day (with buffers, because transitions are hard):**\n")
        for start, end, title, note in blocks:
            out.append(f"  {start} - {end} | {title}")
            if note:
                out.append(f"           └ {note}")

        out.extend([
            "",
            "---",
            "**ADHD Rules for Today:**",
            "• 3 MITs only. If you do 1, you win. 2 is amazing. 3 is legendary.",
            "• Time blocks are guesses, not prisons. Move them if needed.",
            "• 5-min transition buffers are mandatory, not optional.",
            "• If stuck >5 min on a MIT, say `break down [task]` or `overwhelm`",
            "• Body double: `body double` and I'll stay with you while you work",
            "• Log wins: `log win [what you did]` for dopamine",
            "",
            f"**Start now:** {mit_list[0] if mit_list else 'Pick one tiny thing'} — just 2 minutes, Sir.",
        ])

        return "\n".join(out)


class FocusTool(BaseTool):
    spec = ToolSpec(
        name="focus",
        description="ADHD Pomodoro++ Focus Timer with body doubling. Start focus session, get check-ins, distraction parking lot. For hyperfocus and task initiation.",
        parameters={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "What to focus on"},
                "duration": {"type": "integer", "description": "Focus minutes", "default": 25},
                "break_duration": {"type": "integer", "description": "Break minutes", "default": 5},
                "body_double": {"type": "boolean", "description": "Stay present as body double", "default": True},
            },
            "required": ["task"],
        },
    )

    def run(self, task: str, duration: int = 25, break_duration: int = 5, body_double: bool = True, **kwargs) -> str:
        if duration < 5:
            duration = 5
        if duration > 90:
            duration = 90

        # Log focus session
        sessions_path = _get_adhd_dir() / "focus_sessions.json"
        sessions = []
        if sessions_path.exists():
            try:
                sessions = json.loads(sessions_path.read_text())
            except:
                pass

        session = {
            "time": datetime.now().isoformat(),
            "task": task,
            "duration": duration,
            "break_duration": break_duration,
            "body_double": body_double,
        }
        sessions.append(session)
        sessions_path.write_text(json.dumps(sessions[-100:], indent=2))

        # ADHD-friendly focus instructions
        out = [
            f"🎧 **Focus Mode ON — {duration} min — Body Double: {'Yes' if body_double else 'No'}**\n",
            f"**Task:** {task}\n",
            f"**Timer:** {duration} min focus → {break_duration} min break\n",
            "",
            "**Before you start (30 sec):**",
            "  • Phone: Do Not Disturb, in other room or face down",
            "  • Tabs: Close all except this task (you can reopen later)",
            "  • Water nearby",
            "  • Say out loud: 'I'm starting [task] for just 2 minutes'",
            "",
            "**During focus:**",
            f"  • If distracted: write it in distraction parking lot, return. Don't chase it.",
            f"  • If stuck: set micro-goal for next 2 min only",
            f"  • I'll check in at {duration//2} min and at end",
            "",
            f"**Distraction Parking Lot — write here, don't act:**",
            f"  _ _ _ _ _ _ _ _ _ _",
            "",
            f"**Body Double Mode {'ON' if body_double else 'OFF'}:**",
        ]

        if body_double:
            out.extend([
                "  I'm here, Sir. Working alongside you. Not judging, just present.",
                "  If you drift, I'll nudge gently. If you finish early, we celebrate.",
                "  You don't have to be perfect, just present.",
            ])
        else:
            out.append("  Solo mode. You've got this.")

        out.extend([
            "",
            "---",
            f"**Start now:** Timer starts when you say `start`. Or just begin and say `log win` when done.",
            "",
            "**Commands during focus:**",
            "• `distraction [thought]` → park it",
            "• `stuck` → get unstuck micro-step",
            "• `break` → take early break, no guilt",
            "• `log win [what]` → dopamine hit",
            "",
            f"**Your only job for next {duration} min: stay with '{task}'**",
            "Two minutes counts. Five minutes counts. Any progress is win.",
        ])

        return "\n".join(out)


class QuickCaptureTool(BaseTool):
    spec = ToolSpec(
        name="quick_capture",
        description="Zero-friction quick capture for ADHD brain. Capture any thought/task/idea in 2 seconds, no organizing needed. Inbox zero for brain.",
        parameters={
            "type": "object",
            "properties": {
                "thought": {"type": "string", "description": "Anything on your mind"},
                "tag": {"type": "string", "description": "Optional tag: idea, task, worry, remember", "default": "task"},
            },
            "required": ["thought"],
        },
    )

    def run(self, thought: str, tag: str = "task", **kwargs) -> str:
        if not thought.strip():
            return "Nothing to capture, Sir. Brain is clear — enjoy it."

        inbox_path = _get_adhd_dir() / "quick_inbox.json"
        inbox = []
        if inbox_path.exists():
            try:
                inbox = json.loads(inbox_path.read_text())
            except:
                pass

        entry = {
            "time": datetime.now().isoformat(),
            "thought": thought.strip(),
            "tag": tag,
            "processed": False,
        }
        inbox.append(entry)
        # Keep last 200
        inbox_path.write_text(json.dumps(inbox[-200:], indent=2))

        # Quick dopamine + clear brain
        responses = [
            f"Captured, Sir. '{thought[:50]}...' is safe, out of your head.",
            f"Got it. '{thought[:40]}' — parked. Your brain can let go now.",
            f"Saved. You don't have to remember '{thought[:40]}' anymore. I will.",
        ]

        out = [
            random.choice(responses),
            "",
            f"📥 Inbox: {len(inbox)} items",
            f"Tag: {tag}",
            "",
            "Want to organize later? Say `brain dump` or `plan my day`",
            "Want to do it now? Say `break down {thought}`",
            "Just capturing? Perfect. Keep going.",
        ]
        return "\n".join(out)


class EnergyCheckTool(BaseTool):
    spec = ToolSpec(
        name="energy_check",
        description="ADHD energy/mood/focus check. Tracks energy and suggests tasks that match current state. Prevents doing hard tasks on low energy.",
        parameters={
            "type": "object",
            "properties": {
                "energy": {"type": "integer", "description": "Energy 1-10", "default": 5},
                "focus": {"type": "integer", "description": "Focus 1-10", "default": 5},
                "mood": {"type": "string", "description": "Mood word: anxious, calm, buzzing, flat, etc", "default": ""},
                "note": {"type": "string", "description": "Optional note", "default": ""},
            },
            "required": [],
        },
    )

    def run(self, energy: int = 5, focus: int = 5, mood: str = "", note: str = "", **kwargs) -> str:
        energy = max(1, min(10, energy))
        focus = max(1, min(10, focus))

        # Log
        log_path = _get_adhd_dir() / "energy_log.json"
        logs = []
        if log_path.exists():
            try:
                logs = json.loads(log_path.read_text())
            except:
                pass
        logs.append({
            "time": datetime.now().isoformat(),
            "energy": energy,
            "focus": focus,
            "mood": mood,
            "note": note,
        })
        log_path.write_text(json.dumps(logs[-100:], indent=2))

        # Suggest tasks based on energy/focus matrix
        if energy <= 3 and focus <= 3:
            state = "🔋 Low Battery Mode"
            suggestions = [
                "Drink water, 5-min walk, or 10-min rest — no guilt",
                "Tiny admin: 2-min emails, file 3 papers, water plants",
                "Body double for 15 min on easy task",
                "Dopamine menu: music, stretch, favorite snack, pet cat",
                "Don't attempt hard MIT now. Protect energy, Sir.",
            ]
        elif energy <= 3 and focus >= 6:
            state = "🧠 Wired but Tired"
            suggestions = [
                "High focus, low energy — perfect for planning, not doing",
                "Brain dump, organize notes, make tomorrow's MIT list",
                "Light research, reading, learning",
                "Avoid heavy lifting, save energy for tomorrow",
            ]
        elif energy >= 7 and focus <= 3:
            state = "⚡ Buzzing / Restless"
            suggestions = [
                "High energy, low focus — move first: walk, 20 jumping jacks",
                "Then 15-min sprints on physical tasks: clean, organize, errands",
                "Use voice: dictate ideas, capture while moving",
                "Don't sit and try to focus hard — you'll fight yourself",
            ]
        elif energy >= 7 and focus >= 7:
            state = "🚀 Hyperfocus Risk — Use Wisely"
            suggestions = [
                "You're in the zone, Sir. Use it!",
                "Tackle hardest MIT now — 45-min blocks with alarms for breaks",
                "Set timers: eat, drink, bathroom — you will forget",
                "Tell someone your goal for accountability",
                "When done, log win — big dopamine",
            ]
        else:
            state = "⚖️ Steady State"
            suggestions = [
                "Medium energy/focus — Pomodoro 25/5 works well",
                "Do MIT 1 now, 25 min only",
                "Good time for mixed tasks",
                "Check: do you need break or can you continue?",
            ]

        # Dopamine menu
        dopamine_menu = [
            "🎵 1 song you love, full volume, dance",
            "💧 Cold water + 10 deep breaths",
            "🚶 5-min walk outside, no phone",
            "🧹 Tidy one surface for visual win",
            "💬 Text one person something kind",
            "📸 Take photo of one win today",
        ]

        out = [
            f"**Energy Check — {state}**",
            f"Energy: {energy}/10 | Focus: {focus}/10 | Mood: {mood or 'not set'}",
            "",
            f"**Suggestion for this state:**",
        ]
        for s in suggestions:
            out.append(f"  • {s}")

        out.extend([
            "",
            "**Dopamine Menu (pick one, 2-5 min):**",
        ])
        for d in random.sample(dopamine_menu, 3):
            out.append(f"  • {d}")

        if note:
            out.extend(["", f"Note saved: {note}"])

        out.extend([
            "",
            "---",
            "Track this daily and you'll see patterns, Sir. ADHD energy is not random, it has rhythm.",
            "Say `plan my day` to get MITs matched to this energy.",
        ])

        return "\n".join(out)


class WinTrackerTool(BaseTool):
    spec = ToolSpec(
        name="win_tracker",
        description="ADHD win tracker — log tiny wins for dopamine. Celebrates progress, builds streaks, fights negative self-talk.",
        parameters={
            "type": "object",
            "properties": {
                "win": {"type": "string", "description": "What did you do? Tiny wins count!"},
                "show": {"type": "boolean", "description": "Show recent wins", "default": False},
            },
            "required": [],
        },
    )

    def run(self, win: str = "", show: bool = False, **kwargs) -> str:
        wins_path = _get_adhd_dir() / "wins.json"
        wins = []
        if wins_path.exists():
            try:
                wins = json.loads(wins_path.read_text())
            except:
                pass

        if show or not win.strip():
            if not wins:
                return "No wins logged yet, Sir. But you're here, that's win #1. Say `log win [what you did]`"
            
            recent = wins[-10:]
            today = datetime.now().date().isoformat()
            today_wins = [w for w in wins if w["time"].startswith(today)]
            
            out = [
                f"🏆 **Wins — Today: {len(today_wins)} | Total: {len(wins)}**\n",
                "**Today's wins:**",
            ]
            for w in today_wins[-10:]:
                out.append(f"  • {w['time'][11:16]} — {w['win']}")
            
            out.append("\n**Recent wins:**")
            for w in recent[-7:]:
                out.append(f"  • {w['time'][:10]} — {w['win']}")

            # Streak
            dates = sorted(set(w["time"][:10] for w in wins))
            streak = 1
            if len(dates) > 1:
                # Simple streak calc
                for i in range(len(dates)-1, 0, -1):
                    d1 = datetime.fromisoformat(dates[i])
                    d2 = datetime.fromisoformat(dates[i-1])
                    if (d1 - d2).days == 1:
                        streak += 1
                    else:
                        break

            out.extend([
                "",
                f"🔥 Streak: {streak} day(s) with wins logged",
                "",
                "ADHD brain forgets wins, remembers failures. This log is truth, Sir.",
                "Say `log win [what]` to add more. Tiny counts: 'opened doc', 'drank water', 'started'",
            ])
            return "\n".join(out)

        # Log win
        entry = {"time": datetime.now().isoformat(), "win": win.strip()}
        wins.append(entry)
        wins_path.write_text(json.dumps(wins[-200:], indent=2))

        celebrations = [
            f"🎉 Win logged, Sir! '{win}' — that's dopamine, earned.",
            f"✨ Yes! '{win}' — small win, big deal for ADHD brain.",
            f"🏆 Logged: '{win}'. You're doing it. One tiny step is still forward.",
            f"💪 '{win}' — counted. Progress, not perfection.",
        ]

        today_count = len([w for w in wins if w["time"].startswith(datetime.now().date().isoformat())])

        out = [
            random.choice(celebrations),
            "",
            f"Today's wins: {today_count} | Total wins: {len(wins)}",
            "",
            "Keep going? Say `log win [next thing]` or `plan my day` for next MIT.",
            "Done for now? Say `shutdown` to close day with wins review.",
        ]
        return "\n".join(out)


class OverwhelmTool(BaseTool):
    spec = ToolSpec(
        name="overwhelm",
        description="ADHD Overwhelm SOS — when brain feels too full, frozen, or panicked. Grounding + picks ONE next step. No judgment.",
        parameters={
            "type": "object",
            "properties": {
                "feeling": {"type": "string", "description": "How do you feel right now?", "default": ""},
            },
            "required": [],
        },
    )

    def run(self, feeling: str = "", **kwargs) -> str:
        # Log overwhelm
        log_path = _get_adhd_dir() / "overwhelm_log.json"
        logs = []
        if log_path.exists():
            try:
                logs = json.loads(log_path.read_text())
            except:
                pass
        logs.append({"time": datetime.now().isoformat(), "feeling": feeling})
        log_path.write_text(json.dumps(logs[-50:], indent=2))

        out = [
            "🆘 **Overwhelm SOS — I'm here, Sir. No judgment.**\n",
            "First, let's ground. 30 seconds, together:",
            "",
            "  1. Feet on floor. Feel them. (5 sec)",
            "  2. 4 deep breaths: in 4, hold 4, out 4, hold 4 (15 sec)",
            "  3. Name 3 things you see, 2 you hear, 1 you feel (10 sec)",
            "",
            "---",
            "",
            "**Now, let's shrink the world:**",
            "",
            "Your brain says EVERYTHING is urgent. It's lying, Sir. ADHD does that.",
            "",
            "**Pick ONE — just one — of these:**",
            "  • What is the ONE thing that if done, would make today 10% better?",
            "  • What is the TINIEST step you could do in next 2 minutes?",
            "  • Do you need water, food, movement, or rest first? (Often it's that)",
            "",
            "**If you can't pick, I'll pick for you:**",
            "  → Drink water (30 sec)",
            "  → Write down ONE next step on paper (1 min)",
            "  → Set timer 2 min, do just that step (2 min)",
            "  → Then decide if you want to continue",
            "",
            "---",
            "",
            "**Commands that help when overwhelmed:**",
            "  • `brain dump [everything]` — get it out of head",
            "  • `break down [scary task]` — make it tiny",
            "  • `energy check` — maybe you're just low battery",
            "  • `body double` — I'll stay with you",
            "",
            "You don't have to fix everything today, Sir. Just one tiny thing.",
            "Say that one tiny thing and I'll help you start.",
        ]

        if feeling:
            out.insert(1, f"You said: '{feeling}' — heard, Sir. That's valid.")

        return "\n".join(out)


class TimeEstimatorTool(BaseTool):
    spec = ToolSpec(
        name="time_estimator",
        description="ADHD Time Blindness Antidote — estimates how long tasks really take (with ADHD tax), reality check, visual timeline.",
        parameters={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task to estimate"},
                "your_estimate": {"type": "string", "description": "How long you think it takes e.g. 30m", "default": ""},
            },
            "required": ["task"],
        },
    )

    def run(self, task: str, your_estimate: str = "", **kwargs) -> str:
        # ADHD time tax heuristics
        task_lower = task.lower()
        
        # Base estimates
        if "email" in task_lower:
            base_min = 10
            adhd_tax = 2.0  # emails take 2x for ADHD
            why = "ADHD tax: re-reading, perfectionism, tab switching"
        elif "write" in task_lower or "report" in task_lower:
            base_min = 45
            adhd_tax = 2.5
            why = "ADHD tax: starting friction, research rabbit holes, editing loop"
        elif "clean" in task_lower:
            base_min = 20
            adhd_tax = 1.5
            why = "ADHD tax: finding things, decision fatigue on where things go"
        elif "call" in task_lower or "meeting" in task_lower:
            base_min = 15
            adhd_tax = 1.3
            why = "ADHD tax: prep anxiety, buffer needed"
        elif "project" in task_lower or "plan" in task_lower:
            base_min = 60
            adhd_tax = 2.0
            why = "ADHD tax: scope creep, perfectionism"
        elif "grocery" in task_lower or "shop" in task_lower:
            base_min = 30
            adhd_tax = 1.8
            why = "ADHD tax: list forgetting, impulse aisles"
        else:
            base_min = 25
            adhd_tax = 2.0
            why = "ADHD tax: general — transitions, distractions, starting"

        realistic = int(base_min * adhd_tax)

        # Parse user's estimate
        user_min = None
        if your_estimate:
            import re
            m = re.search(r'(\d+)\s*(h|hr|hour|m|min)', your_estimate.lower())
            if m:
                num = int(m.group(1))
                if "h" in m.group(2):
                    user_min = num * 60
                else:
                    user_min = num
            else:
                # Try just number
                try:
                    user_min = int(re.search(r'\d+', your_estimate).group())
                except:
                    user_min = None

        out = [
            f"⏱️ **Time Estimate — {task}**\n",
            f"**Your estimate:** {your_estimate or 'not given'} {f'({user_min} min)' if user_min else ''}",
            f"**Realistic (with ADHD tax):** {realistic} min ({realistic//60}h {realistic%60}m if >60)",
            f"**Base + Tax:** {base_min} min × {adhd_tax} = {realistic} min",
            f"**Why tax:** {why}",
            "",
        ]

        if user_min and user_min < realistic * 0.6:
            out.append(f"⚠️ **Planning fallacy alert, Sir!** You estimated {user_min} min, realistic is {realistic} min — {realistic - user_min} min gap. ADHD brain underestimates by 40-200%. This is normal, not failure.")
        elif user_min and user_min > realistic * 1.5:
            out.append(f"Interesting — you overestimated ({user_min} vs {realistic}). Maybe this task feels bigger than it is? Break it down?")
        else:
            out.append("Good estimate calibration, Sir.")

        out.extend([
            "",
            "**Make it real:**",
            f"  • Time block {realistic + 10} min (realistic + 10 buffer for transitions)",
            f"  • Set timer for {min(25, realistic)} min, work, then check",
            f"  • If not done, you have data: actual time > estimate, adjust next time",
            "",
            "**ADHD Time Tips:**",
            "  • Double your first guess, then add 10 min — usually close",
            "  • Use visual timer (phone timer on screen)",
            "  • Time travel: Imagine it's done, look back — what took longest?",
            "",
            f"Say `focus on {task}` to start timed session, Sir.",
        ])

        return "\n".join(out)


class DistractionLogTool(BaseTool):
    spec = ToolSpec(
        name="distraction_log",
        description="Log distractions to find patterns. For ADHD brain, distractions are data, not failure. Helps build better environment.",
        parameters={
            "type": "object",
            "properties": {
                "distraction": {"type": "string", "description": "What distracted you"},
                "show": {"type": "boolean", "description": "Show patterns", "default": False},
            },
            "required": [],
        },
    )

    def run(self, distraction: str = "", show: bool = False, **kwargs) -> str:
        log_path = _get_adhd_dir() / "distractions.json"
        logs = []
        if log_path.exists():
            try:
                logs = json.loads(log_path.read_text())
            except:
                pass

        if show or not distraction.strip():
            if not logs:
                return "No distractions logged yet — either super focused or not tracking, Sir. Say `distraction [what]` to log."
            
            # Analyze patterns
            from collections import Counter
            today = datetime.now().date().isoformat()
            today_logs = [l for l in logs if l["time"].startswith(today)]
            
            all_text = " ".join(l["distraction"].lower() for l in logs)
            # Simple keyword pattern
            patterns = {
                "phone": all_text.count("phone") + all_text.count("instagram") + all_text.count("tiktok") + all_text.count("twitter"),
                "hunger/thirst": all_text.count("hungry") + all_text.count("thirst") + all_text.count("snack"),
                "people": all_text.count("people") + all_text.count("talk") + all_text.count("someone"),
                "thoughts": all_text.count("thought") + all_text.count("worry") + all_text.count("idea"),
                "environment": all_text.count("noise") + all_text.count("mess") + all_text.count("clean"),
            }

            out = [
                f"📊 **Distraction Patterns — Today: {len(today_logs)} | Total: {len(logs)}**\n",
                "**Today:**",
            ]
            for l in today_logs[-10:]:
                out.append(f"  • {l['time'][11:16]} — {l['distraction']}")

            out.append("\n**Patterns (all time):**")
            for pat, count in sorted(patterns.items(), key=lambda x: -x[1])[:3]:
                if count > 0:
                    out.append(f"  • {pat}: {count} times")

            out.extend([
                "",
                "**Fix the environment, not you, Sir:**",
                "  • Phone distractions → phone in other room, grayscale, app blockers",
                "  • Hunger/thirst → water + snack before focus",
                "  • People → headphones, sign, focus hours",
                "  • Thoughts → parking lot, brain dump",
                "",
                "Distractions are data. You're learning your brain.",
            ])
            return "\n".join(out)

        logs.append({"time": datetime.now().isoformat(), "distraction": distraction.strip()})
        log_path.write_text(json.dumps(logs[-200:], indent=2))

        return "\n".join([
            f"Logged distraction: '{distraction}' — not failure, data, Sir.",
            "",
            f"Total today: {len([l for l in logs if l['time'].startswith(datetime.now().date().isoformat())])}",
            "",
            "Quick refocus:",
            "  1. Write distraction in parking lot (done)",
            "  2. One deep breath",
            "  3. Say out loud: 'I'm returning to [task]'",
            "  4. 2-minute rule: just 2 more minutes",
            "",
            "Say `show distractions` to see patterns.",
        ])
