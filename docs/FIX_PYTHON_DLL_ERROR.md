# Fix: [PYI-12104:ERROR] Failed to load Python DLL 'C:\Program Files\JARVIS\_internal\python311.dll'

**Error you saw:**
```
[PYI-12104:ERROR] Failed to load Python DLL 'C:\Program Files\JARVIS\_internal\python311.dll'.
LoadLibrary: The specified module could not be found.
```

**Root Cause:** You installed old MSI v0.1.9 or v0.1.9.2 which was built with PyInstaller --onedir:
- Onedir creates `dist/jarvis/jarvis.exe` + `dist/jarvis/_internal/` folder with 100+ files including python311.dll
- But MSI WXS only packaged `jarvis.exe` single file, NOT _internal folder
- So installed `C:\Program Files\JARVIS\jarvis.exe` looks for `C:\Program Files\JARVIS\_internal\python311.dll` which doesn't exist → LoadLibrary fails

**Fixed in v0.1.9.3 onefile MSI — single exe contains all DLLs, no _internal needed.**

## Immediate Fix (3 options)

### Option 1: Download new onefile MSI v0.1.9.3 (recommended)

1. Uninstall old:
   ```
   Control Panel -> Programs -> Uninstall JARVIS
   ```

2. Download new MSI onefile:
   - https://github.com/eugenshila/JARVIS/actions/runs/36231538217 -> artifact jarvis-windows-light -> JARVIS-0.1.9.3-x64.msi (onefile 50-80MB)
   - Or https://github.com/eugenshila/JARVIS/actions/runs/36231538230 (full, in progress)
   - Or Releases https://github.com/eugenshila/JARVIS/releases/tag/v0.1.9.3

3. Install:
   ```
   Double-click JARVIS-0.1.9.3-x64.msi -> C:\Program Files\JARVIS SHILATECH\jarvis.exe (onefile, no _internal)
   jarvis --help
   ```

Why onefile fixes: bundles python311.dll inside exe, extracts to %TEMP%\_MEIxxxxxx, no _internal needed.

### Option 2: Python portable — always works, no DLL

```bat
git clone https://github.com/eugenshila/JARVIS
cd JARVIS
pip install -e .[server,memory,tools-search,voice]
python app.py  # GUI stays open
```

Frontend:
```bat
cd frontend && npm install && npm run build && npm run dev
# http://localhost:5173 circular HUD
```

### Option 3: Manual fix for old onedir

```bat
xcopy /E /I dist\jarvis\_internal "C:\Program Files\JARVIS\_internal"
```

Or use heat.exe:
```
heat.exe dir dist/jarvis -cg ProductComponents -dr INSTALLFOLDER -gg -srd -out files.wxs
```

## Verify

```bat
dir "C:\Program Files\JARVIS SHILATECH\"
# jarvis.exe single file 50-80MB, no _internal

"C:\Program Files\JARVIS SHILATECH\jarvis.exe" --help
# No PYI-12104 error
```

**SHILATECH • Onefile MSI fixes python311.dll not found**
