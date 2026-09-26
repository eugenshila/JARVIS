@echo off
setlocal
cd /d "%~dp0\..\.."
where python >nul 2>nul || (echo Python 3.10+ is required. & pause & exit /b 1)
where npm >nul 2>nul || (echo Node.js and npm are required. & pause & exit /b 1)
where ollama >nul 2>nul || (echo Install Ollama from https://ollama.com/download first. & pause & exit /b 1)
ollama list | findstr /i "qwen2.5:3b" >nul
if errorlevel 1 (
  echo Installing qwen2.5:3b in Ollama...
  ollama pull qwen2.5:3b || (pause & exit /b 1)
)
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv || (pause & exit /b 1)
)
".venv\Scripts\python.exe" -c "import jarvis, fastapi, uvicorn" >nul 2>nul
if errorlevel 1 ".venv\Scripts\python.exe" -m pip install -e . || (pause & exit /b 1)
".venv\Scripts\python.exe" -c "import sounddevice" >nul 2>nul
if errorlevel 1 ".venv\Scripts\python.exe" -m pip install sounddevice || echo Double-clap wake unavailable; chat still works.
if not exist "frontend\node_modules" (
  pushd frontend
  call npm ci || (popd & pause & exit /b 1)
  popd
)
start "JARVIS API" cmd /k .venv\Scripts\python.exe -m uvicorn jarvis.server.api:app --host 127.0.0.1 --port 8000
start "JARVIS HUD" /D "%CD%\frontend" cmd /k npm run dev
start "JARVIS Clap Wake" /min cmd /k "set JARVIS_HUD_URL=http://localhost:5173&& .venv\Scripts\python.exe -m jarvis.startup.hud_companion --greet --clap"
echo JARVIS will open at http://localhost:5173
start "" "http://localhost:5173"
endlocal
