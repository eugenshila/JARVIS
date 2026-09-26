# JARVIS ADHD Co-Pilot — Built for ADHD Brain

> **Your brain is not broken, Sir. It needs a different OS.** JARVIS is that OS.

ADHD is not lack of intelligence or willpower. It's executive dysfunction, time blindness, working memory limits, and dopamine regulation. JARVIS is designed for that.

---

## Why Regular Productivity Tools Fail ADHD

| Regular Tool | Why It Fails ADHD | JARVIS ADHD Fix |
|--------------|-------------------|-----------------|
| Long todo lists (20 items) | Overwhelm, paralysis | **Max 3 MITs** — constraints are kindness |
| Big tasks "Write report" | Can't start, executive dysfunction | **Task Atomizer** — breaks into 2-min micro-steps |
| "Just focus" | Time blindness, no visual timer | **Pomodoro++** — visual timer + body doubling + break alarms |
| "Remember to..." | Working memory weak | **Zero-friction capture** — 2 sec, no organizing |
| No celebration | Dopamine seeking, forgets wins | **Win tracker** — logs tiny wins, streaks, celebration |
| Ignores energy | Does hard tasks on low battery | **Energy check** — matches tasks to energy/mood |
| Shame when stuck | RSD, negative self-talk | **Overwhelm SOS** — grounding + ONE step, no shame |

---

## Core Features

### 1. 🧠 Brain Dump → Organized
When brain feels full.

```bash
jarvis ask --agent adhd_coach --mock "brain dump Q4 report due Friday, buy milk, call mom, idea for app, laundry, email client about delay, anxious about meeting"
```

JARVIS organizes into:
- 🔥 Urgent / Today
- 📌 Important / This Week
- 💡 Ideas / Someday
- 🏠 Home / Life
- 💼 Work / Project
- 📧 Comms / People

**CLI:**
```bash
jarvis adhd
> brain dump everything on mind messy is fine
```

### 2. 🔬 Task Atomizer — 2-Min Steps
Big scary tasks → tiny doable steps.

```bash
jarvis breakdown "write Q4 report"
# or
jarvis ask --agent adhd_coach --mock "break down write Q4 report"
```

Output:
```
1. Open doc/app for 'write Q4 report' (30 sec) - just open it
2. Write terrible first line (2 min)
3. Bullet 3 main points (3 min)
4. Expand first bullet (5 min)
...
Next action: Open doc
```

**ADHD Pro Tips:**
- Don't do all steps now. Do step 1 only. That's a win.
- 2-minute rule: If you can start in 2 min, you win.
- Body double: `body double` and JARVIS stays with you.

### 3. 📅 ADHD Day Planner — 3 MITs Max
Never more than 3. With energy matching, time blocking + buffers.

```bash
jarvis adhd --mits "Q4 brief, reply to client, 5-min tidy" --energy medium
# or interactive:
jarvis ask --agent adhd_coach --mock "plan my day MITs: Q4 brief, email client, tidy desk energy: low"
```

Output:
```
📅 ADHD Day Plan — Monday May 13 — Energy: MEDIUM

Energy Note: Medium energy - your baseline. Standard Pomodoro works.
Focus Pattern: 25 min focus / 5 min break

Your 3 MITs:
  1. Q4 brief
  2. email client
  3. tidy desk

Time-Blocked Day (with buffers):
  09:00 AM - 09:15 AM | 🌅 Morning Start-Up | Water, meds, 1-min breathing
  09:20 AM - 10:05 AM | 🔥 MIT 1: Q4 brief | Hardest first, phone other room
  10:10 AM - 10:25 AM | ☕ Break / Dopamine | Walk, snack, water
  10:30 AM - 11:10 AM | 🎯 MIT 2: email client | Second wind
  ...

ADHD Rules:
• 3 MITs only. If you do 1, you win. 2 is amazing. 3 is legendary.
• Time blocks are guesses, not prisons.
• 5-min transition buffers mandatory.
```

### 4. 🎧 Focus Mode — Pomodoro++ with Body Doubling
ADHD needs body doubling (someone present) more than willpower.

```bash
jarvis focus "Q4 brief" --duration 25
# or
jarvis ask --agent adhd_coach --mock "focus on Q4 brief"
```

Features:
- 15m sprint (low energy), 25m Pomodoro (medium), 45m deep (high)
- Body double: "I'm here, Sir. Working alongside you. Not judging, just present."
- Distraction parking lot — write, don't chase
- Visual timer + break alarms (you will forget to break)
- Commands during focus: `distraction [thought]`, `stuck`, `break`, `log win`

### 5. 📥 Quick Capture — Zero Friction
ADHD brain has thoughts that vanish in 10 sec. Capture in 2 sec.

```bash
jarvis capture "buy milk tomorrow"
jarvis capture "idea: app for ADHD time blindness" --tag idea
```

No organizing needed. Just capture. Organize later via brain dump.

### 6. ⚡ Energy Check → Task Matching
Don't do hard tasks on low battery.

```bash
jarvis ask --agent adhd_coach --mock "energy check 3 4 anxious"
```

States:
- 🔋 Low Battery (1-3 energy, 1-3 focus): water, walk, tiny admin, dopamine menu
- 🧠 Wired but Tired (low energy, high focus): planning, organizing, not doing
- ⚡ Buzzing / Restless (high energy, low focus): move first, 15-min physical sprints
- 🚀 Hyperfocus Risk (7+ both): use it! 45-min blocks + alarms for eat/drink
- ⚖️ Steady (4-6): Pomodoro 25/5

Includes Dopamine Menu (2-5 min):
- 🎵 1 song loud, dance
- 💧 Cold water + 10 breaths
- 🚶 5-min walk no phone
- 🧹 Tidy one surface
- 💬 Text someone kind

### 7. 🏆 Win Tracker — Dopamine Hits
ADHD brain forgets wins, remembers failures. This log is truth.

```bash
jarvis log-win "opened doc"
jarvis log-win --show
```

Tiny wins count:
- "opened doc" counts
- "drank water" counts
- "started" counts
- "replied to 1 email" counts

Celebrations + streaks. Progress, not perfection.

### 8. 🆘 Overwhelm SOS
When frozen, panicked, too much.

```bash
jarvis ask --agent adhd_coach --mock "overwhelm I have too much to do and can't start"
```

Flow:
1. Grounding: feet on floor, 4 breaths, name 3 things you see
2. Shrink world: ONE thing that makes today 10% better? TINIEST step in 2 min? Need water/food/movement?
3. If can't pick, JARVIS picks: drink water (30 sec) → write ONE next step (1 min) → timer 2 min

No judgment. Only one next step.

### 9. ⏱️ Time Blindness Antidote
ADHD underestimates time by 40-200%. Normal, not failure.

```bash
jarvis ask --agent adhd_coach --mock "time estimate write report I think 30m"
```

Output:
```
Your estimate: 30m
Realistic (with ADHD tax): 75 min
Base + Tax: 30 min × 2.5 = 75 min
Why tax: starting friction, research rabbit holes, editing loop

⚠️ Planning fallacy alert! You estimated 30, realistic 75 — 45 min gap.

Make it real:
  • Time block 85 min (realistic + 10 buffer)
  • Set timer 25 min, work, then check actual
```

Rule: Double first guess + 10 min buffer — usually close.

### 10. 📊 Distraction Log — Data, Not Failure
Log distractions to find patterns, fix environment not you.

```bash
jarvis ask --agent adhd_coach --mock "distraction phone instagram"
```

Patterns:
- Phone → phone other room, grayscale, app blockers
- Hunger/thirst → water + snack before focus
- People → headphones, sign, focus hours
- Thoughts → parking lot, brain dump

---

## Daily Rituals for ADHD

### Morning Start-Up (15 min, with JARVIS)
```bash
jarvis adhd
> Good morning
# JARVIS: energy check + 3 MITs?
> energy check 5 6 calm
> plan my day MITs: Q4 brief, email client, 5-min tidy energy: medium
```

### Focus Loop (repeat)
```bash
> focus on Q4 brief
# 25 min work
> log win finished first draft of Q4 brief
> break 5 min walk
```

### Overwhelm Anytime
```bash
> overwhelm
# grounding + ONE step
> break down [that one step]
> focus on [first micro-step]
```

### Shutdown Ritual (10 min, with JARVIS)
```bash
> show wins
# See today's wins
> brain dump tomorrow worries
> plan my day for tomorrow MITs: ...
> shutdown
# JARVIS: What went well? 1 win to log. Close tabs.
```

---

## CLI Reference

```bash
# Interactive ADHD co-pilot
jarvis adhd
jarvis adhd --mits "task1, task2, task3" --energy medium
jarvis adhd --engine ollama  # with local LLM
jarvis adhd --engine openai  # with cloud LLM

# Quick commands (no interactive)
jarvis capture "buy milk" --tag task
jarvis breakdown "write Q4 report"
jarvis focus "Q4 brief" --duration 25
jarvis log-win "opened doc"
jarvis log-win --show

# Agent direct
jarvis ask --agent adhd_coach --mock "brain dump ..."
jarvis ask --agent adhd_coach --mock "break down ..."
jarvis ask --agent adhd_coach --mock "plan my day MITs: ..."
jarvis ask --agent adhd_coach --mock "overwhelm"
jarvis ask --agent adhd_coach --mock "energy check 4 5 anxious"
jarvis ask --agent adhd_coach --mock "time estimate write report I think 30m"

# With real LLM
jarvis ask --agent adhd_coach --engine ollama "brain dump ..."
```

---

## Frontend — ADHD Mode

```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
# Default is ADHD Co-Pilot mode (purple)
# Switch to Iron Man or Classic Chat top right
```

Features:
- Left: Quick Start buttons, Focus Timers (15/25/45/5), Dopamine Menu, Wins
- Center: Chat with ADHD coach
- Right: Today's MITs (max 3), ADHD Toolkit, Why this works

Visual timer with notifications.

---

## Why This Works — ADHD Science

**Executive dysfunction:** Brain knows what to do, can't start. Fix: Make first step 2-min tiny, externalize, body double.

**Time blindness:** No sense of time passing. Fix: Visual timer, realistic estimates with ADHD tax, buffers, alarms.

**Working memory:** Can't hold many things. Fix: Capture fast (2 sec), brain dump, max 3 MITs.

**Overwhelm:** Everything feels urgent. Fix: Shrink to ONE next step, grounding, categories.

**Dopamine:** Seeks novelty, forgets wins. Fix: Tiny win tracking, celebration, streaks, dopamine menu, novelty in micro-steps.

**Hyperfocus:** Forgets to eat/break. Fix: Break alarms, body double check-ins, transition buffers.

**RSD (Rejection Sensitive Dysphoria):** Shame spiral. Fix: No shame language, warm witty Sir, failure is data, any progress counts.

**Planning fallacy:** Underestimates time. Fix: ADHD tax 1.5-2.5x, double + 10 buffer, track actual vs estimate.

---

## Future Features for ADHD (Roadmap)

**Next:**
- [ ] Voice capture: "Hey JARVIS capture..." hands-free
- [ ] Calendar integration: auto-suggest MITs from calendar + energy
- [ ] Habit stacking: link new habit to existing
- [ ] Transition helper: 5-min warnings + shutdown/startup rituals
- [ ] Hyperfocus guard: detects long focus, reminds to break/eat
- [ ] Body double video: virtual co-working room
- [ ] Reward system: points, levels, real rewards
- [ ] Weekly review: patterns, wins, what worked

**Later:**
- [ ] Integration with Todoist, Notion, Obsidian
- [ ] Phone app with widget for quick capture
- [ ] Smartwatch haptics for time blindness
- [ ] AI learns your energy patterns, suggests best MIT time
- [ ] Community body doubling

---

## Try Now — Offline Mock (No API Key)

```bash
pip install -e .
jarvis adhd --engine mock

> Good morning
> brain dump Q4 report due Friday, buy milk, call mom, laundry, anxious about meeting
> plan my day MITs: Q4 brief draft, email client, 5-min desk tidy energy: medium
> break down Q4 brief draft
> focus on Q4 brief draft
> log win opened doc and wrote terrible first line
> energy check
> overwhelm
> show wins
```

Every command works offline with mock. For real LLM: `ollama pull llama3.2:3b` + `--engine ollama` or set `OPENAI_API_KEY` + `--engine openai`.

---

**Your brain is not broken, Sir. It needs a different OS. JARVIS is that OS.**

*Built with How to ADHD, ADHD 2.0, and lived experience. No shame, only tiny wins.*
