# JARVIS Installation — Quick Reference

> **Full laptop guide:** [`docs/install/LAPTOP_SETUP.md`](docs/install/LAPTOP_SETUP.md)  
> **MSI build guide:** [`docs/install/WINDOWS_MSI_GUIDE.md`](docs/install/WINDOWS_MSI_GUIDE.md)

## For Laptop Users (You want to USE JARVIS)

### Windows — Easiest (MSI)

1. **Download MSI** from GitHub Releases: `JARVIS-0.1.0-x64.msi` (once we publish a release)
2. **Double-click MSI**, follow wizard (installs to `C:\Program Files\JARVIS\`)
3. **Open new PowerShell**:
   ```powershell
   jarvis doctor
   jarvis ask "hello" --mock
   ```

**Don't have MSI yet? Build it:**

```powershell
# Install Python 3.11 from https://www.python.org/downloads/ (check Add to PATH)
# Install WiX Toolset v3.11 from https://wixtoolset.org/releases/
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
.\deploy\windows\build_msi.ps1 -Version 0.1.0
# Output: dist/JARVIS-0.1.0-x64.msi
```

**Or portable (no admin):**
```powershell
# After building, unzip
Expand-Archive dist\JARVIS-0.1.0-portable.zip -DestinationPath C:\Tools\JARVIS
$env:PATH += ";C:\Tools\JARVIS\jarvis"
```

**Or pip (dev):**
```powershell
python -m pip install -e .[all] --break-system-packages
jarvis doctor
```

### macOS

```bash
brew install python@3.11 git
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[all]
jarvis doctor
jarvis ask "hello" --mock
```

### Linux (Ubuntu)

```bash
sudo apt install python3.11 python3.11-venv python3-pip git python3-tk -y
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
python3 -m venv .venv && source .venv/bin/activate
pip install -e .[all]
jarvis doctor
```

---

## For Real AI (choose one)

### 1. Mock (offline, no download) — always works
```bash
jarvis ask "hello" --mock
```

### 2. OpenAI Cloud (easiest, needs API key, costs money)
```bash
export OPENAI_API_KEY=sk-...   # Windows: $env:OPENAI_API_KEY="sk-..."
jarvis chat
```

### 3. Ollama Local (free, private, recommended)
- **Download**: https://ollama.com/download (500 MB)
- **Setup**:
  ```bash
  ollama pull llama3.2:3b   # 2GB, fast
  jarvis chat --engine ollama
  ```

### 4. vLLM (NVIDIA GPU, Linux/WSL, fastest with GPU)
```bash
pip install -e .[inference-vllm]
JARVIS_MODEL=meta-llama/Meta-Llama-3-8B-Instruct jarvis chat --engine vllm
```

### 5. MLX (Apple Silicon Mac, fastest on Mac)
```bash
pip install -e .[inference-mlx]
JARVIS_MODEL=mlx-community/Llama-3.2-3B-Instruct-4bit jarvis chat --engine mlx
```

### 6. LiteLLM (Claude, Gemini, Bedrock, 100+ providers)
```bash
pip install -e .[inference-litellm]
export ANTHROPIC_API_KEY=...
JARVIS_MODEL=claude-3-5-sonnet-20241022 jarvis chat --engine litellm
```

---

## Optional Enhancements

### Semantic Memory (FAISS)
```bash
pip install -e .[memory]   # 500 MB model, understands meaning
jarvis remember "User likes concise"
jarvis memory "concise"
```

### Real Web Search
```bash
pip install -e .[tools-search]   # Free: DuckDuckGo, no key needed
export TAVILY_API_KEY=tvly-...   # Better: https://tavily.com (1000 free/mo)
jarvis ask "Latest AI news" --agent deep_research
```

---

## What to Download — Summary

| What | Where | Size | When needed |
|------|-------|------|-------------|
| Python 3.11 | python.org | 50 MB | Always (unless MSI) |
| JARVIS code | git clone | 5 MB | Always (unless MSI) |
| Ollama | ollama.com | 500 MB + 2-8 GB models | For free local AI |
| OpenAI key | platform.openai.com | 0 | For cloud AI |
| FAISS deps | pip install -e .[memory] | 500 MB | For semantic memory |
| Tavily key | tavily.com | 0 | For better web search |
| WiX Toolset | wixtoolset.org | 50 MB | Only to BUILD MSI |

**Total for typical laptop (Ollama + FAISS): ~3-4 GB, works offline after.**

---

## Verify Install

```bash
jarvis doctor   # Shows engines, FAISS, search, GPU, MLX status
jarvis init --list
jarvis ask "What can you do?" --mock
python app.py   # Desktop GUI
jarvis serve & cd frontend && npm install && npm run dev  # Web UI at http://localhost:5173
```

---

## Need Help?

- Full guide: `docs/install/LAPTOP_SETUP.md`
- MSI guide: `docs/install/WINDOWS_MSI_GUIDE.md`
- GitHub Issues: https://github.com/eugenshila/JARVIS/issues
- OpenJarvis Discord: https://discord.gg/CMVBmDQ5Fj
