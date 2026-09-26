# JARVIS Business OS — Agentic Harness + OpenAI + Goals + Memory — SHILATECH

> Teach JARVIS your goals, priorities, business, workflows, rules and standards + persistent memory

This guide covers the 4 steps you asked for:

1. **Install agentic harness**
2. **Use OpenAI as AI model**
3. **Teach JARVIS my goals and priorities, business and workflows, rules and standards**
4. **Give it persistent memory**

---

## 1. Install Agentic Harness

JARVIS Business OS is an agentic harness — agents + tools + engines + memory + business profile.

### Quick Install

```bat
# Clone latest main (modern circular HUD v0.1.9.9+)
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
git checkout main
git pull

# Full harness: server, memory, tools-search, voice
pip install -e .[server,memory,tools-search,voice] --break-system-packages

# Verify harness
jarvis business harness
# Should show: 21 agents, 56 tools, engines, memory, business profile
```

### What You Get — Agentic Harness

- **21 Agents**: `business_os`, `ironman`, `simple`, `react`, `orchestrator`, `code_assistant`, `deep_research`, `morning_digest`, `adhd_coach`, etc.
- **56 Tools**: `business_profile`, `business_goals`, `business_priorities`, `business_workflows`, `business_rules`, `business_memory`, `memory_search`, `memory_write`, `file_read`, `file_write`, `shell`, `web_search`, `tavily_search`, `ddgs_search`, `task_breakdown`, `day_planner`, `focus`, `quick_capture`, `win_tracker`, `calendar`, `weather`, `proactive_briefing`, `network_status`, `hybrid_mode`, etc.
- **8 Engines**: `openai`, `ollama`, `mock`, `vllm`, `mlx`, `litellm`, `gemma_cpp`, `auto` (hybrid online/offline)
- **Memory**: Vector FAISS + keyword fallback, persistent in `~/.jarvis/memory/`
- **Business Profile**: `~/.jarvis/business_profile.toml` + JSON + memory store

### Check Harness

```bat
jarvis doctor
jarvis agents
jarvis business harness
```

---

## 2. Use OpenAI as AI Model

Business OS uses OpenAI as primary brain (gpt-4o-mini fast/cheap or gpt-4o best) with offline fallback mock/ollama.

### Setup OpenAI

```bat
# 1. Get API key from https://platform.openai.com/api-keys

# 2. Set env (Windows PowerShell)
$env:OPENAI_API_KEY="sk-proj-..."

# Or Windows CMD
set OPENAI_API_KEY=sk-proj-...

# Or Linux/Mac
export OPENAI_API_KEY=sk-proj-...

# 3. Configure JARVIS to use OpenAI + business-os preset
jarvis business openai --model gpt-4o-mini
# Or gpt-4o for best quality
jarvis business openai --model gpt-4o

# 4. Verify
jarvis business openai --show
# Should show Engine: openai, Model: gpt-4o-mini, API Key Set: ✅ Yes

# 5. Test with OpenAI brain
jarvis ask --agent business_os --engine openai "Good morning, what should I work on today?"
jarvis chat --agent business_os --engine openai
```

### Config File

`~/.jarvis/config.toml` after setup:

```toml
preset = "business-os"

[engine]
type = "openai"
model = "gpt-4o-mini"
api_url = "https://api.openai.com/v1/chat/completions"
temperature = 0.7
max_tokens = 2048
# api_key read from OPENAI_API_KEY env

[auto]
online_engine = "auto"
offline_engine = "mock"
# Hybrid: online=openai best, offline=mock/tinyllama
```

### Offline Fallback

- **Online**: OpenAI if `OPENAI_API_KEY` set → prompt sent HTTPS to OpenAI API, best quality
- **Offline**: `mock` always works or `ollama` tinyllama 1.1B local — nothing leaves device
- **Hybrid Auto**: `auto` engine checks network, picks openai online, mock offline
- **User Decides**: `jarvis chat --interactive` → 1 Full Stack Online vs 2 Basic Offline Local even online

---

## 3. Teach JARVIS Your Goals, Priorities, Business, Workflows, Rules and Standards

### Business Profile — The Brain

Stored in `~/.jarvis/business_profile.toml` + `~/.jarvis/business_profile.json` + vector memory.

Structure:

- **Goals**: north_star, long_term_1y, short_term_90d, short_term_30d, personal
- **Priorities**: mit_today (3 MITs), urgent_important, important_not_urgent, pillars
- **Business**: name, tagline, location, mission, vision, values, products, target_customer, revenue_model
- **Workflows**: daily_routine, weekly_review, sop_development, sop_business
- **Rules**: coding_standards, business_rules, communication, decision_framework

### Quick Teach — Interactive Onboarding

```bat
# Interactive wizard — 5 steps: goals, MITs, business, workflows, rules
jarvis business teach

# It asks:
# Step 1: North Star (1 sentence ultimate goal)
# Step 2: MITs Today (3 Most Important Tasks)
# Step 3: Business name + mission
# Step 4: Daily routine
# Step 5: Business rule

# Saves to business_profile.toml + memory store
```

### Manual Teach — Specific Sections

```bat
# Initialize
jarvis business init --name Eugene --business-name SHILATECH --north-star "Build SHILATECH into leading personal AI company" --force

# Show full profile
jarvis business profile --action show

# Goals
jarvis business goals --action show
jarvis business goals --action set_north_star --goal "Build personal AI that runs on personal devices, private by default"
jarvis business goals --action add --goal "Launch JARVIS v1.0 with modern circular HUD" --timeframe 90d
jarvis business goals --action add --goal "Acquire 1000 users" --timeframe 1y

# Priorities — MITs Today
jarvis business priorities --action show
jarvis business priorities --action set_mits --priority "Ship Business OS with OpenAI+memory,Fix modern HUD MSI,Setup business profile"

# Business
jarvis business profile --action edit --business-name SHILATECH --mission "Build local-first personal AI, Iron Man quality" --user-name Eugene

# Workflows
jarvis business workflows --action show
jarvis business workflows --action add --workflow "06:00 Good morning Eugene + 3 MITs alignment" --type daily
jarvis business workflows --action add --workflow "Ship daily — Push code, release, feedback" --type daily
jarvis business workflows --action add --workflow "Never show green fallback UI — Always modern circular HUD" --type sop_dev

# Rules
jarvis business rules --action show
jarvis business rules --action add --rule "Always SHILATECH, never Stark Industries" --type business
jarvis business rules --action add --rule "Voice must work both online/offline, Sir" --type business
jarvis business rules --action add --rule "Python 3.11+, type hints, modern circular HUD standard" --type coding
```

### Business OS Agent — Knows Your Business

Once taught, Business OS agent uses your profile + memory for every response:

```bat
# Ask about goals — uses business profile
jarvis ask --agent business_os --engine openai "What are my goals?"

# Ask priorities — uses MITs
jarvis ask --agent business_os --engine openai "What should I work on today?"

# Ask workflows
jarvis ask --agent business_os --engine openai "What is my daily routine?"

# Ask rules
jarvis ask --agent business_os --engine openai "What are my business rules?"

# Morning briefing — proactive, aligns to north star + MITs
jarvis ask --agent business_os --engine openai "Good morning"
# Returns: Good morning Eugene, Sir. North Star: Build SHILATECH... 3 MITs today: Ship Business OS, Fix HUD, Setup profile... Shall I break down MIT #1?

# Business profile
jarvis ask --agent business_os --engine openai "Tell me about my business"
```

---

## 4. Give It Persistent Memory

### Memory System

- **Location**: `~/.jarvis/memory/memories.jsonl` + `~/.jarvis/business_profile.toml/json`
- **Type**: Vector FAISS (if `pip install -e .[memory]`) + keyword fallback
- **Search**: Semantic vector search or keyword overlap
- **Persistent**: Survives reboots, saved to disk, loaded on startup

### Business Memory Tools

```bat
# Save to persistent memory
jarvis business memory --action save --content "My new goal is to launch JARVIS mobile app in 60 days"
jarvis business memory --action save --content "SHILATECH workflow: Customer First — Understand problem before solution"
jarvis business memory --action save --content "Business rule: Version bump forces upgrade — Don't force-push same tag"

# Search memory (vector)
jarvis business memory --action search --query "What are my goals?"
jarvis business memory --action search --query "SHILATECH workflows"
jarvis business memory --action search --query "business rules"

# List recent memories
jarvis business memory --action list

# Stats
jarvis business memory --action stats
# Shows count, FAISS available, embedding model

# Also via generic memory
jarvis remember "My target customer is power users who want private local AI"
jarvis memory "SHILATECH" --top-k 5
```

### How Memory Works — Business OS

1. **Save**: When you `business init`, `business teach`, or `business goals add`, it saves to:
   - `business_profile.toml` (structured TOML)
   - `business_profile.json` (JSON for vector ingestion)
   - `memories.jsonl` (vector store — each goal, MIT, pillar, rule as separate entry with metadata)

2. **Search**: `BusinessOSAgent` on every prompt does `memory_search` for relevant context:
   - Searches for user name + goals + priorities
   - Injects into system prompt: `Memory context: - North Star: Build SHILATECH...`
   - Uses for decision: aligns tasks to north star, MITs

3. **Persistent**: Memory survives:
   - Reboots (saved to disk)
   - Online/offline switches (local file)
   - Engine switches (openai vs mock vs ollama)

### Enable Vector Memory (FAISS)

For best memory — semantic search, not just keyword:

```bat
pip install -e .[memory] --break-system-packages
# Installs faiss-cpu + sentence-transformers all-MiniLM-L6-v2

jarvis business memory --action stats
# Should show faiss_available: true, bm25_available: true

# Test vector search
jarvis business memory --action search --query "What is my north star goal for SHILATECH?"
# Returns semantic matches even if words differ
```

### Memory in Business OS Agent

Business OS agent automatically:

- **Loads** business profile on startup
- **Searches** memory for goals, priorities, business context
- **Injects** into system prompt: business context + memory context + time
- **Saves** new learnings via `memory_write` tool
- **Uses** for proactive suggestions: "Sir, this aligns to your MIT #1"

---

## Full Setup — 5 Minutes

```bat
# 1. Install harness
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
pip install -e .[server,memory,tools-search,voice] --break-system-packages
jarvis business harness

# 2. Setup OpenAI brain
$env:OPENAI_API_KEY="sk-proj-..."  # PowerShell
jarvis business openai --model gpt-4o-mini
jarvis init business-os --force

# 3. Teach business
jarvis business init --name Eugene --business-name SHILATECH --north-star "Build SHILATECH into leading personal AI company — local-first, Iron Man quality" --force
jarvis business teach
# Interactive: north star, MITs, business, workflows, rules

# Or manual:
jarvis business goals --action set_north_star --goal "Build personal AI that runs on personal devices, private by default, Iron Man quality"
jarvis business priorities --action set_mits --priority "Ship Business OS,Fix modern HUD,Setup OpenAI+memory"
jarvis business workflows --action add --workflow "06:00 Good morning Eugene + 3 MITs" --type daily
jarvis business rules --action add --rule "Always SHILATECH, never Stark" --type business

# 4. Persistent memory — already saved via above, but add more
jarvis business memory --action save --content "My business SHILATECH builds JARVIS modern circular HUD 13 72 ticks 60 segments voice auto-init"
jarvis business memory --action stats
jarvis business memory --action search --query "SHILATECH goals"

# 5. Test Business OS
jarvis ask --agent business_os --engine openai "Good morning, what should I work on today?"
jarvis ask --agent business_os --engine openai "What are my goals and MITs today?"
jarvis chat --agent business_os --engine openai
# In chat: "Teach me about my business", "What are my workflows?", "How is my data secure?"

# 6. Desktop — Modern circular HUD with Business OS
python app.py
# Or frontend
cd frontend && npm run dev
# Circular HUD 13 72 ticks 60 segments, chat with business_os agent, voice auto-init
```

---

## Business OS in Desktop & Frontend

### Desktop `app.py` — Circular HUD

- Already has business profile integration via `business_profile` tool
- Chat with business_os: type `What should I work on today?` → uses business profile
- Voice auto-init speaks Good morning with MITs from business profile

### Frontend `IronManCircularHUD.tsx`

- Same — can chat with business_os agent via API
- Future: Add business profile panel to HUD

---

## Security — Data Protection

- **Local-first**: Business profile + memory stored in `~/.jarvis/` local, not cloud
- **OpenAI**: Only prompt sent HTTPS to OpenAI API if you set key and choose openai engine — you decide
- **Offline**: mock/ollama — nothing leaves device, 100% private
- **Hybrid**: `auto` engine — online=openai best quality, offline=mock local — user decides Full vs Basic when online
- **No telemetry**: `telemetry.enabled = false`, Apache 2.0
- **SHILATECH Secure**: Encrypted, private by default

---

## Next Steps

- `jarvis business teach` — Interactive onboarding to teach full business
- `jarvis business memory --action search --query "X"` — Search persistent memory
- `jarvis ask --agent business_os --engine openai "Plan my day with 3 MITs"` — Daily planning
- `jarvis business workflows --action add --workflow "Your SOP" --type sop_dev` — Add SOPs
- `jarvis business rules --action add --rule "Your rule" --type business` — Add rules
- `python app.py` — Modern circular HUD with Business OS

**SHILATECH • Malibu Point 10880 • Modern Circular HUD 13 • Voice Auto-Init • Business OS • Persistent Memory • OpenAI Brain**

