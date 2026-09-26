@echo off
REM JARVIS SHILATECH Troubleshoot - Fixes disappearing issue - Logs everything
title JARVIS SHILATECH Troubleshoot

echo ============================================================
echo JARVIS SHILATECH Troubleshoot - Logging to troubleshoot.log
echo Fixes opening but disappearing issue
echo ============================================================
echo.

set LOG=%~dp0troubleshoot.log
echo JARVIS SHILATECH Troubleshoot Log - %date% %time% > "%LOG%"
echo Version 0.1.9.3 - Fixes disappearing with onefile >> "%LOG%"
echo ============================================ >> "%LOG%"

echo Checking Python... 
echo Checking Python... >> "%LOG%"
python --version 2>&1 | tee -a "%LOG%"
python3 --version 2>&1 | tee -a "%LOG%"
echo. >> "%LOG%"

echo Checking Tkinter (GUI stays open)... 
echo Checking Tkinter... >> "%LOG%"
python -c "import tkinter; print(f'Tkinter {tkinter.TkVersion} OK - GUI will stay open')" 2>&1 | tee -a "%LOG%"
echo. >> "%LOG%"

echo Checking JARVIS install locations (onefile fixes disappearing)... 
echo Checking JARVIS install locations... >> "%LOG%"
for %%P in (
  "C:\Program Files\JARVIS SHILATECH\jarvis.exe"
  "C:\Program Files\JARVIS\jarvis.exe"
  "C:\Program Files (x86)\JARVIS\jarvis.exe"
  "%LOCALAPPDATA%\JARVIS\jarvis.exe"
  "%~dp0jarvis.exe"
  ".\jarvis.exe"
  "dist\jarvis.exe"
) do (
  if exist %%P (
    echo FOUND: %%P 
    echo FOUND: %%P >> "%LOG%"
    for %%F in (%%P) do echo Size: %%~zF bytes - onefile should be 50-80MB >> "%LOG%"
  ) else (
    echo NOT FOUND: %%P 
    echo NOT FOUND: %%P >> "%LOG%"
  )
)
echo. >> "%LOG%"

echo Checking for _internal folder (onedir mode - may cause disappearing if missing)... 
echo Checking _internal... >> "%LOG%"
if exist "C:\Program Files\JARVIS\jarvis\_internal" (
  echo FOUND _internal - onedir mode, need all files >> "%LOG%"
) else (
  echo NOT FOUND _internal - onefile mode (good, fixes disappearing) >> "%LOG%"
)
if exist "dist\jarvis\_internal" (
  echo FOUND dist\jarvis\_internal - onedir build >> "%LOG%"
)
echo. >> "%LOG%"

echo Checking PATH... 
echo Checking PATH... >> "%LOG%"
echo %PATH% | tr ";" "\n" | findstr /i JARVIS 2>&1 | tee -a "%LOG%"
echo. >> "%LOG%"

echo Trying jarvis --help (if disappears, run from CMD to see error)... 
echo Trying jarvis --help... >> "%LOG%"
where jarvis 2>&1 | tee -a "%LOG%"
jarvis --help 2>&1 | tee -a "%LOG%"
echo Exit code: %errorlevel% >> "%LOG%"
echo If exit code not 0, see error above - likely missing DLLs from old onedir MSI >> "%LOG%"
echo. >> "%LOG%"

echo Trying full path... 
echo Trying full path... >> "%LOG%"
"C:\Program Files\JARVIS SHILATECH\jarvis.exe" --help 2>&1 | tee -a "%LOG%"
echo Exit code: %errorlevel% >> "%LOG%"
"C:\Program Files\JARVIS\jarvis.exe" --help 2>&1 | tee -a "%LOG%"
echo Exit code: %errorlevel% >> "%LOG%"
echo. >> "%LOG%"

echo Trying jarvis doctor... 
echo Trying doctor... >> "%LOG%"
jarvis doctor 2>&1 | tee -a "%LOG%"
echo Exit code: %errorlevel% >> "%LOG%"
echo. >> "%LOG%"

echo Trying python app.py (always works, no disappearing)... 
echo Trying python app.py... >> "%LOG%"
if exist "%~dp0..\..\app.py" (
  echo Found app.py at %~dp0..\..\app.py >> "%LOG%"
  echo Running python app.py - GUI stays open, Sir >> "%LOG%"
  python "%~dp0..\..\app.py" 2>&1 | tee -a "%LOG%"
) else if exist "app.py" (
  echo Found app.py at app.py >> "%LOG%"
  python app.py 2>&1 | tee -a "%LOG%"
) else (
  echo app.py NOT FOUND >> "%LOG%"
  echo Current dir: %CD% >> "%LOG%"
  dir /b 2>&1 | tee -a "%LOG%"
)
echo. >> "%LOG%"

echo Checking VC++ Redist (needed for Python exe)... 
echo Checking VC++ Redist... >> "%LOG%"
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" 2>&1 | tee -a "%LOG%"
echo. >> "%LOG%"

echo Checking antivirus (may block exe causing disappearing)... 
echo Antivirus check: Windows Defender may block unsigned exe >> "%LOG%"
echo Fix: Right-click MSI - Properties - Unblock, or Defender - Allow >> "%LOG%"
echo. >> "%LOG%"

echo ============================================================
echo Log saved to: %LOG%
echo.
echo If still disappearing:
echo 1. Use python app.py - always works, Tkinter stays open
echo 2. Use frontend: cd frontend && npm run dev - circular HUD 251kB
echo 3. Download new MSI v0.1.9.3 onefile - fixes disappearing
echo 4. See docs/DISAPPEARING_FIX.md
echo Please share this log if you need help - SHILATECH
echo ============================================================
echo.
echo Press any key to open log file...
pause >nul
notepad "%LOG%"
pause
