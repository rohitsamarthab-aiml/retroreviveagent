@echo off
title RetroRevive — Hammurabi: The Living Empire
color 0A
cls

echo.
echo  ================================================================
echo   RETROREVIVE: HAMMURABI — THE LIVING EMPIRE
echo   Ancient Babylonian Kingdom Strategy
echo  ================================================================
echo.
echo  Starting launcher...
echo.

cd /d "%~dp0"

:: Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo  [ERROR] Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

:: Launch the cinematic Babylon menu
python launcher_menu.py

if errorlevel 1 (
    echo.
    echo  [INFO] Launching classic mode directly...
    python main.py
)

pause
