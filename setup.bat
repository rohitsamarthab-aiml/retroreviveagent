@echo off
REM ============================================================
REM  RetroRevive — Setup Script
REM  Tested on Python 3.14.0 / Windows 10/11 (64-bit)
REM ============================================================
title RetroRevive Setup

echo.
echo  =====================================================
echo   RETROREVIVE — Ancient Babylonian Kingdom Strategy
echo   Setup Script  ^|  Python 3.14 ^| pygame-ce 2.5.8
echo  =====================================================
echo.

REM --- Locate Python ---
set PYTHON_CMD=
where python >nul 2>&1
if %ERRORLEVEL%==0 (
    for /f "delims=" %%i in ('where python') do (
        set PYTHON_CMD=%%i
        goto :found_python
    )
)
where py >nul 2>&1
if %ERRORLEVEL%==0 (
    set PYTHON_CMD=py
    goto :found_python
)
echo  [ERROR] Python not found. Please install Python 3.14 from https://www.python.org
echo          and add it to your PATH, then re-run this script.
pause
exit /b 1

:found_python
echo  [OK] Python found: %PYTHON_CMD%
%PYTHON_CMD% --version

REM --- Check Python version is 3.x ---
%PYTHON_CMD% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Python 3.10 or later is required. Found:
    %PYTHON_CMD% --version
    pause
    exit /b 1
)

REM --- Create virtual environment if missing ---
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo  Creating virtual environment...
    %PYTHON_CMD% -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo  [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo  [OK] Virtual environment created at .venv\
) else (
    echo  [OK] Virtual environment already exists at .venv\
)

REM --- Activate venv ---
call .venv\Scripts\activate.bat

REM --- Upgrade pip ---
echo.
echo  Upgrading pip...
python -m pip install --upgrade pip --quiet

REM --- Install dependencies ---
echo.
echo  Installing RetroRevive dependencies...
echo  (pygame-ce 2.5.8 — pre-built wheel for Python 3.14)
echo.

REM Remove conflicting pygame if installed
pip show pygame >nul 2>&1
if %ERRORLEVEL%==0 (
    echo  Removing conflicting 'pygame' package (replaced by pygame-ce)...
    pip uninstall pygame -y --quiet
)

pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [ERROR] Dependency installation failed. Check your internet connection.
    pause
    exit /b 1
)

REM --- Run tests ---
echo.
echo  Running verification tests...
set SDL_VIDEODRIVER=dummy
set SDL_AUDIODRIVER=dummy
python -m pytest test_game.py test_modern.py test_auth.py test_ui.py test_platform.py "games\23_matches\test_engine.py" -q
if %ERRORLEVEL% NEQ 0 (
    echo  [WARNING] Some tests failed. The game may still run. Check output above.
) else (
    echo  [OK] All tests passed!
)

echo.
echo  =====================================================
echo   Setup complete! Run  RUN_RETROREVIVE.bat  to play.
echo  =====================================================
echo.
pause

