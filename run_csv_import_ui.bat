@echo off
REM CSV Import UI Launcher for Windows

setlocal enabledelayedexpansion

echo.
echo ========================================
echo CSV File Number Importer Web UI
echo ========================================
echo.

REM Get the script directory
set SCRIPT_DIR=%~dp0

REM Navigate to the script directory
cd /d "%SCRIPT_DIR%"

REM Check if .venv exists
if exist ".venv\" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else if exist "..\.venv\" (
    echo Activating virtual environment...
    cd ..
    call .venv\Scripts\activate.bat
    cd src
) else (
    echo Error: Virtual environment not found
    echo Please run: python -m venv .venv
    pause
    exit /b 1
)

REM Check if Flask and dependencies are installed
python -c "import flask, flask_socketio" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install Flask==3.0.0 flask-socketio==5.3.5 python-socketio==5.10.0 python-engineio==4.8.0
)

echo.
echo Starting CSV Import Web UI...
echo Opening browser to http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo.

python run_csv_import_ui.py

pause
