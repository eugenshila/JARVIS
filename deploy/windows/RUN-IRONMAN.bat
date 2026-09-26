@echo off
REM JARVIS Iron Man Mode - Interactive AI like in movie
REM Double-click this file - WILL stay open, witty personality

echo ============================================================
echo JARVIS Iron Man Mode - Interactive AI
echo Personal AI, On Personal Devices
echo ============================================================
echo.
echo This is JARVIS like in Iron Man movie:
echo - Witty British humor, calls you Sir
echo - Controls lights, music, system (mock + real via tools)
echo - Remembers preferences, proactive
echo - Voice ready (use --voice flag if you have mic)
echo.
echo Checking Python...
python --version 2>&1
if %errorlevel% neq 0 (
  echo ERROR: Python not found! Install from https://www.python.org/downloads/
  pause
  exit /b 1
)

echo Installing JARVIS...
python -m pip install -e .[server] --break-system-packages 2>nul
if %errorlevel% neq 0 (
  python -m pip install -e .[server] 2>nul
)

echo.
echo ============================================================
echo Try these commands (offline mock works, no internet needed):
echo - Good morning JARVIS
echo - Turn off the lights in the lab
echo - What should I work on today?
echo - System status
echo - Play some music
echo - I am Iron Man
echo - Tell me a joke
echo - Who are you?
echo ============================================================
echo.
echo Starting Iron Man mode (text - for voice add --voice flag)...
echo Type /exit to quit
echo.

REM Set PYTHONPATH and run
set PYTHONPATH=%~dp0src;%~dp0
python -m jarvis.cli.main ironman --engine mock 2>&1
if %errorlevel% neq 0 (
  echo Trying with src path...
  set PYTHONPATH=%~dp0src
  python -m jarvis.cli.main ironman --engine mock
)

echo.
echo Iron Man mode ended.
pause
