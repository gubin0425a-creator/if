@echo off
title Chronos v3.0 - AI Shorts Creator
color 0b
echo ==================================================================
echo   Welcome to Chronos v3.0 - AI Shorts Creator
echo ==================================================================
echo.
echo   [1/2] Loading Desktop GUI Application...
echo   [2/2] Running scripts in the background...
echo.
echo   * Close this window to exit the application.
echo ==================================================================
echo.

cd /d "%~dp0"

:: Start the native desktop GUI
.venv\Scripts\python.exe gui.py

pause
