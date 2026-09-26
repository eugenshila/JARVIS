# JARVIS — Personal AI, On Personal Devices

> **A complete rebuild inspired by [open-jarvis/OpenJarvis](https://github.com/open-jarvis/OpenJarvis)** — local-first modular assistant stack with MSI installer.

![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![MSI](https://img.shields.io/badge/Windows-MSI%20Installer-blue?logo=windows)

JARVIS is a framework for **local-first personal AI**, built around three core ideas from OpenJarvis:

1. **Shared primitives** for building on-device agents (engines, tools, memory, skills)
2. **Evaluations** that treat energy, latency, and cost as first-class constraints
3. **Learning loop** that improves from local trace data

Goal: agents run **locally by default**, calling cloud only when truly necessary.

---

## Architecture

```
jarvis/
├── core/          — config, types, paths (local-first, TOML-based)
├── engine/        — openai, ollama, mock, vllm, mlx, litellm, gemma_cpp
├── agents/        — simple, ReAct, orchestrator, morning_digest, deep_research, code_assistant
├── tools/         — file_read/write, shell, web_search (Tavily+DDGS hybrid), memory, calendar, gmail
├── memory/        — JSONL + FAISS vector store + BM25 + keyword fallback
├── skills/        — agentskills.io compatible loader + built-ins
├── server/        — FastAPI OpenAI-compatible API + /run agent endpoint
├── cli/           — Click CLI with rich UI + doctor
├── telemetry/     — latency, token, energy tracking
└── speech/        — placeholder for TTS/STT

frontend/          — React Vite chat UI (proxies to backend)
app.py             — Tkinter desktop app (enhanced, multi-agent)
deploy/windows/    — MSI builder (WiX) + PyInstaller spec + install.bat
deploy/linux/      — install.sh
docs/install/      — LAPTOP_SETUP.md (full laptop guide)
```

### Agents (from OpenJarvis)

| Agent | Type | What it does |
|-------|------|-------------|
| `simple` / `chat-simple` | On-demand | Single-turn chat, no tools |
| `native_react` | On-demand | ReAct loop with tool use |
| `orchestrator` | On-demand | Multi-turn reasoning, auto tool selection |
| `morning_digest` | Scheduled | Daily briefing from email/calendar/news (mock + connect) |
| `deep_research` | On-demand | Multi-hop research with citations |
| `code_assistant` | On-demand | File I/O, shell, code exec |

### Engines (new: vLLM, MLX, LiteLLM, Gemma)

| Engine | Best for | Requirements | Install |
|--------|----------|--------------|---------|
| **openai** | Cloud, easy | `OPENAI_API_KEY` | `pip install -e .` |
| **ollama** | Local, free, private | Ollama app | `pip install -e .` + https://ollama.com |
| **mock** | Offline demo | None | Always works |
| **vllm** | High-perf NVIDIA GPU | CUDA, Linux/WSL, 8GB VRAM | `pip install -e .[inference-vllm]` |
| **mlx** | Apple Silicon Mac | M1/M2/M3, macOS 13+ | `pip install -e .[inference-mlx]` |
| **litellm** | 100+ providers (Claude, Gemini, Bedrock) | API keys | `pip install -e .[inference-litellm]` |
| **gemma_cpp** | Ultra-light CPU | Low RAM | `pip install pygemma` |

### Memory (new: FAISS vector)

- **Keyword** (default): always works, no deps
- **BM25**: better ranking, `pip install -e .[memory-bm25]`
- **FAISS + SentenceTransformers**: semantic search, understands meaning
  - `pip install -e .[memory]` (~500 MB model)
  - Auto fallback: vector → BM25 → keyword
  - Stats: `curl http://localhost:8000/memory/stats`

### Web Search (new: real search)

- **Mock** (default): guidance only
- **DDGS** (free, no key): DuckDuckGo, `pip install -e .[tools-search]`
- **Tavily** (better, needs key): https://tavily.com (1000 free/month), set `TAVILY_API_KEY`
- Hybrid tool auto picks: Tavily → DDGS → Mock

---

## Installation — Laptop Setup

**Full guide:** [`docs/install/LAPTOP_SETUP.md`](docs/install/LAPTOP_SETUP.md) — step-by-step for Windows/macOS/Linux, what to download, troubleshooting.

### Quick (2 min, offline demo)

**Windows:**
```powershell
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
python -m pip install -e .[all] --break-system-packages
python -m jarvis.cli.main doctor
python -m jarvis.cli.main ask "hello" --mock
```

**macOS/Linux:**
```bash
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[all]
jarvis doctor
jarvis ask "hello" --mock
```

### With Real AI

**Option A: Cloud (easiest)**
```bash
export OPENAI_API_KEY=sk-...
jarvis chat
```

**Option B: Local Ollama (free, private, recommended)**
```bash
# Install from https://ollama.com/download
ollama pull llama3.2:3b   # 2GB, fast
jarvis chat --engine ollama
```

**Option C: Apple Silicon Mac (fastest on Mac)**
```bash
pip install -e .[inference-mlx]
JARVIS_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit jarvis chat --engine mlx
```

**Option D: NVIDIA GPU (fastest on Linux/WSL)**
```bash
pip install -e .[inference-vllm]
JARVIS_MODEL=meta-llama/Meta-Llama-3-8B-Instruct jarvis chat --engine vllm
```

### Windows MSI Installer

**Build MSI on Windows:**
```powershell
# Prerequisites: Python 3.11 + WiX Toolset v3.11 from https://wixtoolset.org/releases/
.\deploy\windows\build_msi.ps1 -Version 0.1.0
# Output: dist/JARVIS-0.1.0-x64.msi + portable ZIP
```

**Install MSI:**
1. Double-click `JARVIS-0.1.0-x64.msi`
2. Installs to `C:\Program Files\JARVIS\`, adds to PATH, Start Menu shortcut
3. Open new PowerShell: `jarvis doctor`

**Or portable (no admin):**
- Unzip `JARVIS-0.1.0-portable.zip` and add folder to PATH

**Or simple batch installer:**
```cmd
deploy\windows\install.bat  # double-click
```

**Automated via GitHub Actions:**
- Push tag `v0.1.0` → workflow builds MSI+EXE+ZIP and creates Release
- See `.github/workflows/build-msi.yml`

### What to download for your laptop

| Need | Download | Size | Where |
|------|----------|------|-------|
| **Always** | Python 3.11 | ~50 MB | https://www.python.org/downloads/ |
| **Always** | JARVIS code | ~5 MB | `git clone` or ZIP |
| **For cloud AI** | Nothing (just API key) | 0 | https://platform.openai.com/api-keys |
| **For local free AI** | Ollama | ~500 MB + 2-8 GB models | https://ollama.com/download |
| **For semantic memory** | FAISS deps | ~500 MB model | `pip install -e .[memory]` |
| **For real web search** | Tavily key (optional) | 0 | https://tavily.com (free 1000/mo) |
| **For MSI build** | WiX Toolset v3.11 | ~50 MB | https://wixtoolset.org/releases/ |

Full table in [`docs/install/LAPTOP_SETUP.md`](docs/install/LAPTOP_SETUP.md).

---

## Quick Start

### 1. Doctor check

```bash
jarvis doctor   # now shows FAISS, Tavily, GPU, MLX status
```

### 2. Init preset

```bash
jarvis init --list
jarvis init chat-simple --force
```

### 3. Chat (offline mock)

```bash
jarvis ask "Hello, what can you do?" --mock
jarvis ask "Build a meeting brief from Q4 planning" --mock --agent morning_digest
```

### 4. Chat (real inference)

```bash
# OpenAI
export OPENAI_API_KEY=sk-...
jarvis chat

# Ollama local
ollama serve
ollama pull llama3.1
jarvis chat --engine ollama

# vLLM (NVIDIA)
pip install -e .[inference-vllm]
jarvis chat --engine vllm

# MLX (Mac)
pip install -e .[inference-mlx]
JARVIS_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit jarvis chat --engine mlx

# LiteLLM (Claude, Gemini, etc)
pip install -e .[inference-litellm]
export ANTHROPIC_API_KEY=...
jarvis chat --engine litellm
JARVIS_MODEL=claude-3-5-sonnet-20241022 jarvis ask "Hello"
```

### 5. Server + Web UI

```bash
# Terminal 1: backend
jarvis serve --host 0.0.0.0 --port 8000

# Terminal 2: frontend
cd frontend && npm install && npm run dev
# Open http://localhost:5173
```

API docs: http://localhost:8000/docs

### 6. Desktop GUI

```bash
python app.py
# or
jarvis-desktop
```

Now with engine dropdown: mock, openai, ollama, vllm, mlx, litellm, gemma_cpp.

### 7. Memory with FAISS

```bash
pip install -e .[memory]   # FAISS + sentence-transformers
jarvis remember "User prefers concise briefs under 200 words"
jarvis memory "brief preferences"   # semantic search, not just keyword
curl http://localhost:8000/memory/stats  # check FAISS status
```

### 8. Real web search

```bash
pip install -e .[tools-search]
# Free (no key): uses DuckDuckGo
jarvis ask "Search latest AI news" --agent deep_research

# Better: Tavily
export TAVILY_API_KEY=tvly-...
jarvis ask "What is Intelligence Per Watt?" --agent deep_research
```

### 9. Skills

```bash
jarvis skill --list
jarvis ask "Use code-explainer skill to explain: for i in range(5): print(i*2)" --mock
```

---

## Configuration

Config lives at `~/.jarvis/config.toml` (override via `JARVIS_HOME`).

```toml
preset = "chat-simple"

[engine]
type = "openai"  # openai, ollama, mock, vllm, mlx, litellm, gemma_cpp
model = "gpt-4o-mini"
api_url = "https://api.openai.com/v1/chat/completions"
temperature = 0.7
max_tokens = 2048

[telemetry]
enabled = false
```

Env overrides:

- `OPENAI_API_KEY` — OpenAI
- `ANTHROPIC_API_KEY` — Claude via LiteLLM
- `TAVILY_API_KEY` — Real web search
- `JARVIS_API_URL` — custom endpoint
- `JARVIS_MODEL` — model override
- `JARVIS_HOME` — config home
- `JARVIS_MOCK=1` — force mock

---

## API

OpenAI-compatible + extensions:

```
GET  /health
GET  /v1/models
POST /v1/chat/completions   (supports stream)
POST /run                   {prompt, context, agent, engine}
GET  /agents
GET  /engines                (now: openai, ollama, mock, vllm, mlx, litellm, gemma_cpp)
GET  /skills
GET  /memory
GET  /memory/stats           (new: FAISS status)
POST /memory
GET  /telemetry
```

---

## Comparison to OpenJarvis

| Feature | OpenJarvis | This JARVIS |
|---------|------------|-------------|
| Engine abstraction | ✅ full (mlx, vllm, afm, etc) | ✅ openai, ollama, mock, vllm, mlx, litellm, gemma_cpp |
| Agents | 8 built-ins | 6 built-ins (same patterns) |
| Tools | 20+ | 8 core + Tavily/DDGS hybrid |
| Memory | FAISS, ColBERT, BM25 | FAISS + BM25 + keyword auto fallback |
| Skills | Hermes, OpenClaw, agentskills.io | Built-ins + markdown loader |
| Server | FastAPI + Rust ext | FastAPI |
| Frontend | React + Tauri desktop | React Vite + Tkinter |
| CLI | Click, rich | Click, rich + enhanced doctor |
| Telemetry | Energy, FLOPs, cost | Latency, tokens (energy hook) |
| Local-first | ✅ | ✅ |
| Installer | Shell scripts | Shell + PowerShell + MSI (WiX) + GitHub Actions |

---

## Development

```bash
pip install -e .[dev]
pytest
ruff check src
```

Build MSI (Windows):

```powershell
.\deploy\windows\build_msi.ps1 -Version 0.1.0
```

---

## License

Apache 2.0 — same as OpenJarvis.

---

## Roadmap

- [x] Add vLLM / MLX / LiteLLM / Gemma engines
- [x] FAISS vector memory + BM25
- [x] Real web search (Tavily/DDGS)
- [x] Windows MSI installer + portable ZIP
- [x] Full laptop setup guide
- [ ] Tauri desktop bundle
- [ ] Rust extension for perf
- [ ] Eval harness with energy tracking
- [ ] Skill sync from Hermes/OpenClaw
- [ ] Voice I/O (Whisper + Kokoro)
