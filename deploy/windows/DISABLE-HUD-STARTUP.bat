@echo off
setlocal
cd /d "%~dp0\..\.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m jarvis.startup.hud_companion --remove-startup
) else (
  del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS-HUD.bat" 2>nul
  echo JARVIS HUD sign-in startup removed.
)
pause
