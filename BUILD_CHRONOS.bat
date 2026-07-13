@echo off
setlocal
title Chronos v4.0 EXE Builder
color 0e

cd /d "%~dp0"

echo ==================================================================
echo   ⚡ Chronos v4.0 - Standalone EXE Builder ⚡
echo ==================================================================
echo.
echo   [System] 빌드 환경을 준비하고 있습니다...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo   [Error] .venv 환경을 찾을 수 없습니다. 빌드를 중단합니다.
    pause
    exit /b
)

echo   [System] 빌드 프로세스를 시작합니다. (약 1~3분 소요)
echo   [System] 이 창을 닫지 마세요...
echo.

.venv\Scripts\python.exe tools\build_exe.py

echo.
echo ==================================================================
echo   [System] 빌드 작업이 완료되었습니다.
echo   [System] 'dist' 폴더 안에 Chronos_AI_Creator.exe가 생성되었습니다.
echo ==================================================================
pause
