@echo off
REM JARVIS Windows Quick Installer (Batch)
REM For users who prefer double-click install

echo === JARVIS Installer ===
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo Make sure to check "Add python.exe to PATH"
    pause
    exit /b 1
)

echo Python found:
python --version

echo.
echo Installing JARVIS...
python -m pip install --upgrade pip
python -m pip install -e .[all] --break-system-packages
if %errorlevel% neq 0 (
    python -m pip install -e .[all]
)

echo.
echo Running doctor...
python -m jarvis.cli.main doctor

echo.
echo === Install complete ===
echo Try: jarvis ask "hello" --mock
echo For real AI, set OPENAI_API_KEY or install Ollama from https://ollama.com
echo.
pause
