@echo off
REM JARVIS Desktop GUI Launcher
REM Double-click to launch Tkinter GUI (stays open)

echo Launching JARVIS Desktop...

REM Try python app.py first (GUI)
if exist "%~dp0..\..\app.py" (
    python "%~dp0..\..\app.py"
    goto :end
)

if exist "app.py" (
    python app.py
    goto :end
)

REM Try jarvis-desktop command
where jarvis-desktop >nul 2>&1
if %errorlevel% equ 0 (
    jarvis-desktop
    goto :end
)

REM Try jarvis with gui launcher
where jarvis >nul 2>&1
if %errorlevel% equ 0 (
    python -m jarvis.cli.gui_launcher desktop 2>nul
    if %errorlevel% equ 0 goto :end
)

REM Try Program Files
if exist "C:\Program Files\JARVIS\jarvis.exe" (
    echo Desktop GUI needs Python + Tkinter. Trying CLI...
    "C:\Program Files\JARVIS\jarvis.exe" chat
    goto :end
)

echo ERROR: Could not launch Desktop GUI
echo.
echo For Desktop GUI, you need Python + Tkinter:
echo 1. Install Python from https://www.python.org/downloads/
echo 2. git clone https://github.com/eugenshila/JARVIS
echo 3. cd JARVIS
echo 4. python -m pip install -e .[all]
echo 5. python app.py
echo.
echo Or use CLI: jarvis chat --mock
pause

:end
