@echo off
setlocal
title Chronos v4.0 - AI Video Creator
color 0b

cd /d "%~dp0"

echo ==================================================================
echo   * Chronos v4.0 - AI Video Creator *
echo ==================================================================
echo.
echo   [System] Checking virtual environment...

if not exist ".venv\Scripts\python.exe" (
    echo   [Error] .venv environment not found.
    pause
    exit /b
)

echo   [System] Loading Chronos v4.0 Engine...
echo   [System] Please wait...
echo.

.venv\Scripts\python.exe gui.py

echo.
echo ==================================================================
echo   [System] Program terminated.
echo ==================================================================
pause
