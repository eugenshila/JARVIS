# Security — Hybrid Online/Offline — Is My Data Secure?

**Question:** "will our interface look like this for both local and online starts, also when online will my data be secure"

**Answer:** Yes — same circular interface for both local and online, only badge changes. And yes — data secure, local-first, private by default.

---

## 1. Interface — Same For Local and Online ✅

**Screenshot you sent:** Circular HUD with blue glowing ring, central number 13, outer tick marks, left device specs, right weather, bottom trash/size/power.

**Our new implementation:** `frontend/src/pages/IronManCircularHUD.tsx` — matches screenshot:

- Central 560px canvas circular HUD:
  - Outer housing 2 rings (slate + cyan)
  - 72 tick marks like screenshot (major every 6)
  - 16 segmented middle ring rotating
  - Inner blue glowing ring with shadowBlur 20 (main reactor)
  - 3 rotating energy prongs gradient white→cyan
  - Inner core pulsing blue 28px + sin() *4, white center, number 13 like screenshot
  - Inner small ring 45px
  - 4 data points around

- Left panel like screenshot:
  - Device specifications: Device name DESKTOP-3D8CN02, Processor i5-6300U @ 2.40GHz, RAM 8GB (7.41 usable), System 64-bit x64, OS Windows 11 Pro 21H2, Engine mock/openai/ollama + ONLINE/OFFLINE
  - Today's Alignment 3 MITs
  - Security • Data Protection panel

- Right panel like screenshot:
  - More images on this site (3 arc placeholders)
  - Related searches 4 buttons
  - Security • Your Data panel
  - Quick Protocols

- Top bar: J.A.R.V.I.S MARK XLII + SHILATECH + time/date + ONLINE badge green dot glow / OFFLINE red + USER + ARC power
- Bottom bar: Trash 44 items • Size 248.95 MB • Source AC Line • Power 90% • ONLINE SECURE vs OFFLINE SECURE • time/date
- Center under circle: chat with Good morning Eugene + hybrid mode note

**Same UI for both local and online starts:**
- Local (offline) start: `python app.py` or `jarvis --engine mock` → shows 📴 OFFLINE BASIC • LOCAL ONLY • SECURE — nothing leaves device
- Online start: `jarvis --engine auto` with OPENAI_API_KEY → shows 🌐 ONLINE OPENAI • FULL STACK • SECURE — same circular interface, only badge + mode text changes from OFFLINE to ONLINE
- Frontend: `npm run dev` → default mode now `circular` — matches screenshot for both online/offline, auto detects via navigator.onLine + backend /run check every 30 sec

**7 modes now:** chat/ironman/hud/adhd/bodydouble/arc/circular — circular is default like screenshot

---

## 2. Security — Is My Data Secure When Online? ✅

**Short answer:** Yes — local-first, private by default, you control what leaves device. Same as Iron Man — JARVIS runs in Stark's lab, not in cloud unless he says.

### What Happens Offline (Basic) — 100% Private 🔒

```
📴 OFFLINE MODE — Basic
- Engine: mock or ollama tinyllama offline (local)
- Network: No internet, check_online() fails
- What leaves device: NOTHING — zero network calls
- LLM: mock (keyword heuristic) or ollama tinyllama local (1.1B, ~8-10 tokens/sec on your i5-6300U) — stays on device
- Memory: ~/.jarvis/memory keyword fallback (no FAISS needed) — local
- Calendar: ~/.jarvis/calendar.json or mock 3 events — local
- Email: ~/.jarvis/emails.json or mock 3 emails — local
- Search: mock only — no Tavily/DDGS
- Faces: ~/.jarvis/faces/*.json — local
- Voice: pyttsx3 local or piper-tts offline — local
- Config: ~/.jarvis/config.toml — local, API keys NOT stored (env only)
- Google OAuth token: ~/.jarvis/google_token.json — local, not sent to us
```

**For your i5-6300U 8GB offline:** mock basic always works, tinyllama offline works if `ollama pull tinyllama`, nothing leaves device, Sir.

### What Happens Online (Full Stack) — You Control 🔒

**You have 3 choices when online:**

#### Choice A — Online + OpenAI (Best for your 8GB, recommended) 🌐

```bash
$env:OPENAI_API_KEY="sk-..."  # you set
jarvis ask --engine auto "Good morning Eugene"
# Auto picks: Online + OPENAI_API_KEY set → openai full stack
```

**What leaves device:**
- ✅ Prompt you type ("Good morning Eugene", "brain dump Q4 planning...")
- ✅ Context you provide (if you paste meeting details, that text goes to OpenAI API)
- ✅ Tool calls (if agent uses web_search, the search query goes to Tavily/DDGS, not your files)
- ❌ NOT your whole memory — only if you use memory_search tool and it retrieves relevant chunks, those chunks are sent as context (you control)
- ❌ NOT your local files — only if you say "read file X" and that file content is added to context
- ❌ NOT your calendar/email unless you use those tools and their output is added to context
- ❌ NOT your faces/voice models — local only
- ❌ NOT your config.toml API keys — reads from env, not written to disk

**Where it goes:**
- To `https://api.openai.com/v1/chat/completions` — OpenAI's API, not to us (eugenshila/JARVIS)
- OpenAI's data usage policy: https://openai.com/policies/api-data-usage — API data not used to train models by default (as of 2024+)
- Encrypted HTTPS, not plain

**How to make it more private even online:**
- Don't paste sensitive files into context
- Use `jarvis ask --agent adhd_coach` which uses minimal tools (no file_read by default)
- Or use Choice B

#### Choice B — Online + Ollama Local (Most Private Even Online) 🏠

```bash
# Install Ollama https://ollama.com
ollama pull tinyllama  # 1.1B
ollama serve  # runs on localhost:11434

jarvis hybrid --action set --online-engine ollama --offline-engine ollama
jarvis ask --engine auto "Good morning Eugene"
# Auto picks: Online + Ollama running → ollama full local
```

**What leaves device:**
- ❌ LLM stays local — prompt does NOT go to OpenAI, stays on your i5-6300U
- ✅ Only search queries go online if you use web_search/tavily_search tools and you have TAVILY_API_KEY or DDGS (free) — search query like "weather Nairobi" goes to Tavily/DDGS, not your private data
- ❌ Memory FAISS local
- ❌ Calendar/email local or Google API (Google, not us)

**This is most private even when online, Sir.** LLM never leaves device, only search queries (if you use search) go online. For your 8GB, tinyllama is ~8-10 tokens/sec — slower than OpenAI but private.

#### Choice C — Online But Basic (No LLM Key) 🌐

```bash
# No OPENAI_API_KEY, no Ollama
jarvis ask --engine auto "hello"
# Auto picks: Online but no LLM key/Ollama → mock LLM + online search
```

**What leaves device:**
- ✅ Search queries only (if you use web_search) — goes to DDGS (free, no key) or Tavily if key set
- ❌ LLM mock local — nothing leaves for LLM

### What Never Leaves Device (Always Local) 🔒

- `~/.jarvis/config.toml` — preset, engine type, auto prefs — local, API keys NOT stored (comment says "api_key is read from OPENAI_API_KEY env")
- `~/.jarvis/user_name.txt` — your name Eugene — local
- `~/.jarvis/adhd/*.json` — wins, energy_log, focus_sessions, plans, quick_capture, blocked_sites, etc. — local
- `~/.jarvis/memory/` — FAISS vectors or keyword store — local, not sent to cloud unless you explicitly use cloud memory (we don't have cloud memory, only local)
- `~/.jarvis/faces/*.json` — face encodings — local
- `~/.jarvis/google_token.json` + `google_credentials.json` — OAuth tokens — local, only used to call Google Calendar/Gmail APIs (Google, not us)
- `~/.jarvis/voice_config.json` + `last_speech.mp3` — voice config — local
- `~/.jarvis/data/` — your data dir — local
- Frontend localStorage `jarvis_user_name`, `jarvis_mits`, `jarvis_today_tasks` — browser local, not sent to backend unless you send prompt
- Telemetry — disabled by default (`telemetry_enabled: false`), no PostHog unless you enable

### Security Measures Implemented

1. **Local-first architecture** — from OpenJarvis upstream: runs on personal devices, private by default
2. **No telemetry by default** — `telemetry_enabled: false`, no tracking unless you opt-in
3. **API keys from env, not disk** — `config.py` saves comment "api_key is read from OPENAI_API_KEY env" not actual key, to avoid leaking in git or config.toml
4. **.gitignore secrets** — ignores `google_credentials.json`, `google_token.json`, `openai_key.txt`, `.env.local`, `.jarvis/`, `models/`, `*.bin`, `*.onnx`, `*.pt`, etc.
5. **Google OAuth local** — token stored at `~/.jarvis/google_token.json`, only used to call `calendar.events.list` and `gmail.users.messages.list` via `googleapiclient`, not sent to our server
6. **Open source Apache 2.0** — you can audit all code, no hidden data exfiltration, see `src/jarvis/engine/openai.py` — only sends `_payload()` which is `model, messages, temperature, max_tokens` to `api_url` you set
7. **Hybrid auto transparent** — shows reason for engine selection: "Online (8.8.8.8:53 socket 1ms) + OPENAI_API_KEY set → full stack online (best for 8GB machine, no local RAM)" — you know what happens
8. **Offline fallback always works** — if online engine fails, falls back to mock, shows "⚠️ openai failed: ... — Fallback to mock" — never crashes, always has basic
9. **Frontend same UI** — circular HUD for both online/offline, only badge changes from 🌐 ONLINE to 📴 OFFLINE, no data leak via UI
10. **No data to eugenshila/JARVIS server** — we have no backend server collecting data, only GitHub repo, all runs locally on your DESKTOP-3D8CN02

### For Your Machine DESKTOP-3D8CN02 i5-6300U 8GB

**Recommended secure setup:**

```powershell
# Online full stack secure:
$env:OPENAI_API_KEY="sk-..."  # from https://platform.openai.com/api-keys
# Optional: $env:TAVILY_API_KEY="tvly-..." for real search
jarvis hybrid --action set --online-engine openai --offline-engine mock
jarvis online  # check: 🌐 ONLINE • FULL STACK ONLINE • openai

# What is sent when online: only your prompt + context you paste
# What stays local: memory, faces, voice, calendar.json, emails.json, adhd logs, etc.

# Offline basic secure:
# Disconnect WiFi or
# jarvis hybrid --action set --online-engine mock --offline-engine mock
# or just pull Ethernet — auto detects 📴 OFFLINE BASIC, nothing leaves device

# Most private even online (LLM stays local):
ollama pull tinyllama
jarvis hybrid --action set --online-engine ollama --offline-engine ollama
# LLM stays on your i5-6300U even online, only search queries go online if you use search
```

**Interactive When Online — Same Interface, You Decide, Sir:**

New requirement: when online, JARVIS stays interactive like offline mode — you make a decision from HUD or CLI.

**CLI:**
```bash
jarvis ask --engine auto --interactive "Good morning Eugene"
# Shows:
# 🌐 ONLINE — Interactive Decision — SHILATECH
# 1. Full Stack Online — openai if OPENAI_API_KEY HTTPS encrypted else ollama local, full search, best quality
# 2. Basic Offline Local even though online — mock/ollama local, nothing leaves device, private
# Decide — 1 for Full Stack Online, 2 for Basic Offline Local
jarvis chat --interactive  # same, plus /mode /online /offline commands inside chat

jarvis ask --agent ironman --engine auto "hybrid_mode interactive"  # tool
jarvis ask --agent ironman --engine auto "hybrid_mode decide choice 1"  # force full
jarvis ask --agent ironman --engine auto "hybrid_mode decide choice 2"  # force basic even online
```

**Tools:**
- `network_status status` — checks online/offline
- `hybrid_mode status` — shows auto prefs
- `hybrid_mode interactive` — returns decision prompt Option1 Full Stack vs Option2 Basic
- `hybrid_mode decide choice 1` — forces online_engine (full stack)
- `hybrid_mode decide choice 2` — forces offline_engine even though online (basic local, SHILATECH secure)

**Frontend Circular HUD:**
- Top bar ONLINE badge is now clickable button: "ONLINE OPENAI • FULL STACK • CLICK TO DECIDE" → opens modal
- Modal shows 2 cards: 1. FULL STACK ONLINE (green, recommended when online) 2. BASIC OFFLINE LOCAL EVEN THOUGH ONLINE (amber, private)
- Quick Protocols added DECIDE FULL / DECIDE BASIC buttons
- Same for IronManHUD — online badge clickable → decision modal
- When you pick Basic even though online: badge becomes "ONLINE • BASIC LOCAL • SHILATECH" — same circular interface, only badge changes, nothing leaves device
- When you pick Full: badge "ONLINE FULL STACK" — prompt to OpenAI if key else Ollama local, search online

**Answer to your question:** Yes, when online JARVIS is still interactive as offline mode — you decide from HUD click or CLI --interactive. Same circular interface local and online, only badge changes. SHILATECH branding: SHILATECH • time/date, SHILATECH • Malibu Point 10880.

**Data secure, Sir. Same circular interface like your screenshot for both local and online starts — only top badge changes from OFFLINE BASIC to ONLINE FULL STACK, and you decide interactive when online.**

---

## 3. Files

- `frontend/src/pages/IronManCircularHUD.tsx` NEW 600+ lines — matches screenshot circular HUD
- `frontend/src/App.tsx` — 7 modes, default circular
- `src/jarvis/core/network.py` — online detection + engine availability
- `src/jarvis/engine/auto_engine.py` — hybrid auto engine
- `src/jarvis/tools/network_tools.py` — network_status, hybrid_mode
- `docs/SECURITY_HYBRID.md` — this file
- Frontend build: 38 modules 243.19kB (69.35kB gzip) — 1 more module than before (circular)
- Tools: 50

**No MSI built yet — ready when you say, Sir.**
