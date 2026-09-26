@echo off
title JARVIS SHILATECH Desktop
echo JARVIS SHILATECH Desktop GUI
python app.py
if %errorlevel% neq 0 (
    echo Failed, trying with error details...
    python app.py
    echo.
    echo Error code %errorlevel%
)
pause
