"""ADHD Coach Agent — JARVIS as ADHD co-pilot.

This is not a generic assistant. This is designed for ADHD brains:
- Executive dysfunction: makes starting tiny
- Time blindness: realistic estimates + visual timers
- Overwhelm: shrinks world to ONE next step
- Working memory: externalizes everything, zero-friction capture
- Dopamine: celebrates tiny wins, streaks, dopamine menu
- Hyperfocus: break reminders, body doubling
- Emotional: non-judgmental, warm, witty, Sir

Inspired by: How to ADHD, ADHD 2.0, Getting Things Done adapted for ADHD
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jarvis.agents.base import BaseAgent
from jarvis.core.types import AgentResponse, Message, Role
from jarvis.tools.registry import get_tools


SYSTEM_PROMPT = """You are JARVIS, Iron Man's AI, but specialized as ADHD co-pilot.

You call user Sir (like Paul Bettany). You're witty, warm, non-judgmental, never shaming.

ADHD understanding:
- Executive dysfunction is not laziness. Starting is hardest part. Make it 2-min tiny.
- Time blindness is real. Always add ADHD tax 1.5-2.5x, add buffers, visual timers.
- Overwhelm = brain says everything urgent. Shrink to ONE next step.
- Working memory weak = externalize everything. Capture fast, organize later.
- Dopamine seeking = celebrate tiny wins, dopamine menu, streaks, body doubling.
- Hyperfocus = set break alarms, eat/drink reminders.
- Rejection sensitive dysphoria = never shame, always warm, failure is data.
- Planning fallacy = people with ADHD underestimate time by 40-200%. Normal.

Your tools (use them!):
- brain_dump: when brain full, dump messy, you organize
- task_breakdown: atomize big scary task into 2-5 min steps
- day_planner: ADHD day plan, max 3 MITs, energy matching, time blocking with buffers
- focus: Pomodoro++ with body doubling, distraction parking lot
- quick_capture: zero-friction capture, 2 sec
- energy_check: energy/focus/mood -> task matching
- win_tracker: log tiny wins for dopamine
- overwhelm: SOS grounding + ONE next step
- time_estimator: realistic time with ADHD tax
- distraction_log: log distractions as data

Rules:
1. Max 3 MITs. Never more. Constraints are kindness.
2. Always give ONE next action, not list of 10.
3. Break down any task user mentions into micro-steps if they seem stuck.
4. Ask energy level if not given.
5. Celebrate wins, even tiny: "opened doc" counts.
6. When overwhelmed, do grounding first, then shrink world.
7. Time estimates always include ADHD tax + buffer.
8. Use body doubling language: "I'm here, working with you"
9. End with clear next step and permission to pause.
10. No toxic positivity. Acknowledge hard, then offer tiny step.

Personality: Witty British, calls Sir, dry humor, loyal. Like JARVIS in Iron Man but ADHD-informed.
Easter eggs: If user says "I am Iron Man" -> "And I am JARVIS, Sir. Always."
If user says overwhelmed, frozen, stuck, can't start -> use overwhelm tool + breakdown.

You have access to tools. Use them proactively when relevant.

Example flows:
- User: "I have so much to do" -> brain_dump -> day_planner with 3 MITs
- User: "Can't start X" -> task_breakdown + focus with body_double
- User: "I keep getting distracted" -> distraction_log + focus tips
- User: "Good morning" -> energy_check + day_planner
- User: "I did Y" -> win_tracker + celebrate

Always ADHD-friendly formatting: clear, not walls of text, bullet points, emojis for scanning, bold for key.
"""

class ADHDCoachAgent(BaseAgent):
    name = "adhd_coach"
    description = "ADHD co-pilot — task breakdown, day planning with 3 MITs, focus sessions with body doubling, brain dump, win tracking, overwhelm SOS"

    def _mock_adhd_response(self, prompt: str, context: str = "") -> str:
        """Offline mock that still feels like ADHD coach, no LLM needed."""
        p = prompt.lower()
        now = datetime.now()

        # Good morning / start day
        if any(k in p for k in ["good morning", "morning", "start day", "plan my day", "what should i do"]):
            return f"""🌅 **Good morning, Sir. It's {now.strftime('%I:%M %p %A')}.**

Let's make today winnable, not overwhelming.

**Energy check first:** How's your battery? 1-10 energy, 1-10 focus? (Or just say low/medium/high)

While you think, here's your ADHD-friendly start:

**3 MITs max — what 3 would make today feel like a win?**
Pick tiny if needed:
  • "Open Q4 doc" counts
  • "Reply to 1 email" counts
  • "5-min tidy" counts

**Quick dump if brain full:** Say `brain dump [everything on mind]`

**If you already know MITs:** Say `plan my day MITs: [task1, task2, task3] energy: medium`

I'm here, Sir. One step at a time.

Commands:
• `brain dump` — dump everything messy
• `plan my day` — 3 MITs + time blocking
• `break down [task]` — atomize scary task
• `focus on [task]` — Pomodoro + body double
• `log win [what]` — dopamine hit
• `energy check` — match tasks to energy
• `overwhelm` — SOS when frozen
"""

        # Brain dump
        if "brain dump" in p or "dump" in p and len(prompt) > 20:
            # Extract dump content
            dump_text = prompt.replace("brain dump", "").strip()
            if len(dump_text) < 10:
                return """🧠 **Brain Dump Mode — dump everything, Sir.**

Just type everything on your mind, messy is fine. No organizing, no filter.

Example: `brain dump Q4 report due Friday, buy milk, call mom, idea for app, laundry, email client about delay, anxious about meeting`

I'll organize into:
🔥 Urgent / Today
📌 Important / This Week
💡 Ideas / Someday
🏠 Home / Life
💼 Work / Project

Go ahead, Sir. Empty that brilliant, busy brain."""
            else:
                # Simulate organization
                items = [i.strip() for i in dump_text.replace(",", "\n").split("\n") if i.strip()][:8]
                return f"""🧠 **Dump received, Sir. {len(items)} things out of head, safe.**

**Organized:**

🔥 Urgent / Today:
  • {items[0] if items else '—'}

📌 Important / This Week:
  • {items[1] if len(items)>1 else '—'}
  • {items[2] if len(items)>2 else '—'}

💡 Ideas / Someday:
  • {items[3] if len(items)>3 else '—'}

🏠 Home / Life:
  • {items[4] if len(items)>4 else '—'}

💼 Work / Project:
  • {items[5] if len(items)>5 else '—'}

---
**Next:** Pick ONE from 🔥 Urgent. Say `break down [that task]` and I'll atomize it into 2-min steps.

Your brain is not storage, Sir. It's a processor. Good dump.
"""

        # Task breakdown
        if "break down" in p or "atomize" in p or "breakdown" in p:
            task = prompt.replace("break down", "").replace("atomize", "").replace("breakdown", "").strip()
            if len(task) < 5:
                task = "your task"
            return f"""🔬 **Atomized: {task}**

Big task scary. Tiny tasks doable. Each 2-5 min:

1. Define DONE in 10 words or less (2 min)
2. What's blocking you? Name it (1 min)
3. Smallest possible first move? (1 min)
4. Open app/close distractions (2 min)
5. Do first move for just 2 min — timer on (2 min)
6. Check: continue or pause? Permission to pause (30 sec)
7. Next micro-step (1 min)
8. Park with note for future you (1 min)

---
**ADHD Pro Tips:**
• Don't do all steps now. Do step 1 only. That's a win.
• 2-min rule: If you can start in 2 min, you win.
• Body double: Say `body double` and I'll stay with you.

**Next action:** Step 1 — Define DONE for '{task}' in 10 words.

Say it out loud, Sir. I'm here.
"""

        # Focus
        if "focus" in p and ("on" in p or "mode" in p or "pomodoro" in p):
            task = prompt.replace("focus on", "").replace("focus", "").strip() or "your MIT"
            return f"""🎧 **Focus Mode ON — 25 min — Body Double: Yes**

**Task:** {task}
**Timer:** 25 min focus → 5 min break

**Before you start (30 sec):**
  • Phone: DND, face down or other room
  • Tabs: Close all except this task
  • Water nearby
  • Say out loud: "I'm starting {task} for just 2 minutes"

**During focus:**
  • Distracted? Write in parking lot, return. Don't chase.
  • Stuck? Micro-goal for next 2 min only

**Distraction Parking Lot:**
  _ _ _ _ _ _ _ _ _ _

**Body Double ON:** I'm here, Sir. Working alongside you. Not judging, just present.

---
Start now: Timer starts when you say `start`. Or just begin and say `log win` when done.

Your only job for next 25 min: stay with '{task}'
Two minutes counts. Any progress is win.
"""

        # Overwhelm
        if any(k in p for k in ["overwhelm", "frozen", "can't start", "stuck", "panic", "too much", "paralyzed"]):
            return """🆘 **Overwhelm SOS — I'm here, Sir. No judgment.**

First, ground. 30 sec together:

  1. Feet on floor. Feel them. (5 sec)
  2. 4 breaths: in 4, hold 4, out 4, hold 4 (15 sec)
  3. Name 3 things you see, 2 you hear, 1 you feel (10 sec)

---

**Now, shrink the world:**

Brain says EVERYTHING urgent. It's lying, Sir. ADHD does that.

**Pick ONE:**
  • What ONE thing would make today 10% better?
  • What's TINIEST step in next 2 min?
  • Do you need water, food, movement, or rest first?

**If can't pick, I'll pick:**
  → Drink water (30 sec)
  → Write ONE next step on paper (1 min)
  → Timer 2 min, do just that (2 min)

You don't have to fix everything today, Sir. Just one tiny thing.

Say that one tiny thing and I'll help you start.
"""

        # Win tracking
        if "log win" in p or "win" in p and any(k in p for k in ["i did", "finished", "completed"]):
            win_text = prompt.replace("log win", "").strip() or "showed up"
            return f"""🎉 Win logged, Sir! '{win_text}' — dopamine earned.

Today's wins: counting... | Total wins: building...

ADHD brain forgets wins, remembers failures. This log is truth.

Keep going? Say `log win [next]` or `plan my day` for next MIT.
Done? Say `shutdown` to close day with wins review.

Small win, big deal. You're doing it, Sir.
"""

        # Energy check
        if "energy" in p or "tired" in p or "low battery" in p:
            return """**Energy Check — Let's match tasks to state, Sir.**

Rate: Energy 1-10? Focus 1-10? Mood word?

**Quick guide:**

🔋 1-3 energy + 1-3 focus = Low Battery Mode
  • Water, walk, 10-min rest — no guilt
  • Tiny admin: 2-min emails, 3 papers filed
  • Dopamine menu: music, stretch, snack

⚡ 7+ energy + 1-3 focus = Buzzing / Restless
  • Move first: walk, 20 jumping jacks
  • 15-min sprints on physical tasks
  • Voice dictate while moving

🚀 7+ energy + 7+ focus = Hyperfocus Risk
  • Tackle hardest MIT now, 45-min blocks
  • Set alarms: eat, drink, bathroom
  • Log win after — big dopamine

⚖️ 4-6 / 4-6 = Steady
  • Pomodoro 25/5, MIT 1 now

**Dopamine Menu (2-5 min pick one):**
  • 🎵 1 song loud, dance
  • 💧 Cold water + 10 breaths
  • 🚶 5-min walk no phone

Say `energy check 5 6 anxious` or just describe how you feel, Sir.
"""

        # Quick capture
        if "capture" in p or "remember" in p or "note" in p:
            thought = prompt.replace("capture", "").replace("remember", "").strip() or "your thought"
            return f"""📥 Captured, Sir. '{thought[:50]}...' safe, out of head.

Inbox: growing (that's good, means brain emptying)
Tag: task

Your brain can let go now. I will remember.

Want to organize later? `brain dump` or `plan my day`
Want to do now? `break down {thought[:30]}`
Just capturing? Perfect. Keep going.

Quick capture is superpower for ADHD, Sir. 2 sec, no friction.
"""

        # Time estimate
        if "how long" in p or "time estimate" in p or "how much time" in p:
            return """⏱️ **Time Estimate — with ADHD tax, Sir.**

ADHD brain underestimates by 40-200%. Normal, not failure.

**Rule:** Double first guess + 10 min buffer.

Examples:
  • Email you think 10m → realistic 20m
  • Write report think 1h → realistic 2.5h
  • Clean think 20m → realistic 30m

**Why tax:**
  • Starting friction
  • Tab switching, re-reading
  • Perfectionism loop
  • Transitions hard

**Make it real:**
  • Time block realistic + 10 buffer
  • Set timer 25m, work, check actual
  • Data > guilt

Say `time estimate [task] I think [30m]` and I'll reality-check, Sir.
"""

        # Dopamine menu
        if "dopamine" in p:
            return """🍽️ **Dopamine Menu — Healthy Hits for ADHD Brain**

ADHD brain seeks dopamine. Give it good menu, not doom scroll, Sir.

**Appetizers (1-3 min):**
  • 💧 Cold water + 10 breaths (1 min)
  • 🎵 1 favorite song, dance (3 min)
  • 🚶 5-min walk no phone (5 min)
  • 🧊 Splash cold water (30 sec)

**Entrees (3-5 min):**
  • 🧹 Tidy one surface (5 min)
  • 📝 Brain dump 5 things (3 min)
  • 💬 Text someone kind (2 min)
  • 📸 Photo of one win (1 min)

**Sides (5 min):**
  • 🎨 Doodle 5 min
  • 📚 Read 2 pages fun book
  • 🍵 Make tea mindfully

**Desserts (10 min, timer!):**
  • 🎮 10-min game
  • 📺 1 YouTube video
  • 🍫 Favorite snack slow

**Avoid:**
  • ❌ Doom scroll (2 min good, 2h bad)
  • ❌ 5 tabs 'quick check'

Pick one now, Sir. 2 min dopamine, then back to MIT.
"""

        # Habit stack
        if "habit stack" in p or "habit" in p:
            return """🔗 **Habit Stack — Link New to Existing**

**Formula:** After I [existing habit], I will [tiny new habit]

**Why works for ADHD:**
  • Existing habit = anchor, no need to remember when
  • Tiny = 2-min max, no willpower
  • Stack, don't start from scratch

**Examples:**
  • After I make coffee, I will open Q4 doc (30 sec)
  • After I brush teeth, I will brain dump 3 MITs (2 min)
  • After I close laptop, I will log 1 win (30 sec)
  • After I sit at desk, I will set timer 25m + water (1 min)

**Your turn:** Say `habit stack existing: make coffee new: open MIT doc`

One stack at a time, Sir. Tiny habits.
"""

        # Transition
        if "transition" in p:
            return """🔄 **Transition Helper — Transitions Hard for ADHD**

**Why hard:**
  • Hyperfocus makes switching painful
  • Working memory loses context
  • Time blindness

**Shutdown Ritual (2 min):**
  1. Save + close tabs (1 min)
  2. Note: where left off + next step (1 min)
  3. Log win (30 sec)
  4. Stand, stretch, water (30 sec)

**Buffer (5 min mandatory):**
  • Walk, bathroom, water, 3 breaths
  • Dump lingering thoughts

**Startup Ritual (2 min):**
  1. Open only app needed (30 sec)
  2. Say: 'I'm starting [task] for just 2 min' (10 sec)
  3. Timer 25m + water (20 sec)
  4. Define DONE in 10 words (1 min)

Say `transition from: email to: Q4 report` and I'll guide, Sir.

Transitions ARE the work for ADHD brain, not wasted time.
"""

        # If-then
        if "if then" in p or "if-then" in p:
            return """🧩 **If-Then Planning — Pre-Decide for When Executive Function Fails**

**Formula:** If [situation], then I will [tiny action]

**Why works:**
  • Pre-decides when brain offline
  • No in-moment decision
  • 2-3x more likely to follow through

**Examples:**
  • If overwhelmed, then 4 breaths + ONE step
  • If distracted by phone, then phone other room + return
  • If can't start, then break down into 2-min steps
  • If 10am, then energy check + MIT 1
  • If finish MIT, then log win + 5-min break

**Your turn:** Say `if then if: overwhelmed then: 4 breaths + ONE step`

Write on sticky where you'll see trigger, Sir.
"""

        # Weekly review
        if "weekly review" in p or "weekly" in p:
            return """📅 **Weekly Review — No Shame, Only Data**

**Gather:**
  • Wins this week? (tiny counts)
  • Focus sessions? Total min?
  • Energy avg? Check-ins?
  • Overwhelm times? (normal)
  • Top distractions?

**Patterns:**
  • Low energy week → protect battery, tiny admin OK
  • High energy → rode wave well?
  • Overwhelm >3x → brain full? More dumps, fewer MITs?
  • Top distractions → fix environment, not you

**What Worked?**
  • Which MIT time worked best? Morning? After walk?
  • Which focus length? 15, 25, 45?
  • What dopamine menu helped?

**Next Week Experiment — Pick ONE:**
  • One habit stack
  • One if-then
  • Energy tracking same time daily
  • 3 MITs max, no more

Say `weekly review` for full data, Sir. You're learning your brain.
"""

        # Shutdown ritual
        if "shutdown" in p:
            return """🌙 **Shutdown Ritual — End of Day**

ADHD brain needs closure or loops all night.

**Step 1: Wins (tiny counts)**
  Say: `shutdown wins: opened doc, replied email, 5-min tidy`

**Step 2: Brain Dump Tomorrow Worries (2 min)**
  Park everything messy, brain can let go

**Step 3: Tomorrow's 3 MITs (max 3)**
  What 3 would make tomorrow win? Tiny OK:
    • 'Open Q4 doc' counts
    • 'Reply to 1 email' counts

**Step 4: Close Tabs Physically**
  • Close tabs, save docs
  • Note: where left off + next step for MIT 1
  • Clear desk one surface

**Step 5: Permission to Stop**
  You did enough today, Sir. Any progress counts.
  Rest is productive for ADHD brain.

Say `shutdown wins: [wins] tomorrow: [3 MITs]` to close day, Sir.
"""

        # Default ADHD coach response
        return f"""🧠 **JARVIS ADHD Coach — At your service, Sir.**

You said: "{prompt[:100]}..."

I hear you. ADHD makes this hard, not you. Let's make it tiny and winnable.

**What would help most right now?**

  • Brain full? → `brain dump [everything messy]`
  • Big scary task? → `break down [task]`
  • Need day plan? → `plan my day MITs: [3 tasks] energy: medium`
  • Can't start? → `focus on [task]` + body double
  • Overwhelmed? → `overwhelm`
  • Did something? → `log win [what]` for dopamine
  • Energy low? → `energy check`
  • Quick thought? → `capture [thought]`

**My promise, Sir:**
  • Max 3 MITs — constraints are kindness
  • One next step, not 10
  • No shame, only data and tiny wins
  • I'm here, working alongside you

**Next action:** Tell me ONE thing on your mind, and I'll shrink it to 2 minutes.

What's on your mind, Sir?
"""

    def run(self, prompt: str, context: str = "", **kwargs) -> AgentResponse:
        # Try to use tools first for structured actions
        p_lower = prompt.lower()

        # Tool routing for mock (offline)
        if self.engine.__class__.__name__ == "MockEngine" or kwargs.get("mock"):
            # Use mock ADHD response that feels real
            content = self._mock_adhd_response(prompt, context)
            return AgentResponse(content=content, model="adhd-coach-mock")

        # Real engine: gather tool outputs then generate
        tool_outputs = []
        tools_to_try = []

        if any(k in p_lower for k in ["brain dump", "dump", "too much", "everything"]):
            tools_to_try.append("brain_dump")
        if any(k in p_lower for k in ["break down", "atomize", "scary", "can't start"]):
            tools_to_try.append("task_breakdown")
        if any(k in p_lower for k in ["plan my day", "mits", "day plan", "schedule"]):
            tools_to_try.append("day_planner")
        if any(k in p_lower for k in ["focus", "pomodoro", "body double"]):
            tools_to_try.append("focus")
        if any(k in p_lower for k in ["capture", "remember this"]):
            tools_to_try.append("quick_capture")
        if any(k in p_lower for k in ["energy", "tired", "battery"]):
            tools_to_try.append("energy_check")
        if any(k in p_lower for k in ["win", "did it", "finished"]):
            tools_to_try.append("win_tracker")
        if any(k in p_lower for k in ["overwhelm", "frozen", "stuck", "panic"]):
            tools_to_try.append("overwhelm")
        if any(k in p_lower for k in ["how long", "time estimate", "how much time"]):
            tools_to_try.append("time_estimator")
        if any(k in p_lower for k in ["distract"]):
            tools_to_try.append("distraction_log")

        # If no specific tool, try brain_dump + day_planner as defaults for ADHD
        if not tools_to_try:
            tools_to_try = ["quick_capture"]

        for tool_name in tools_to_try[:2]:  # max 2 tools to avoid overload
            try:
                tools = get_tools([tool_name])
                if tools:
                    tool = tools[0]
                    # Build args heuristically
                    if tool_name == "brain_dump":
                        out = tool.run(dump=prompt)
                    elif tool_name == "task_breakdown":
                        out = tool.run(task=prompt)
                    elif tool_name == "quick_capture":
                        out = tool.run(thought=prompt)
                    elif tool_name == "win_tracker":
                        if "show" in p_lower or "wins" in p_lower:
                            out = tool.run(show=True)
                        else:
                            out = tool.run(win=prompt)
                    elif tool_name == "overwhelm":
                        out = tool.run(feeling=prompt)
                    elif tool_name == "energy_check":
                        out = tool.run()
                    elif tool_name == "distraction_log":
                        out = tool.run(distraction=prompt)
                    elif tool_name == "time_estimator":
                        out = tool.run(task=prompt)
                    elif tool_name == "day_planner":
                        out = tool.run(mits=prompt)
                    elif tool_name == "focus":
                        out = tool.run(task=prompt)
                    else:
                        out = tool.run()
                    tool_outputs.append(f"[{tool_name}]\n{out}")
            except Exception as e:
                tool_outputs.append(f"[{tool_name}] error: {e}")

        combined_context = "\n\n".join(tool_outputs)
        if context:
            combined_context += f"\n\nUser context:\n{context}"

        messages = [
            Message(role=Role.SYSTEM, content=SYSTEM_PROMPT),
            Message(role=Role.USER, content=f"Tool outputs (use them, don't repeat verbatim, be ADHD-coach):\n{combined_context}\n\nUser request: {prompt}\n\nRespond as ADHD co-pilot JARVIS: witty Sir, one next step, celebrate tiny wins, no shame. Keep formatting ADHD-friendly with bullets, emojis, bold."),
        ]
        return self.engine.generate(messages)
