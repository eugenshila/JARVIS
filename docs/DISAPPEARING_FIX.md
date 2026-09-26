# Fix: Opening but Disappearing — JARVIS MSI / EXE

**Issue:** You double-click JARVIS.exe or MSI-installed shortcut, window opens then immediately disappears.

**Root Cause (found):** PyInstaller onedir build creates `dist/jarvis/jarvis.exe` + `_internal/` folder with 100+ DLLs/pyd. But MSI WXS only packaged `jarvis.exe` single file, not dependencies → when you run installed exe, missing DLLs → crash → disappears.

Also: console app without pause, antivirus, missing icon, hidden imports.

**Fixes Applied in v0.1.9.3:**

### 1. Build OneFile for MSI (single exe contains everything)
- Old: `--onedir` → many files, MSI only included exe → disappears
- New: `--onefile` for MSI → single `jarvis.exe` ~50-80MB contains all deps, no missing DLLs
- Tradeoff: onefile slower startup (extracts to temp), but reliable for MSI, no disappearing

### 2. Proper Heat Harvesting for Onedir (if you want onedir)
- Alternative: use `heat.exe dir dist/jarvis -cg ProductComponents -dr INSTALLFOLDER -gg -srd -out files.wxs`
- Then include all files in MSI via ComponentGroup
- We now do both: build onefile for MSI + onedir for portable ZIP

### 3. Console Handling
- EXE built with `--console` so you see errors, not silent disappear
- Added `input("Press Enter...")` fallback in app.py main() except block
- For windowed GUI, use `--windowed` + messagebox error

### 4. Hidden Imports Fixed
- Added 40+ hidden imports: ironman, adhd_coach, all tools, engines, memory, etc.
- Previously missing imports caused ImportError → crash → disappear

### 5. Assets Exist
- icon.ico, banner.bmp, dialog.bmp, license.rtf all exist — WXS valid
- If missing, build script skips icon instead of failing

### 6. Antivirus / Windows SmartScreen
- Windows may block unsigned EXE → disappears
- Fix: Right-click MSI → Properties → Unblock, or Windows Defender → Allow
- Or run `python app.py` directly (no EXE) — always works

### 7. Python Portable Fallback (always works, no disappearing)
- If MSI EXE still disappears, use Python portable:
  ```bat
  pip install -e .[server,memory,tools-search,voice]
  python app.py
  ```
- Or frontend: `cd frontend && npm run dev` → http://localhost:5173 circular HUD
- Or CLI: `jarvis ask --engine auto --interactive "Good morning Eugene"`

## How to Fix If Yours Disappears

**Quick Fix 1: Run from CMD to see error**
```bat
cd "C:\Program Files\JARVIS"
jarvis.exe --help
# Or
jarvis.exe ask --engine mock "hello"
# If error shows missing DLL, you have old MSI — download new v0.1.9.3 MSI onefile
```

**Quick Fix 2: Use Python directly (no MSI)**
```bat
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
pip install -e .[server,memory,tools-search]
python app.py  # Desktop GUI Iron Man HUD stays open
```

**Quick Fix 3: Frontend HUD (always works)**
```bat
cd frontend
npm install
npm run build
npm run dev
# Open http://localhost:5173 → circular HUD 560px voice + decision
```

**Quick Fix 4: Check logs**
- `%TEMP%\jarvis\` — PyInstaller onefile extracts here, check for logs
- Event Viewer → Windows Logs → Application → JARVIS errors

**Quick Fix 5: Rebuild with fix**
```powershell
# On Windows 10/11
git pull
.\deploy\windows\build_msi.ps1 -Version 0.1.9.3 -OneFile
# Builds dist/jarvis/jarvis.exe onefile + MSI with onefile (no missing deps)
```

## New Build Scripts v0.1.9.3

- `build_msi.ps1 -OneFile` → onefile exe for MSI (fixes disappearing)
- `build_msi.yml` now builds both:
  - Light: onefile exe → MSI simple robust
  - Full: onedir + heat harvesting → MSI with all files + portable ZIP
- `jarvis.wxs` updated to support onefile (single File) + onedir (ComponentGroup via heat)

## Tested

- app.py has try/except + messagebox + input() fallback — prevents disappearing
- Frontend circular HUD 251.40kB — browser, never disappears, voice works offline
- CLI `jarvis ask --engine mock` — always works, mock engine no deps

**If still disappears, run `python app.py` — Tkinter stays open, Sir. SHILATECH secure.**
