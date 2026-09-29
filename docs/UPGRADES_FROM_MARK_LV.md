# What we can borrow from FatihMakes/Mark-LV (Mark 55)

Reference: https://github.com/FatihMakes/Mark-LV — ~25.8k LOC Python, 52 commits,
last pushed 2 days ago. This is a much more mature codebase than Mark-XXXIX-OR
(11.6k LOC): it adds `core/` infrastructure (model ladder, plugin/action loaders,
undo, confirm, echo cancellation, wake word, TTS/STT/viseme/avatar), a FastAPI
remote `dashboard/`, and a proactive/background-monitor layer.

**Licensing caveat (different from Mark 39!):** Mark-LV ships a LICENSE —
**CC BY-NC 4.0, commercial use not permitted**. That is *worse* for us than no
license in one respect: it is explicit and it is NonCommercial, and CC-BY-NC is
incompatible with our Apache-2.0. So again: **do not copy source or vendor files.**
Re-implement the designs below independently. If we ever want actual code, we'd
need written permission from the author.

---

## The four ideas worth taking

### 1. A single model ladder with timeouts and cooldowns (`core/gemini.py`)
This is the headline of the release and it maps exactly onto the weakness I
flagged in `UPGRADES_FROM_MARK39.md`.

Their problem: 16 files each constructed their own client with an inline model
name and **no timeout**, so a sick model alias hung requests forever. Their fix:

- One module owns all one-shot model calls.
- Named ladders by *purpose*, not by model — `FAST` (classification/extraction),
  `SMART` (reasoning/long docs/images), `SEARCH` (grounded). Each is an ordered
  list of rungs.
- Every call has a timeout; on 429/504/timeout, fall to the next rung and put
  the failed one on a **cooldown** so the next call doesn't pay the same cost.
- Ordering is by *measured* latency and by *which quota pool* each rung draws
  from, not by guesswork.

For us: `src/jarvis/engine/auto_engine.py` currently only switches
online/offline and caches the choice for 30s — it has no per-call timeout, no
failure cooldown, and no purpose-based routing. Proposal:

- `src/jarvis/engine/ladder.py` — `FAST` / `SMART` / `SEARCH` ladders defined in
  `config.toml`, each rung `(engine, model, timeout_s)`.
- A `_cooldown: dict[rung, expiry]` so a rung that 429s is skipped for N seconds.
- Agents ask for a *purpose* (`engine.for_purpose("fast")`), not a model name.
  Cheap classification stops burning gpt-4o.

This supersedes the simpler "cascade" idea from the Mark 39 writeup — take this
version instead.

### 2. Auto-discovered tools with declared blocking behaviour (`core/action_loader.py`, `core/plugin_loader.py`)
Two loaders sharing one contract: a module drops a `TOOL` / `PLUGIN` dict
(name, description, JSON-schema parameters, handler) into a folder and is picked
up at startup. Handlers are called by **signature introspection**, so each one
declares only the context it wants (`player`, `speak`, `session_memory`).
Import errors, schema errors and name collisions are logged and the file is
skipped — discovery never raises.

Two details worth copying verbatim as *design*:
- **Enable/disable state is re-read from config on every dispatch**, so toggling
  a tool needs no restart.
- Each tool can declare `behavior: BLOCKING|NON_BLOCKING` and
  `scheduling: WHEN_IDLE|SILENT|INTERRUPT` — i.e. a slow tool says so, the model
  keeps talking, and the result is re-injected either at the next pause,
  silently, or as an interruption.

For us: `src/jarvis/tools/registry.py` is a hand-maintained import list with
`try/except ImportError` blocks — every new tool means editing the registry.
Replace with directory discovery over `src/jarvis/tools/`, plus the
behavior/scheduling fields, which our HUD needs anyway for long-running tools.

### 3. Undo stack + an unforgeable confirmation gate (`core/undo.py`, `core/confirm.py`)
The best safety thinking in the repo, and we have **neither**.

- **`undo.py`**: a bounded (depth 10) thread-safe stack. An action does the thing
  immediately and pushes `(human label, zero-arg reverse callable)`. "Undo" is a
  tool the model can call. Rationale: confirming everything trains users to stop
  using the assistant; act fast and be reversible instead.
- **`confirm.py`**: the key insight — the old pattern of a `confirmed=yes` tool
  *parameter* is not a gate at all, because **the model writes that parameter**.
  Instead the token is issued by the *interface*: the action registers a pending
  callable, the UI shows CONFIRM/CANCEL, and only a real UI click resolves it.
  Non-blocking (the model keeps talking), 90s timeout, and reserved strictly for
  *irreversible* things — everything reversible goes to `undo` instead.

For us: several of our tools (`app_launcher`, `business_tools`, shell) use
exactly the forgeable `confirm` parameter pattern. Add `core/undo.py` and
`core/confirm.py`, wire CONFIRM/CANCEL into the React HUD, and make
`ShellTool` / file-write / device tools go through them.

### 4. The remote dashboard (`dashboard/server.py`, 884 lines)
FastAPI on :8000 with a login page, session-key-derived AES-256-CBC at the
application layer (plain HTTP, no self-signed-cert warnings), websocket
transcript, and file upload capped at 500 MB into a cross-platform
`~/Downloads/JARVIS Uploads` folder.

We already have `server/api.py` + a React frontend, so we don't need their UI —
but we have **no auth at all** on the API. The upload-dir fallback chain and the
"auth at the app layer so you can stay on plain HTTP on a LAN" trade-off are both
directly reusable ideas. (I'd still prefer a token + loopback binding over
hand-rolled CryptoJS AES.)

---

## Worth a look, lower priority

- **`core/echo.py`** — barge-in / echo-tail suppression without a tuned level
  threshold: it subtracts recent *output* band-energies from the mic block, so
  our own voice cancels while a second speaker survives, plus a self-calibrating
  echo-gain estimate. If we ever do always-on voice, this is the hard part solved.
- **`core/wake_word.py`** — openwakeword "hey jarvis" with two disciplines worth
  keeping: import the dep *only* inside `start()` so the feature costs nothing
  when off, and the mic callback only does a non-blocking queue push with
  inference on a separate thread. We have a `wakeword_tool.py`; worth auditing
  against that pattern.
- **`llm_client.py` warmup** — warm the model with the *static* part of the
  system prompt so Ollama's KV prefix cache is primed; they measure first-token
  latency dropping from ~17s to <1s. Trivial to add to our `engine/ollama.py`,
  meaningful on low-spec hardware.
- **`actions/proactive.py`** — silence gate (15 min) + cooldown (20 min) +
  rotating context focus so unprompted messages don't repeat. Pairs well with
  our `startup/morning_brief.py`.
- **`actions/background_monitor.py`** — user-declared topic watches, daily check,
  headline-hash dedupe, with a hardcoded blocklist (crypto/finance) so it never
  becomes an uninvited tracker. Good taste.
- **`core/audio_devices.py` / `tts.py` / `viseme.py` / `avatar.py`** — a talking
  3D face with viseme lip-sync. Impressive, off our roadmap.

## Not worth taking
- `ui.py` — **5,848 lines** in one file (up from 1,534 in Mark 39). Our React HUD
  is the better answer; this is the clearest sign their architecture doesn't scale.
- `main.py` — 2,321 lines of orchestration.
- Gemini-Live-first architecture: clever quota arbitrage (Live API draws from a
  different pool than the text API, so leading with it preserves the text quota),
  but it hard-binds the whole app to one vendor. We're multi-engine; keep that.
- Plaintext `config/api_keys.json` — still there, still worse than our env+TOML.

---

## Revised first PR (replaces the Mark 39 proposal)
1. `engine/ladder.py` — purpose-named ladders, per-rung timeout, failure cooldown.
2. `core/undo.py` + `core/confirm.py` — and move `ShellTool`/file-write/app-launch
   off the forgeable `confirmed=` parameter.
3. Directory-based tool discovery to replace the hand-maintained
   `tools/registry.py` import list.

~600–700 LOC, no new hard dependencies, all independently written.
