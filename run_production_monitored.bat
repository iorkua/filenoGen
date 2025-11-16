@echo off
REM Production File Number Generation with Monitoring
REM This script will generate all 7.2M file numbers with real-time progress

echo ==========================================
echo FILE NUMBER PRODUCTION GENERATION
echo ==========================================
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found!
    echo Please make sure .venv directory exists in the project folder.
    pause
    exit /b 1
)

REM Run with virtual environment Python
echo Running with monitoring and progress tracking...
echo.
.venv\Scripts\python.exe run_production_monitored.py

echo.
echo ==========================================
echo Script execution completed!
echo ==========================================
pause