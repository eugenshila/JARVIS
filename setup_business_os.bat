@echo off
REM JARVIS Business OS Setup — Agentic Harness + OpenAI + Goals + Memory — SHILATECH
REM Run this after git clone

echo ============================================
echo JARVIS Business OS Setup — SHILATECH
echo Agentic Harness + OpenAI + Goals + Memory
echo ============================================

REM 1. Install harness
echo [1/4] Installing agentic harness...
python -m pip install -e .[server,memory,tools-search,voice] --break-system-packages
if %errorlevel% neq 0 (
    echo Trying without break-system-packages...
    python -m pip install -e .[server,memory,tools-search,voice]
)

echo.
echo [1/4] Harness check...
python -m jarvis.cli.main business harness

echo.
echo [2/4] Setup OpenAI as primary brain...
echo Set OPENAI_API_KEY env first: set OPENAI_API_KEY=sk-proj-...
echo Then run: jarvis business openai --model gpt-4o-mini
echo.
set /p OPENAI_KEY="Enter OpenAI API Key (or press Enter to skip): "
if not "%OPENAI_KEY%"=="" (
    set OPENAI_API_KEY=%OPENAI_KEY%
    python -m jarvis.cli.main business openai --model gpt-4o-mini
    python -m jarvis.cli.main init business-os --force
) else (
    echo Skipping OpenAI setup — will use mock offline
    python -m jarvis.cli.main init business-os --force
)

echo.
echo [3/4] Teach JARVIS your business...
python -m jarvis.cli.main business init --name Eugene --business-name SHILATECH --north-star "Build SHILATECH into leading personal AI company — local-first, Iron Man quality" --force

echo.
echo Running interactive teach — goals, priorities, workflows, rules...
python -m jarvis.cli.main business teach

echo.
echo [4/4] Persistent memory check...
python -m jarvis.cli.main business memory --action stats
python -m jarvis.cli.main business memory --action list

echo.
echo ============================================
echo Business OS Setup Complete — SHILATECH
echo ============================================
echo.
echo Test:
echo   jarvis ask --agent business_os "What should I work on today?"
echo   jarvis chat --agent business_os --engine openai
echo   python app.py — Modern circular HUD
echo.
echo Docs: docs/BUSINESS_OS.md
echo Profile: %USERPROFILE%\.jarvis\business_profile.toml
echo Memory: %USERPROFILE%\.jarvis\memory\
echo.
pause
