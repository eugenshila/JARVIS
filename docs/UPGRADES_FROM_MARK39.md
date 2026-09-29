# What we can borrow from FatihMakes/Mark-XXXIX-OR

Reference: https://github.com/FatihMakes/Mark-XXXIX-OR (~11.6k LOC Python, single-user
desktop assistant: `main.py`, `ui.py`, `or_client.py`, `actions/`, `agent/`, `memory/`).

**Licensing caveat:** that repo ships **no LICENSE file**, so it is "all rights reserved".
Do not copy source. Re-implement the *ideas* below in our own code (our repo is Apache-2.0).

## Architecture comparison

| Area | Mark XXXIX-OR | Our JARVIS | Verdict |
|---|---|---|---|
| Engines | OpenRouter only, hardcoded free-model list | ollama / openai / litellm / vllm / mlx / gemma + auto | we're ahead |
| Packaging | `setup.py`, loose top-level modules | `src/` layout, hatchling, MSI, CLI entrypoints | we're ahead |
| Memory | flat JSON w/ categories + char budget + trimming | FAISS + BM25 vector store | we're ahead on recall, behind on *structure* |
| Planning | dedicated planner → task queue → executor → error handler | single ReAct loop (60 lines) | **they're ahead** |
| Vision | screen capture + webcam, Gemini live audio | `vision_tool.py` only | **they're ahead** |
| Files | 832-line universal file processor (pdf/docx/csv/xlsx/code/audio/video/zip) | none | **they're ahead** |
| Desktop control | pyautogui/pygetwindow/pycaw, app launch, settings, browser via Playwright | `app_launcher` allow-list | they're broader, we're safer |

## Worth stealing (priority order)

### 1. Model fallback chain (`or_client.py`)
They keep an ordered list of models and walk down it on 429/5xx/empty response.
Port this into `src/jarvis/engine/auto_engine.py` as a real *cascade*: try
ollama-local → openai → litellm, with per-provider cooldown after failure.
Cheap win, big reliability gain for offline/rate-limited users.

### 2. Planner / executor / error-handler split (`agent/`)
Their loop is: `planner.py` emits a ≤5-step JSON plan over a typed tool catalogue →
`task_queue.py` (priority queue, cancel flags, worker thread) → `executor.py` runs steps →
`error_handler.py` asks the LLM to classify a failure as `retry | skip | replan | abort`
with a max-retry count and a ≤15-word user message.

That last piece is the single best idea in the repo. Proposal for us:
- `src/jarvis/agents/planner.py` — plan JSON validated against our `tools/registry.py` specs
  (we can auto-generate the tool catalogue from specs instead of hand-writing the prompt as
  they do — their prompt drifts out of sync with the code).
- `src/jarvis/agents/recovery.py` — the retry/skip/replan/abort classifier.
- `src/jarvis/core/task_queue.py` — priority + cancellable background tasks, which also gives
  the HUD a real "JARVIS is working on 3 things" panel.

### 3. Universal file processor (`actions/file_processor.py`)
Type-detect by extension → dispatch to per-type verbs (image: describe/ocr/resize;
pdf: summarize/extract; csv/xlsx: analyze/stats; code: explain/review; media: trim/convert).
As `src/jarvis/tools/file_processor.py` this plugs straight into our tool registry and the
frontend gains drag-and-drop upload. Use local libs (pypdf, python-docx, pandas, ffmpeg)
with the LLM only for the summarize/describe verbs — unlike them we shouldn't hard-depend
on Gemini.

### 4. Screen + webcam awareness (`actions/screen_processor.py`)
`mss` screen grab → downscale to 640x360 JPEG q55 → send to a vision model. The downscale
budget is the practical detail worth copying. Extend our `vision_tool.py` with
`capture_screen()` / `capture_camera()` behind an explicit user-consent flag.

### 5. Structured long-term memory (`memory/memory_manager.py`)
Categories (`identity`, `preferences`, `projects`, `relationships`, `wishes`, `notes`),
per-value length cap, total char budget, oldest-entry eviction. Our vector store has no
such curated "always in the system prompt" layer. Add a small `profile.json` facts layer
in `memory/store.py` that is *always* injected, with the vector store used for recall.

### 6. Small ergonomics
- Cross-platform `get_base_dir()` that handles PyInstaller `sys.frozen` — we should audit
  `core/paths.py` for the frozen case before the next MSI build.
- Task cancellation via `threading.Event` on every long-running action.

## Not worth taking
- Hardcoded free-OpenRouter model list (rots within weeks; ours is config-driven).
- Single 1,534-line `ui.py` Tkinter UI — our React HUD is better.
- Windows-only deps (pycaw, pywinauto, win10toast) as hard requirements; keep ours optional.
- Plaintext `config/api_keys.json` — we already use env + TOML config, which is safer.

## Suggested first PR
Model cascade in `auto_engine.py` + `recovery.py` error classifier + a `plan` step in the
ReAct agent. ~400 LOC, no new hard dependencies, directly improves reliability.
