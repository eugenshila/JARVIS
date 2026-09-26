# Windows MSI Build

This folder contains everything to build a Windows installer for JARVIS.

## Prerequisites (Windows 10/11)

1. **Python 3.10, 3.11, 3.12 or 3.13** (64-bit)
   - Download from https://www.python.org/downloads/
   - ✅ Check **"Add python.exe to PATH"** during install
   - Verify: `python --version`

2. **WiX Toolset v3.11** (for MSI, optional for EXE-only)
   - Download: https://wixtoolset.org/releases/
   - Or via Chocolatey: `choco install wixtoolset`
   - Or via winget: `winget install WiXToolset.WiXToolset`
   - Verify: `candle.exe -?` should work after adding to PATH
   - Default path: `C:\Program Files (x86)\WiX Toolset v3.11\bin\`

3. **Git** (optional, for cloning)
   - https://git-scm.com/download/win

4. **Visual C++ Build Tools** (only if you want FAISS/vLLM from source)
   - Usually not needed — we use prebuilt wheels
   - If needed: https://visualstudio.microsoft.com/visual-cpp-build-tools/

## Quick Build

### Option A: PowerShell one-liner (EXE + MSI)

```powershell
# Clone
git clone https://github.com/eugenshila/JARVIS
cd JARVIS

# Build (creates dist/JARVIS-0.1.0-x64.msi and dist/jarvis/jarvis.exe)
.\deploy\windows\build_msi.ps1 -Version 0.1.0

# Or build single-file EXE
.\deploy\windows\build_msi.ps1 -Version 0.1.0 -OneFile
```

### Option B: Manual with PyInstaller

```powershell
# Install deps
python -m pip install --upgrade pip
python -m pip install pyinstaller
python -m pip install -e .[all]

# Build EXE folder (recommended, faster startup)
python -m PyInstaller --onedir --name jarvis --console src/jarvis/cli/main.py --collect-all jarvis --add-data "configs;configs"

# Or single file
python -m PyInstaller --onefile --name jarvis src/jarvis/cli/main.py

# Output in dist/
```

### Option C: pip only (no installer)

```powershell
python -m pip install -e .
jarvis doctor
jarvis ask "hello" --mock
```

## Output

- `dist/jarvis/jarvis.exe` — main executable + dependencies folder
- `dist/JARVIS-0.1.0-x64.msi` — Windows installer (if WiX installed)
- `dist/JARVIS-0.1.0-portable.zip` — portable ZIP

## Installing the MSI

1. Double-click `JARVIS-0.1.0-x64.msi`
2. Follow wizard (installs to `C:\Program Files\JARVIS\`)
3. Adds `C:\Program Files\JARVIS\` to system PATH
4. Start menu shortcut: **JARVIS**

After install, open new PowerShell/CMD:

```powershell
jarvis doctor
jarvis --help
jarvis ask "hello" --mock
```

## What the MSI does

- Installs to `ProgramFiles64Folder\JARVIS\`
- Adds install folder to system PATH
- Creates Start Menu shortcuts
- Registers uninstaller (Add/Remove Programs)
- Does NOT require admin for portable ZIP, but MSI does for per-machine install

## Troubleshooting

**PyInstaller fails with "faiss not found":**
```powershell
python -m pip install faiss-cpu --no-cache-dir
```

**WiX candle.exe not found:**
- Add WiX bin to PATH: `$env:PATH += ";C:\Program Files (x86)\WiX Toolset v3.11\bin"`
- Or skip MSI: use EXE/ZIP only

**Antivirus flags EXE:**
- PyInstaller EXEs sometimes trigger false positives
- Add exception or use `pip install -e .` method instead

**Build on Linux for Windows (cross-compile):**
- Can't build MSI on Linux — MSI must be built on Windows
- But you can build Linux binary on Linux with same spec

## GitHub Actions (automated)

See `.github/workflows/build-msi.yml` — builds MSI on every tag push `v*`.

Workflow:
- Runs on `windows-latest`
- Installs Python, WiX, deps
- Builds EXE + MSI
- Uploads to Release

To trigger:
```bash
git tag v0.1.0
git push origin v0.1.0
```

## Icon

Place `assets/icon.ico` (256x256) for custom icon. If missing, default console icon used.

Generate ICO from PNG:
```powershell
# Using Pillow
python -c "from PIL import Image; Image.open('assets/icon.png').save('assets/icon.ico', sizes=[(256,256)])"
```
