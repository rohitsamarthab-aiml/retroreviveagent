@echo off
REM ============================================================
REM  RUN_RETROREVIVE.bat — One-click game launcher
REM  RetroRevive: Ancient Babylonian Kingdom Strategy
REM ============================================================
title RetroRevive — Launching...

REM Change to script directory so relative paths work
cd /d "%~dp0"

REM --- Check virtual environment ---
if not exist ".venv\Scripts\activate.bat" (
    echo  [!] Virtual environment not found. Running setup first...
    echo.
    call setup.bat
)

REM --- Activate virtual environment ---
call .venv\Scripts\activate.bat

REM --- Verify pygame-ce is installed ---
python -c "import pygame" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [!] pygame-ce not found. Installing...
    pip install pygame-ce==2.5.8 --quiet
)

REM --- Clear SDL dummy drivers (allow real display) ---
set SDL_VIDEODRIVER=
set SDL_AUDIODRIVER=

title RetroRevive — Ancient Babylonian Kingdom

REM --- Launch the game ---
echo.
echo  Launching RetroRevive...
echo.
python main.py

REM --- If pygame fails, fall back to CLI ---
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [!] Graphical launch failed. Falling back to terminal mode...
    python main.py --cli
)

pause

