@echo off
REM JARVIS Troubleshoot - Logs everything to file and keeps window open

echo ============================================================
echo JARVIS Troubleshoot - Logging to troubleshoot.log
echo ============================================================
echo.

set LOG=%~dp0troubleshoot.log
echo JARVIS Troubleshoot Log - %date% %time% > "%LOG%"
echo ============================================ >> "%LOG%"

echo Checking Python... | tee -a "%LOG%"
python --version 2>&1 | tee -a "%LOG%"
python3 --version 2>&1 | tee -a "%LOG%"
echo. >> "%LOG%"

echo Checking Tkinter... | tee -a "%LOG%"
python -c "import tkinter; print(f'Tkinter {tkinter.TkVersion} OK')" 2>&1 | tee -a "%LOG%"
echo. >> "%LOG%"

echo Checking JARVIS install locations... | tee -a "%LOG%"
for %%P in (
  "C:\Program Files\JARVIS\jarvis.exe"
  "C:\Program Files (x86)\JARVIS\jarvis.exe"
  "%LOCALAPPDATA%\JARVIS\jarvis.exe"
  "%~dp0jarvis.exe"
  ".\jarvis.exe"
) do (
  if exist %%P (
    echo FOUND: %%P | tee -a "%LOG%"
    echo Size: | tee -a "%LOG%"
    for %%F in (%%P) do echo %%~zF bytes | tee -a "%LOG%"
  ) else (
    echo NOT FOUND: %%P | tee -a "%LOG%"
  )
)
echo. >> "%LOG%"

echo Checking PATH... | tee -a "%LOG%"
echo %PATH% | tr ";" "\n" | findstr /i JARVIS 2>&1 | tee -a "%LOG%"
echo. >> "%LOG%"

echo Trying jarvis --help... | tee -a "%LOG%"
where jarvis 2>&1 | tee -a "%LOG%"
jarvis --help 2>&1 | tee -a "%LOG%"
echo Exit code: %errorlevel% | tee -a "%LOG%"
echo. >> "%LOG%"

echo Trying full path... | tee -a "%LOG%"
"C:\Program Files\JARVIS\jarvis.exe" --help 2>&1 | tee -a "%LOG%"
echo Exit code: %errorlevel% | tee -a "%LOG%"
echo. >> "%LOG%"

echo Trying jarvis doctor... | tee -a "%LOG%"
"C:\Program Files\JARVIS\jarvis.exe" doctor 2>&1 | tee -a "%LOG%"
echo Exit code: %errorlevel% | tee -a "%LOG%"
echo. >> "%LOG%"

echo Trying python app.py... | tee -a "%LOG%"
if exist "%~dp0..\..\app.py" (
  echo Found app.py at %~dp0..\..\app.py | tee -a "%LOG%"
  python "%~dp0..\..\app.py" 2>&1 | tee -a "%LOG%"
) else if exist "app.py" (
  echo Found app.py at app.py | tee -a "%LOG%"
  python app.py 2>&1 | tee -a "%LOG%"
) else (
  echo app.py NOT FOUND | tee -a "%LOG%"
  echo Current dir: %CD% | tee -a "%LOG%"
  dir /b 2>&1 | tee -a "%LOG%"
)
echo. >> "%LOG%"

echo Checking VC++ Redist... | tee -a "%LOG%"
reg query "HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" 2>&1 | tee -a "%LOG%"
echo. >> "%LOG%"

echo ============================================================
echo Log saved to: %LOG%
echo Please share this log file if you need help
echo ============================================================
echo.
echo Press any key to open log file...
pause >nul
notepad "%LOG%"
pause
