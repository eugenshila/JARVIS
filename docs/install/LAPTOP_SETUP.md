# JARVIS Laptop Setup Guide

Complete guide to get JARVIS running on your laptop (Windows, macOS, Linux).

---

## TL;DR Quick Install (2 minutes)

### Windows
```powershell
# 1. Install Python 3.11 from https://www.python.org/downloads/ (check Add to PATH)
# 2. Open PowerShell and run:
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
python -m pip install -e .[all] --break-system-packages
python -m jarvis.cli.main doctor
python -m jarvis.cli.main ask "hello" --mock
```

### macOS / Linux
```bash
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[all]
jarvis doctor
jarvis ask "hello" --mock
```

That's it for offline demo. For real AI, continue below.

---

## 1. System Requirements

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| OS | Windows 10/11, macOS 12+, Ubuntu 20.04+ | Windows 11, macOS 14+, Ubuntu 22.04+ | 64-bit only |
| Python | 3.10 | 3.11 or 3.12 | 3.13 works, 3.14 not yet (numpy) |
| RAM | 4 GB | 16 GB+ | 8 GB for local models, 16+ for vLLM |
| Disk | 2 GB | 20 GB+ | Models: 2-8 GB each |
| GPU | None (CPU works) | NVIDIA 8GB+ VRAM for vLLM, Apple Silicon for MLX | Optional but faster |

---

## 2. What You Need to Download

### A. Always Required

1. **Python 3.10+**
   - Windows: https://www.python.org/downloads/ — download 3.11.9 64-bit installer
   - macOS: `brew install python@3.11` or from python.org
   - Linux: `sudo apt install python3.11 python3.11-venv python3-pip` (Ubuntu/Debian)
   - Verify: `python --version` or `python3 --version`

2. **Git** (to clone repo)
   - Windows: https://git-scm.com/download/win
   - macOS: `xcode-select --install` or `brew install git`
   - Linux: `sudo apt install git`
   - Or download ZIP from GitHub instead

3. **JARVIS code**
   ```bash
   git clone https://github.com/eugenshila/JARVIS
   cd JARVIS
   ```

### B. For Real AI (choose ONE)

#### Option 1: OpenAI / Cloud (easiest, no local GPU needed)
- **What**: Uses OpenAI API (or any OpenAI-compatible endpoint)
- **Download**: Nothing extra, just API key
- **Get key**: https://platform.openai.com/api-keys
- **Cost**: Pay per use (~$0.01-0.10 per chat)
- **Setup**:
  ```bash
  # Windows PowerShell
  $env:OPENAI_API_KEY="sk-..."
  # macOS/Linux
  export OPENAI_API_KEY=sk-...

  jarvis ask "Explain quantum computing"
  ```
- **Alternatives via LiteLLM**:
  - Anthropic Claude: `ANTHROPIC_API_KEY`
  - Google Gemini: `GOOGLE_API_KEY`
  - Use: `jarvis ask --engine litellm` with model `claude-3-5-sonnet` or `gemini/gemini-1.5-pro`

#### Option 2: Ollama (recommended for local, free, private)
- **What**: Runs Llama, Mistral, etc locally
- **Download**: https://ollama.com/download
  - Windows: `OllamaSetup.exe` (~500 MB)
  - macOS: `Ollama-darwin.zip`
  - Linux: `curl -fsSL https://ollama.com/install.sh | sh`
- **Setup**:
  ```bash
  # After install, Ollama runs automatically
  ollama pull llama3.1   # 4.7 GB, best general
  ollama pull llama3.2:3b # 2 GB, smaller/faster
  ollama pull mistral    # 4 GB

  # Test
  ollama run llama3.1 "Hello"

  # Use with JARVIS
  jarvis chat --engine ollama
  jarvis ask "Summarize this code" --engine ollama
  ```
- **Models to try**:
  - `llama3.1` (8B, good balance)
  - `llama3.2:3b` (small, fast, laptop friendly)
  - `codellama` (for code)
  - `mistral` (fast)
  - See all: https://ollama.com/library

#### Option 3: vLLM (high-performance, NVIDIA GPU, Linux/WSL)
- **What**: Fastest local inference, for NVIDIA GPUs
- **Requirements**: NVIDIA GPU 8GB+, CUDA 12+, Linux or WSL2
- **Download**: No separate download, pip package
- **Setup**:
  ```bash
  pip install -e .[inference-vllm]
  # Model auto-downloads on first run (HF cache)
  jarvis ask "Hello" --engine vllm
  # Set model
  JARVIS_MODEL=meta-llama/Meta-Llama-3-8B-Instruct jarvis chat --engine vllm
  ```
- **Models**: `meta-llama/Meta-Llama-3-8B-Instruct`, `mistralai/Mistral-7B-Instruct-v0.2`

#### Option 4: MLX (Apple Silicon Mac, fastest on Mac)
- **What**: Native Apple Silicon inference, uses Neural Engine
- **Requirements**: Mac with M1/M2/M3/M4, macOS 13+
- **Download**: pip package
- **Setup**:
  ```bash
  pip install -e .[inference-mlx]
  # Model: mlx-community/Llama-3.2-3B-Instruct-4bit (quantized, small)
  JARVIS_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit jarvis chat --engine mlx
  ```

#### Option 5: Mock (offline demo, no download)
- **What**: No AI, shows architecture working
- **Use**: `jarvis ask "test" --mock` — always works, no key/GPU needed

### C. For Enhanced Features (optional but recommended)

#### FAISS + Sentence Transformers (semantic memory)
- **What**: Vector search for memory — understands meaning, not just keywords
- **Download**: pip packages (auto)
- **Install**:
  ```bash
  pip install -e .[memory]
  # Or all: pip install -e .[all]
  ```
- **Size**: ~500 MB for model `all-MiniLM-L6-v2`
- **Benefit**: `jarvis memory "brief preferences"` finds relevant even without exact words
- **Verify**:
  ```bash
  jarvis memory --help
  # Should show FAISS available if installed
  ```

#### Real Web Search (Tavily + DuckDuckGo)
- **What**: Agents can search real web, not mock
- **Free option (no key)**: DuckDuckGo via `ddgs`
  ```bash
  pip install -e .[tools-search]
  jarvis ask "Search latest AI news" --agent deep_research
  ```
- **Better quality (needs API key)**: Tavily
  - Get key: https://tavily.com (free tier 1000 searches/month)
  - Setup:
    ```bash
    # Windows
    $env:TAVILY_API_KEY="tvly-..."
    # macOS/Linux
    export TAVILY_API_KEY=tvly-...

    pip install tavily-python
    jarvis ask "What is Intelligence Per Watt?" --agent deep_research
    ```

#### Voice (STT + TTS)
- **What**: Speak to JARVIS, hear responses
- **Install**:
  ```bash
  pip install -e .[voice]
  # Also needs: brew install espeak-ng (macOS) or apt install espeak-ng (Linux)
  ```
- **Use**: `jarvis chat` with voice flag (coming soon)

---

## 3. Installation Steps by Platform

### Windows 10/11 (full guide)

**Step 1: Install Python**
- Go to https://www.python.org/downloads/
- Download **Python 3.11.9** (Windows installer 64-bit)
- Run installer, **check**: ✅ Add python.exe to PATH, ✅ Install pip
- Open PowerShell, verify: `python --version` → `Python 3.11.x`

**Step 2: Install Git (optional)**
- https://git-scm.com/download/win → 64-bit setup, default options
- Or skip and download ZIP from GitHub: https://github.com/eugenshila/JARVIS → Code → Download ZIP

**Step 3: Get JARVIS**
```powershell
# If git installed
git clone https://github.com/eugenshila/JARVIS
cd JARVIS

# If ZIP downloaded
Expand-Archive JARVIS-main.zip -DestinationPath .
cd JARVIS-main
```

**Step 4: Install JARVIS**
```powershell
# Create venv (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# If error about execution policy:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Install
python -m pip install --upgrade pip
python -m pip install -e .[all]

# If you get externally-managed-environment error (Python 3.11+ from Microsoft Store):
python -m pip install -e .[all] --break-system-packages
```

**Step 5: Verify**
```powershell
jarvis doctor
jarvis ask "Hello, what can you do?" --mock
python app.py  # Desktop GUI
```

**Step 6: Add real AI (choose one)**
```powershell
# Option A: OpenAI
$env:OPENAI_API_KEY="sk-..."
jarvis chat

# Option B: Ollama (local, free)
# Download OllamaSetup.exe from https://ollama.com/download and install
ollama pull llama3.2:3b
jarvis chat --engine ollama
```

**Step 7: (Optional) Build MSI**
```powershell
# Install WiX Toolset from https://wixtoolset.org/releases/
# Then:
.\deploy\windows\build_msi.ps1 -Version 0.1.0
# Output: dist/JARVIS-0.1.0-x64.msi
```

### macOS (Intel or Apple Silicon)

```bash
# 1. Install brew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install Python + Git
brew install python@3.11 git

# 3. Clone and install
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[all]

# 4. Verify
jarvis doctor
jarvis ask "hello" --mock

# 5. Real AI
# OpenAI
export OPENAI_API_KEY=sk-...
jarvis chat

# Or Ollama (recommended for local)
brew install ollama
ollama serve &
ollama pull llama3.2:3b
jarvis chat --engine ollama

# Or MLX (Apple Silicon only, fastest)
pip install -e .[inference-mlx]
JARVIS_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit jarvis chat --engine mlx

# Desktop GUI (needs Tkinter, usually included)
python app.py
# If Tkinter missing: brew install python-tk@3.11
```

### Linux (Ubuntu/Debian)

```bash
# 1. System deps
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip git python3-tk -y

# 2. Clone
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[all]

# 3. Verify
jarvis doctor
jarvis ask "hello" --mock

# 4. Ollama local
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
jarvis chat --engine ollama

# 5. vLLM if NVIDIA GPU
# Install CUDA first from https://developer.nvidia.com/cuda-downloads
pip install -e .[inference-vllm]
JARVIS_MODEL=meta-llama/Meta-Llama-3-8B-Instruct jarvis chat --engine vllm

# Server + Web UI
jarvis serve --host 0.0.0.0 --port 8000 &
cd frontend && npm install && npm run dev
# Open http://localhost:5173
```

---

## 4. What Gets Installed Where

| What | Location | Size |
|------|----------|------|
| JARVIS config | `~/.jarvis/config.toml` (Windows: `C:\Users\You\.jarvis\`) | <1 KB |
| Memory | `~/.jarvis/memory/memories.jsonl` + `faiss.index` | MBs, grows with use |
| Telemetry | `~/.jarvis/telemetry/telemetry.jsonl` | MBs |
| Skills | `~/.jarvis/skills/*.md` | KBs |
| Python venv | `JARVIS/.venv/` | ~500 MB base, +2 GB with all extras |
| Ollama models | `~/.ollama/models/` (Windows: `C:\Users\You\.ollama\`) | 2-8 GB per model |
| HuggingFace cache (vLLM/MLX) | `~/.cache/huggingface/` | 4-15 GB per model |
| Frontend node_modules | `frontend/node_modules/` | ~200 MB |

**To reset:**
```bash
rm -rf ~/.jarvis  # Clears config, memory, etc
ollama rm llama3.2:3b  # Remove model
```

---

## 5. Using JARVIS After Install

### CLI

```bash
jarvis --help
jarvis doctor              # Check health
jarvis init --list         # List presets
jarvis init chat-simple --force
jarvis ask "Explain this code: ..." --mock
jarvis chat                # Interactive chat
jarvis chat --engine ollama --agent code_assistant
jarvis memory "search query"
jarvis remember "User likes concise answers"
jarvis skill --list
jarvis digest --fresh      # Morning briefing
jarvis serve --port 8000   # API server
```

### Desktop GUI

```bash
python app.py
# Features:
# - Agent selector (simple, react, orchestrator, etc)
# - Engine selector (openai, ollama, mock, vllm, mlx)
# - Prompt library
# - Context pane
# - Memory save
# - Doctor, Server buttons
```

### Web UI

```bash
# Terminal 1
jarvis serve

# Terminal 2
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### API

```bash
curl http://localhost:8000/health
curl http://localhost:8000/agents
curl -X POST http://localhost:8000/run -H "Content-Type: application/json" -d '{"prompt":"Hello","agent":"simple","engine":"mock"}'
# Docs: http://localhost:8000/docs
```

---

## 6. Troubleshooting

**`jarvis` command not found:**
```bash
# Use full path
python -m jarvis.cli.main --help
# Or activate venv
source .venv/bin/activate  # macOS/Linux
.\.venv\Scripts\Activate.ps1  # Windows
# Or add to PATH
pip install -e . --break-system-packages
```

**`OPENAI_API_KEY not set`:**
- Set env var, or use `--mock` or `--engine ollama`

**Ollama not reachable:**
- Ensure `ollama serve` running (check system tray on Windows)
- `curl http://localhost:11434` should respond

**FAISS install fails on Windows:**
```bash
pip install faiss-cpu --no-cache-dir
# If fails, skip: pip install -e . without [memory], keyword search still works
```

**vLLM fails on Windows:**
- vLLM doesn't support native Windows — use WSL2
- `wsl --install` then install inside WSL

**MLX fails on non-Mac:**
- MLX only works on Apple Silicon Macs — use Ollama or vLLM instead

**Tkinter missing (app.py fails):**
- Windows: Should be included with python.org installer
- macOS: `brew install python-tk@3.11`
- Linux: `sudo apt install python3-tk`

**Port already in use:**
```bash
jarvis serve --port 8001
# Or kill
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

---

## 7. Recommended Laptop Setup (Balanced)

For most users (Windows laptop, 8GB RAM, no GPU):

1. Python 3.11 + JARVIS `pip install -e .[all]`
2. Ollama + `llama3.2:3b` (2GB, fast, private)
3. FAISS memory (`pip install -e .[memory]`) for semantic search
4. Tavily free key for web search (optional)

Total download: ~3 GB, works offline after.

For power user (16GB RAM, NVIDIA GPU):

1. Same as above
2. Plus vLLM + Llama-3-8B (faster than Ollama with GPU)
3. All extras

For MacBook M1/M2/M3:

1. Python 3.11 + JARVIS
2. MLX + `mlx-community/Llama-3.2-3B-Instruct-4bit` (super fast, low RAM)
3. FAISS + Tavily

---

## 8. Uninstall

```bash
# Remove JARVIS
pip uninstall jarvis -y
rm -rf ~/.jarvis
rm -rf JARVIS/

# Remove Ollama models (optional)
ollama rm llama3.2:3b
# Uninstall Ollama app via Control Panel / Applications

# Remove Python venv
rm -rf .venv
```

MSI: Control Panel → Add/Remove Programs → JARVIS → Uninstall.

---

## Need Help?

- GitHub Issues: https://github.com/eugenshila/JARVIS/issues
- OpenJarvis Docs: https://open-jarvis.github.io/OpenJarvis/
- Discord: https://discord.gg/CMVBmDQ5Fj (OpenJarvis community)

Happy building! 🚀
