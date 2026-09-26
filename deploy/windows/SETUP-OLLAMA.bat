@echo off
setlocal EnableExtensions
 title JARVIS Ollama Setup - 8GB RAM
 echo.
 echo ================================================
 echo   JARVIS + Ollama setup for 8GB RAM computers
 echo ================================================
 echo.

 where ollama >nul 2>&1
 if errorlevel 1 (
   echo ERROR: Ollama was not found on PATH.
   echo Install or repair Ollama from https://ollama.com/download/windows
   pause
   exit /b 1
 )

 echo Ollama version:
 ollama --version
 echo.

 echo Checking Ollama service...
 powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 5 ^| Out-Null; exit 0 } catch { exit 1 }"
 if errorlevel 1 (
   echo Ollama is not responding. Starting Ollama...
   start "Ollama" /min ollama app
   timeout /t 5 /nobreak >nul
 )

 powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 10 ^| Out-Null; exit 0 } catch { exit 1 }"
 if errorlevel 1 (
   echo ERROR: Ollama API is unavailable at http://localhost:11434
   echo Start Ollama manually, then run this script again.
   pause
   exit /b 1
 )

 echo.
 echo Installing recommended lightweight model: llama3.2:3b
 echo This may take several minutes and uses approximately 2-3 GB.
 ollama pull llama3.2:3b
 if errorlevel 1 (
   echo ERROR: Failed to download llama3.2:3b
   pause
   exit /b 1
 )

 echo.
 echo Ollama models installed:
 ollama list
 echo.
 echo Launching JARVIS with llama3.2:3b...
 set "JARVIS_MODEL=llama3.2:3b"
 if exist jarvis.exe (
   jarvis.exe chat --engine ollama
 ) else if exist .venv\Scripts\python.exe (
   .venv\Scripts\python.exe -m jarvis.cli.main chat --engine ollama
 ) else (
   python -m jarvis.cli.main chat --engine ollama
 )

 if errorlevel 1 (
   echo.
   echo JARVIS exited with an error. Run deploy\windows\TROUBLESHOOT.bat for diagnostics.
 )
 pause
