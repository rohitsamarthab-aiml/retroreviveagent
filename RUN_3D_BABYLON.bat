@echo off
setlocal
title RetroRevive: The Living Empire (3D Edition)

echo =====================================================================
echo  RETROREVIVE: THE LIVING EMPIRE -- 3D BABYLONIAN KINGDOM
echo =====================================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Running setup.bat first...
    call setup.bat
    if errorlevel 1 goto :fail
)

echo [*] Launching 3D Hardware Accelerated Babylonian Kingdom...
echo [*] Controls: [1-6] Camera Presets | [T] Throne | [M] Military | [A] Agriculture | [Space] Decree
echo.

".venv\Scripts\python.exe" main_3d.py %*

if errorlevel 1 (
    echo.
    echo [ERROR] Application closed with an error.
    pause
    exit /b 1
)

exit /b 0

:fail
echo.
echo [ERROR] Failed to start 3D engine.
pause
exit /b 1

