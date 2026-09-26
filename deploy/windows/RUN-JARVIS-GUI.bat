@echo off
title JARVIS SHILATECH - Desktop GUI - Stays Open
echo ========================================
echo JARVIS SHILATECH v0.1.9.3
echo Voice speaks both online/offline
echo Circular HUD + Hybrid Interactive
echo ========================================
echo.

REM Check Python
python --version
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Install Python 3.11 from python.org
    echo Make sure to check "Add python.exe to PATH"
    pause
    exit /b 1
)

REM Check Tkinter
python -c "import tkinter; print('Tkinter OK - GUI will stay open')"
if %errorlevel% neq 0 (
    echo ERROR: Tkinter not available
    pause
    exit /b 1
)

echo.
echo Installing JARVIS if needed...
python -m pip install -e .[server,memory,tools-search,voice] --break-system-packages 2>nul
if %errorlevel% neq 0 (
    python -m pip install -e .[server,memory,tools-search]
)

echo.
echo Starting JARVIS Desktop GUI - Iron Man HUD - stays open...
echo If window disappears, check error below and see docs/DISAPPEARING_FIX.md
echo.

python app.py

echo.
echo ========================================
echo JARVIS GUI closed
echo If it disappeared immediately, run from CMD to see error:
echo   python app.py
echo Or frontend: cd frontend && npm run dev
echo See docs/DISAPPEARING_FIX.md
echo ========================================
pause
