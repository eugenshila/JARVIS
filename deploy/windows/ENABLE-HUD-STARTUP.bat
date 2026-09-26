@echo off
setlocal
cd /d "%~dp0\..\.."
if not exist ".venv\Scripts\python.exe" (echo Run RUN-OLLAMA-HUD.bat once before enabling startup. & pause & exit /b 1)
".venv\Scripts\python.exe" -m jarvis.startup.hud_companion --install-startup "%CD%\deploy\windows\RUN-OLLAMA-HUD.bat"
if errorlevel 1 (pause & exit /b 1)
echo JARVIS will open after your next Windows sign-in.
pause
