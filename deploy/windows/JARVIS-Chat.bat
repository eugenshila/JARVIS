@echo off
REM JARVIS Chat Launcher - Keeps window open
REM Double-click this file to start JARVIS chat

echo ============================================================
echo JARVIS - Personal AI, On Personal Devices
echo ============================================================
echo.
echo Starting chat... (type /exit to quit)
echo.

REM Try jarvis command first (if in PATH)
where jarvis >nul 2>&1
if %errorlevel% equ 0 (
    jarvis chat
    goto :pause
)

REM Try Program Files location
if exist "C:\Program Files\JARVIS\jarvis.exe" (
    "C:\Program Files\JARVIS\jarvis.exe" chat
    goto :pause
)

REM Try local exe
if exist "%~dp0jarvis.exe" (
    "%~dp0jarvis.exe" chat
    goto :pause
)

REM Fallback to python
echo JARVIS exe not found, trying python...
python -m jarvis.cli.main chat 2>nul
if %errorlevel% equ 0 goto :pause

python -m jarvis.cli.main chat --help 2>nul
if %errorlevel% neq 0 (
    echo ERROR: JARVIS not found!
    echo.
    echo Please:
    echo 1. Install MSI from https://github.com/eugenshila/JARVIS/releases
    echo 2. Or run: python -m pip install -e .[all]
    echo 3. Then: jarvis chat --mock
)

:pause
echo.
echo Chat ended.
pause
