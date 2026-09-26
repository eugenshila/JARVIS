@echo off
title JARVIS SHILATECH Chat - Stays Open
echo JARVIS SHILATECH Chat - Interactive - Voice
python -m jarvis.cli.main chat --interactive
if %errorlevel% neq 0 (
    echo.
    echo Chat failed, trying mock engine...
    python -m jarvis.cli.main chat --engine mock
)
pause
