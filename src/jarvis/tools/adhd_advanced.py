"""Advanced ADHD tools — habit stacking, transitions, if-then, weekly review, dopamine menu builder.

These build on the core 10 ADHD tools for deeper executive function support.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from jarvis.tools.base import BaseTool, ToolSpec
from jarvis.core.config import get_home


def _get_adhd_dir() -> Path:
    d = get_home() / "adhd"
    d.mkdir(parents=True, exist_ok=True)
    return d


class HabitStackTool(BaseTool):
    spec = ToolSpec(
        name="habit_stack",
        description="ADHD Habit Stacking — link new habit to existing habit. Tiny habits, anchored to something you already do. James Clear + ADHD adaptation.",
        parameters={
            "type": "object",
            "properties": {
                "existing_habit": {"type": "string", "description": "Existing habit you already do (e.g. make coffee, brush teeth)"},
                "new_habit": {"type": "string", "description": "Tiny new habit to stack (2-min max)"},
                "time": {"type": "string", "description": "When: morning, afternoon, evening", "default": "morning"},
            },
            "required": ["existing_habit", "new_habit"],
        },
    )

    def run(self, existing_habit: str, new_habit: str, time: str = "morning", **kwargs) -> str:
        if not existing_habit or not new_habit:
            return "Need both existing habit and new tiny habit, Sir."

        # Save stack
        path = _get_adhd_dir() / "habit_stacks.json"
        stacks = []
        if path.exists():
            try:
                stacks = json.loads(path.read_text())
            except:
                pass

        stack = {
            "time": datetime.now().isoformat(),
            "existing": existing_habit,
            "new": new_habit,
            "when": time,
            "formula": f"After I {existing_habit}, I will {new_habit}",
        }
        stacks.append(stack)
        path.write_text(json.dumps(stacks[-50:], indent=2))

        out = [
            f"🔗 **Habit Stack Created, Sir**\n",
            f"**Formula:** After I {existing_habit}, I will {new_habit}",
            f"**When:** {time}",
            "",
            "**Why this works for ADHD:**",
            "  • Existing habit is anchor — no need to remember when",
            "  • Tiny habit = 2-min max, no willpower needed",
            "  • Stack, don't start from scratch",
            "",
            "**ADHD Habit Rules:**",
            "  • Make it tiny: 'open doc' not 'write report'",
            "  • Make it obvious: put cue where you see existing habit",
            "  • Make it easy: 2-min max, lower bar than you think",
            "  • Celebrate immediately: say 'win' after, dopamine",
            "",
            "**Examples that work:**",
            "  • After I make coffee, I will open Q4 doc (30 sec)",
            "  • After I brush teeth, I will brain dump 3 MITs (2 min)",
            "  • After I close laptop, I will log 1 win (30 sec)",
            "  • After I sit at desk, I will set timer 25m + water (1 min)",
            "",
            f"**Your stack:** {stack['formula']}",
            "Try it tomorrow, Sir. One stack at a time. Track wins.",
        ]
        return "\n".join(out)


class TransitionTool(BaseTool):
    spec = ToolSpec(
        name="transition",
        description="ADHD Transition Helper — transitions are hard for ADHD brain. Gives 5-min warning, shutdown ritual, startup ritual, buffer.",
        parameters={
            "type": "object",
            "properties": {
                "from_task": {"type": "string", "description": "Leaving this task"},
                "to_task": {"type": "string", "description": "Going to this task"},
                "minutes": {"type": "integer", "description": "Minutes for transition", "default": 5},
            },
            "required": ["from_task", "to_task"],
        },
    )

    def run(self, from_task: str, to_task: str, minutes: int = 5, **kwargs) -> str:
        if not from_task or not to_task:
            return "Need from and to tasks, Sir. Transitions need both ends."

        out = [
            f"🔄 **Transition — {from_task} → {to_task} — {minutes} min buffer**\n",
            "**Why transitions hard for ADHD:**",
            "  • Hyperfocus makes switching painful",
            "  • Working memory loses context",
            "  • Time blindness — 5 min feels like 0 or 60",
            "  • Need closure + clear next step",
            "",
            f"**Shutdown Ritual for '{from_task}' ({minutes//2} min):**",
            "  1. Save + close tabs (1 min)",
            "  2. Write 1-sentence note: where left off + next step (1 min)",
            "  3. Log win: what you did (30 sec)",
            "  4. Physical move: stand, stretch, water (30 sec)",
            "",
            f"**Transition Buffer ({minutes} min):**",
            "  • Don't jump directly — buffer is mandatory",
            "  • Walk, bathroom, water, 3 deep breaths",
            "  • Brain dump any lingering thoughts from previous task",
            "",
            f"**Startup Ritual for '{to_task}' ({minutes//2} min):**",
            "  1. Open only app needed for new task (30 sec)",
            "  2. Say out loud: 'I'm starting [task] for just 2 min' (10 sec)",
            "  3. Set timer 25m, visual timer on screen (20 sec)",
            "  4. First micro-step: define DONE in 10 words (1 min)",
            "",
            f"**Ready? Timer {minutes} min, then start '{to_task}' for just 2 min, Sir.**",
            "",
            "Tip: Transitions are not wasted time. They ARE the work for ADHD brain.",
        ]
        return "\n".join(out)


class IfThenTool(BaseTool):
    spec = ToolSpec(
        name="if_then",
        description="ADHD If-Then Planning — implementation intentions. 'If X happens, then I will do Y'. Pre-decides for when executive function fails.",
        parameters={
            "type": "object",
            "properties": {
                "if_situation": {"type": "string", "description": "If this situation happens"},
                "then_action": {"type": "string", "description": "Then I will do this tiny action"},
            },
            "required": ["if_situation", "then_action"],
        },
    )

    def run(self, if_situation: str, then_action: str, **kwargs) -> str:
        if not if_situation or not then_action:
            return "Need If and Then, Sir. If [situation], then [tiny action]."

        path = _get_adhd_dir() / "if_then.json"
        plans = []
        if path.exists():
            try:
                plans = json.loads(path.read_text())
            except:
                pass

        plan = {
            "time": datetime.now().isoformat(),
            "if": if_situation,
            "then": then_action,
            "formula": f"If {if_situation}, then I will {then_action}",
        }
        plans.append(plan)
        path.write_text(json.dumps(plans[-50:], indent=2))

        examples = [
            "If I feel overwhelmed, then I will do 4 breaths + write ONE next step",
            "If I get distracted by phone, then I will put phone in other room + return",
            "If I can't start task, then I will break it down into 2-min steps",
            "If it's 10am, then I will energy check + pick MIT 1",
            "If I finish MIT, then I will log win + 5-min break",
            "If I feel low energy, then I will water + walk + tiny admin",
        ]

        out = [
            f"🧩 **If-Then Plan Created — Implementation Intention**\n",
            f"**Formula:** If {if_situation}, then I will {then_action}",
            "",
            "**Why this works for ADHD:**",
            "  • Pre-decides when executive function is offline",
            "  • No in-the-moment decision — just follow plan",
            "  • If is trigger, Then is tiny action (2-min max)",
            "  • Research: 2-3x more likely to follow through",
            "",
            "**Your If-Then plans (you have {}):**".format(len(plans)),
        ]
        for p in plans[-5:]:
            out.append(f"  • {p['formula']}")

        out.extend([
            "",
            "**Examples that work for ADHD:**",
        ])
        for ex in random.sample(examples, 3):
            out.append(f"  • {ex}")

        out.extend([
            "",
            f"**Your new plan:** If {if_situation}, then {then_action}",
            "Write it on sticky note where you'll see trigger, Sir.",
            "When trigger happens, no thinking — just do Then.",
        ])

        return "\n".join(out)


class WeeklyReviewTool(BaseTool):
    spec = ToolSpec(
        name="weekly_review",
        description="ADHD Weekly Review — patterns, wins, what worked, what didn't. No shame, only data. Builds self-awareness.",
        parameters={
            "type": "object",
            "properties": {
                "show": {"type": "boolean", "description": "Show review", "default": True},
            },
            "required": [],
        },
    )

    def run(self, show: bool = True, **kwargs) -> str:
        adhd_dir = _get_adhd_dir()
        
        # Gather data from all logs
        def load_json(name, default=None):
            p = adhd_dir / name
            if p.exists():
                try:
                    return json.loads(p.read_text())
                except:
                    return default or []
            return default or []

        wins = load_json("wins.json", [])
        energy_logs = load_json("energy_log.json", [])
        focus_sessions = load_json("focus_sessions.json", [])
        distractions = load_json("distractions.json", [])
        plans = load_json("plans.json", [])
        overwhelm_logs = load_json("overwhelm_log.json", [])

        # Calculate stats
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        week_wins = [w for w in wins if datetime.fromisoformat(w["time"]) > week_ago]
        week_focus = [f for f in focus_sessions if datetime.fromisoformat(f["time"]) > week_ago]
        week_energy = [e for e in energy_logs if datetime.fromisoformat(e["time"]) > week_ago]
        week_overwhelm = [o for o in overwhelm_logs if datetime.fromisoformat(o["time"]) > week_ago]

        total_focus_min = sum(f.get("duration", 25) for f in week_focus)
        avg_energy = sum(e.get("energy", 5) for e in week_energy) / len(week_energy) if week_energy else 5
        avg_focus = sum(e.get("focus", 5) for e in week_energy) / len(week_energy) if week_energy else 5

        # Distraction patterns
        from collections import Counter
        distraction_text = " ".join(d.get("distraction", "").lower() for d in distractions[-30:])
        top_distractions = []
        for keyword in ["phone", "instagram", "tiktok", "email", "hungry", "tired", "noise", "people"]:
            if keyword in distraction_text:
                top_distractions.append(keyword)

        out = [
            f"📅 **Weekly Review — {week_ago.strftime('%b %d')} to {now.strftime('%b %d')}**\n",
            "**No shame, only data, Sir. Let's see patterns.**\n",
            f"**Wins:** {len(week_wins)} this week, {len(wins)} total",
            f"**Focus:** {len(week_focus)} sessions, {total_focus_min} min total ({total_focus_min//60}h {total_focus_min%60}m)",
            f"**Energy:** Avg {avg_energy:.1f}/10 energy, {avg_focus:.1f}/10 focus ({len(week_energy)} check-ins)",
            f"**Overwhelm:** {len(week_overwhelm)} times (normal, not failure)",
            f"**Plans:** {len([p for p in plans if datetime.fromisoformat(p.get('date', '2000-01-01') + 'T00:00:00') > week_ago])} day plans made",
            "",
            "**This Week's Wins (dopamine log):**",
        ]

        for w in week_wins[-10:]:
            out.append(f"  • {w['time'][:10]} {w['time'][11:16]} — {w['win']}")

        if not week_wins:
            out.append("  • No wins logged — log even tiny: 'opened doc' counts, Sir")

        out.extend([
            "",
            "**Patterns I see:**",
        ])

        if avg_energy < 4:
            out.append("  • Low energy week — protect battery, more breaks, tiny admin OK")
        elif avg_energy > 7:
            out.append("  • High energy week — you rode wave well, Sir")

        if len(week_overwhelm) > 3:
            out.append(f"  • Overwhelm {len(week_overwhelm)}x — brain full? More brain dumps, fewer MITs?")

        if top_distractions:
            out.append(f"  • Top distractions: {', '.join(top_distractions[:3])} — fix environment, not you")

        if len(week_focus) == 0:
            out.append("  • No focus sessions — try 15m sprint tomorrow, just 15m")
        elif total_focus_min > 300:
            out.append(f"  • {total_focus_min} min focus — strong week, Sir!")

        out.extend([
            "",
            "**What Worked? (guess, then test next week)**",
            "  • Which MIT time worked best? Morning? After walk?",
            "  • Which focus length? 15, 25, 45?",
            "  • What dopamine menu item helped most?",
            "",
            "**What to Try Next Week? Pick ONE:**",
            "  • One habit stack: After I [existing], I will [tiny new]",
            "  • One if-then: If [trigger], then [tiny action]",
            "  • Energy tracking at same time daily to see rhythm",
            "  • 3 MITs max, no more — constraints are kindness",
            "",
            "**Next Week's Experiment (one thing):**",
            "Say: `habit stack existing: make coffee new: open MIT doc` or `if then if: overwhelmed then: 4 breaths + ONE step`",
            "",
            "Weekly review is not about perfection, Sir. It's about data. You're learning your brain.",
        ])

        return "\n".join(out)


class DopamineMenuTool(BaseTool):
    spec = ToolSpec(
        name="dopamine_menu",
        description="Build personalized dopamine menu — healthy dopamine hits for ADHD brain. Appetizers, entrees, sides, desserts. No doom scroll.",
        parameters={
            "type": "object",
            "properties": {
                "build": {"type": "boolean", "description": "Build menu", "default": False},
                "show": {"type": "boolean", "description": "Show menu", "default": True},
            },
            "required": [],
        },
    )

    def run(self, build: bool = False, show: bool = True, **kwargs) -> str:
        path = _get_adhd_dir() / "dopamine_menu.json"
        menu = None
        if path.exists():
            try:
                menu = json.loads(path.read_text())
            except:
                menu = None

        if not menu or build:
            # Default ADHD-friendly dopamine menu
            menu = {
                "appetizers": [
                    "💧 Cold water + 10 deep breaths (1 min)",
                    "🎵 1 favorite song, full volume, dance (3 min)",
                    "🚶 5-min walk outside, no phone (5 min)",
                    "🧊 Splash cold water on face (30 sec)",
                    "🫁 4-7-8 breathing: in 4, hold 7, out 8 (1 min)",
                ],
                "entrees": [
                    "🧹 Tidy one surface — visual win (5 min)",
                    "📝 Brain dump 5 things on mind (3 min)",
                    "💬 Text one person something kind (2 min)",
                    "🌱 Water plants / pet cat / stretch (3 min)",
                    "📸 Take photo of one win today (1 min)",
                ],
                "sides": [
                    "🎨 Doodle / sketch for 5 min",
                    "📚 Read 2 pages of fun book",
                    "🎸 Play instrument / hum 1 song",
                    "🧩 5-min puzzle / Lego",
                    "🍵 Make favorite tea/coffee mindfully",
                ],
                "desserts": [
                    "🎮 10-min game (timer! No rabbit hole)",
                    "📺 1 YouTube video you love (not autoplay)",
                    "🍫 Favorite snack, eat slowly, no phone",
                    "🛁 10-min bath / shower with music",
                    "💤 10-min rest, no guilt, eyes closed",
                ],
                "specials_avoid": [
                    "❌ Doom scroll (feels good 2 min, bad 2 hours)",
                    "❌ 2-hour research rabbit hole",
                    "❌ 5 tabs open 'quick check'",
                    "❌ 'Just one more episode'",
                ]
            }
            path.write_text(json.dumps(menu, indent=2))

        out = [
            "🍽️ **Dopamine Menu — Healthy Hits for ADHD Brain**\n",
            "ADHD brain seeks dopamine. Give it good menu, not doom scroll, Sir.\n",
            "**Appetizers (1-3 min, quick hit):**",
        ]
        for item in menu["appetizers"]:
            out.append(f"  • {item}")

        out.append("\n**Entrees (3-5 min, satisfying):**")
        for item in menu["entrees"]:
            out.append(f"  • {item}")

        out.append("\n**Sides (5 min, fun):**")
        for item in menu["sides"]:
            out.append(f"  • {item}")

        out.append("\n**Desserts (10 min, treat, set timer!):**")
        for item in menu["desserts"]:
            out.append(f"  • {item}")

        out.append("\n**Avoid (fake dopamine, crash later):**")
        for item in menu["specials_avoid"]:
            out.append(f"  • {item}")

        out.extend([
            "",
            "**How to use:**",
            "  • Low energy? Appetizer",
            "  • Need win? Entree (tidy one surface = visual dopamine)",
            "  • Between tasks? Side",
            "  • Done with MIT? Dessert with timer",
            "",
            "**Build your own:** Say `dopamine menu` and tell me what gives YOU healthy dopamine, Sir. I'll add to menu.",
            "",
            "Menu saved to ~/.jarvis/adhd/dopamine_menu.json — edit anytime.",
        ])

        return "\n".join(out)


class ShutdownRitualTool(BaseTool):
    spec = ToolSpec(
        name="shutdown_ritual",
        description="ADHD Shutdown Ritual — end of day, close loops, log wins, preview tomorrow, permission to stop.",
        parameters={
            "type": "object",
            "properties": {
                "wins": {"type": "string", "description": "Today's wins (comma separated)", "default": ""},
                "tomorrow_mits": {"type": "string", "description": "Tomorrow's 3 MITs", "default": ""},
            },
            "required": [],
        },
    )

    def run(self, wins: str = "", tomorrow_mits: str = "", **kwargs) -> str:
        # Log wins if provided
        if wins:
            wins_path = _get_adhd_dir() / "wins.json"
            all_wins = []
            if wins_path.exists():
                try:
                    all_wins = json.loads(wins_path.read_text())
                except:
                    pass
            for w in [x.strip() for x in wins.replace(",", "\n").split("\n") if x.strip()]:
                all_wins.append({"time": datetime.now().isoformat(), "win": w})
            wins_path.write_text(json.dumps(all_wins[-200:], indent=2))

        # Save tomorrow MITs
        if tomorrow_mits:
            plans_path = _get_adhd_dir() / "plans.json"
            plans = []
            if plans_path.exists():
                try:
                    plans = json.loads(plans_path.read_text())
                except:
                    pass
            plans.append({
                "date": (datetime.now() + timedelta(days=1)).date().isoformat(),
                "mits": [m.strip() for m in tomorrow_mits.replace(",", "\n").split("\n") if m.strip()][:3],
                "created_at": datetime.now().isoformat(),
            })
            plans_path.write_text(json.dumps(plans[-30:], indent=2))

        out = [
            "🌙 **Shutdown Ritual — End of Day, Sir**\n",
            "ADHD brain needs closure, or it loops all night. Let's close loops.\n",
            "**Step 1: Wins (what did you do today? Tiny counts)**",
        ]

        if wins:
            out.append(f"  Logged: {wins}")
        else:
            out.append("  Say your wins: `shutdown wins: opened doc, replied email, 5-min tidy`")

        out.extend([
            "",
            "**Step 2: Brain Dump — Park Tomorrow Worries (2 min)**",
            "  Write everything on mind for tomorrow, messy is fine",
            "  Your brain can let go, I will hold it",
            "",
            "**Step 3: Tomorrow's 3 MITs (max 3, Sir)**",
        ])

        if tomorrow_mits:
            out.append(f"  Tomorrow: {tomorrow_mits}")
        else:
            out.append("  What 3 would make tomorrow feel like win? Even tiny:")

        out.extend([
            "    • 'Open Q4 doc' counts",
            "    • 'Reply to 1 email' counts",
            "    • '5-min tidy' counts",
            "",
            "**Step 4: Close Tabs, Physically**",
            "  • Close all tabs, save docs",
            "  • Write 1-sentence note: where left off + next step for MIT 1",
            "  • Clear desk one surface (visual closure)",
            "",
            "**Step 5: Permission to Stop**",
            "  You did enough today, Sir. Even if list not done, you did something.",
            "  Any progress counts. Rest is productive for ADHD brain.",
            "  Tomorrow is new day with fresh dopamine.",
            "",
            "---",
            "Shutdown complete, Sir. Log off, guilt-free.",
            "Say `shutdown wins: [wins] tomorrow: [3 MITs]` to do ritual fully.",
        ])

        return "\n".join(out)
