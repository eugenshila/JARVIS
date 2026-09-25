# Windows MSI Build — Complete Guide

## What is an MSI?

MSI (Microsoft Installer) is the standard Windows installer package. It handles:
- Installing to Program Files
- Adding to PATH and Start Menu
- Registering uninstaller
- Upgrade/downgrade logic
- Rollback on failure

This guide shows how to build `JARVIS-0.1.0-x64.msi`.

---

## Option 1: Build on Windows (Recommended)

### Prerequisites

1. **Windows 10/11 64-bit**
2. **Python 3.11** from https://www.python.org/downloads/
   - During install, check **Add python.exe to PATH**
3. **WiX Toolset v3.11** from https://wixtoolset.org/releases/
   - Download `wix311.exe` and install
   - Or via Chocolatey: `choco install wixtoolset`
   - Or winget: `winget install WiXToolset.WiXToolset`
   - Verify: open new PowerShell, `candle.exe -?` should show help
4. **Git** (optional): https://git-scm.com/download/win

### Build Steps

```powershell
# 1. Clone
git clone https://github.com/eugenshila/JARVIS
cd JARVIS

# 2. Build MSI (one command)
.\deploy\windows\build_msi.ps1 -Version 0.1.0

# Output:
# dist/jarvis/jarvis.exe (folder with dependencies)
# dist/JARVIS-0.1.0-x64.msi (installer)
# dist/JARVIS-0.1.0-portable.zip (portable)
```

**What the script does:**
1. Checks Python, WiX, PyInstaller
2. Installs deps: `pip install -e .[all]`
3. Builds EXE via PyInstaller (`--onedir` for faster startup)
4. Builds MSI via WiX `candle.exe` + `light.exe`
5. Creates portable ZIP

### Install the MSI

```powershell
# Double-click in Explorer, or:
msiexec /i dist\JARVIS-0.1.0-x64.msi

# Silent install (for IT deployment)
msiexec /i JARVIS-0.1.0-x64.msi /quiet

# After install, open NEW PowerShell:
jarvis doctor
jarvis ask "hello" --mock
```

**What MSI installs:**
- `C:\Program Files\JARVIS\jarvis.exe` + dependencies
- `C:\Program Files\JARVIS\configs\`
- PATH entry: `C:\Program Files\JARVIS\`
- Start Menu: `JARVIS` + `Uninstall JARVIS`
- Registry: `HKCU\Software\JARVIS`

### Uninstall

- Control Panel → Programs → JARVIS → Uninstall
- Or: `msiexec /x JARVIS-0.1.0-x64.msi`
- Or Start Menu → Uninstall JARVIS

---

## Option 2: Build EXE only (No WiX needed)

If you don't want to install WiX, you can build just EXE:

```powershell
# Install PyInstaller
python -m pip install pyinstaller
python -m pip install -e .[all]

# Build
python -m PyInstaller --onedir --name jarvis --console src/jarvis/cli/main.py --collect-all jarvis --add-data "configs;configs"

# Output: dist/jarvis/jarvis.exe
# Run: dist/jarvis/jarvis.exe doctor
```

---

## Option 3: Simple pip install (No MSI, for devs)

```powershell
python -m pip install -e .[all]
jarvis doctor
```

---

## Option 4: Build via GitHub Actions (Automated)

The repo includes `.github/workflows/build-msi.yml` which builds MSI automatically on tag push.

**Trigger:**
```bash
git tag v0.1.0
git push origin v0.1.0
# GitHub Actions builds MSI+EXE+ZIP and creates Release
```

Check releases at: https://github.com/eugenshila/JARVIS/releases

---

## Customizing the MSI

### Change version, name, icon

Edit `deploy/windows/jarvis.wxs`:

```xml
<Product Name="JARVIS - Personal AI" Version="0.1.0" Manufacturer="Your Company">
```

Icon: place `assets/icon.ico` (256x256) before build. Generate from PNG:

```powershell
python -c "from PIL import Image; Image.open('assets/icon.png').save('assets/icon.ico', sizes=[(256,256)])"
```

### Add files to MSI

Edit `deploy/windows/jarvis.wxs` → `<ComponentGroup>`.

Or auto-harvest with `heat.exe`:

```powershell
heat dir dist/jarvis -cg ProductComponents -dr INSTALLFOLDER -gg -srd -out deploy/windows/files.wxs
candle deploy/windows/jarvis.wxs deploy/windows/files.wxs -o deploy/windows/ -arch x64 -dSourceDir=dist/jarvis
light deploy/windows/jarvis.wixobj deploy/windows/files.wixobj -o dist/JARVIS.msi -ext WixUIExtension
```

### Per-user vs per-machine

Current MSI is `perMachine` (requires admin, installs to Program Files). For per-user (no admin, installs to LocalAppData):

In `jarvis.wxs`, change:
```xml
<Package InstallScope="perUser" ...>
```

---

## Troubleshooting MSI Build

**`candle.exe` not found:**
```powershell
$env:PATH += ";C:\Program Files (x86)\WiX Toolset v3.11\bin"
```

**PyInstaller fails: `faiss` not found:**
```powershell
pip install faiss-cpu --no-cache-dir
# Or build without FAISS: pip install -e . without [memory]
```

**Antivirus flags EXE:**
- PyInstaller EXEs sometimes trigger false positives
- Add exception or use `pip install` method
- Or sign EXE with code signing cert (for production)

**MSI build fails: `light.exe` error:**
- Ensure `dist/jarvis/jarvis.exe` exists first (PyInstaller must succeed)
- Check `deploy/windows/jarvis.wxs` paths are correct

**Can't build MSI on Linux/macOS:**
- MSI is Windows-only format, must be built on Windows or via GitHub Actions Windows runner
- On Linux, build Linux binary instead: `pyinstaller --onedir ...`

---

## What Users Need to Install JARVIS on Their Laptop

See [`docs/install/LAPTOP_SETUP.md`](LAPTOP_SETUP.md) for full guide. Summary:

| Need | Download | Size | Required? |
|------|----------|------|-----------|
| Python 3.11 | python.org | 50 MB | Yes, unless using MSI |
| JARVIS MSI | GitHub Releases | ~200-500 MB | For MSI install |
| OR Python + code | git clone | 5 MB | For pip install |
| Ollama (local AI) | ollama.com | 500 MB + models | Optional, for free local AI |
| OpenAI key | platform.openai.com | 0 | Optional, for cloud AI |
| WiX (build MSI) | wixtoolset.org | 50 MB | Only for building MSI |

**For end users (not building):**
- Just download `JARVIS-0.1.0-x64.msi` from Releases and double-click
- Or `JARVIS-0.1.0-portable.zip`, unzip, add to PATH

**For developers:**
- Python + `pip install -e .[all]`
- Ollama for local models
- WiX if building MSI

---

## MSI vs Portable ZIP vs pip

| Method | Pros | Cons |
|--------|------|------|
| **MSI** | Standard Windows install, PATH, Start Menu, uninstaller, admin deployment | Requires admin, larger, needs WiX to build |
| **Portable ZIP** | No admin, unzip and run, easy to move | No PATH, no uninstaller, manual |
| **pip install** | Smallest, dev friendly, easy update `pip install -U` | Needs Python, venv management |

For most laptop users: **MSI** is best. For devs: **pip**.

---

## Next Steps After MSI Install

```powershell
# Open new PowerShell after MSI install
jarvis doctor
jarvis init chat-simple --force
jarvis ask "Hello" --mock

# Real AI
# Option A: Cloud
$env:OPENAI_API_KEY="sk-..."
jarvis chat

# Option B: Local (free, private)
# Install Ollama from https://ollama.com/download
ollama pull llama3.2:3b
jarvis chat --engine ollama
```

Full guide: `docs/install/LAPTOP_SETUP.md`
