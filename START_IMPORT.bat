@echo off
REM START_IMPORT.bat - One-click import starter with menu

setlocal enabledelayedexpansion

cls
echo.
echo ╔══════════════════════════════════════════════════════════════════════╗
echo ║                                                                      ║
echo ║           CSV FILE NUMBER IMPORTER - QUICK START MENU                ║
echo ║                                                                      ║
echo ║  Fast, Modern Web UI with Real-Time Progress Tracking                ║
echo ║  1000+ records/second • Automatic Grouping Matching                  ║
echo ║  Beautiful Dashboard • Zero Configuration                            ║
echo ║                                                                      ║
echo ╚══════════════════════════════════════════════════════════════════════╝
echo.
echo OPTIONS:
echo.
echo   1 = Start Web UI (Recommended - Beautiful Dashboard)
echo   2 = Run Command Line Import (Simple Text Output)
echo   3 = Run System Test (Verify Setup)
echo   4 = View Quick Start Guide
echo   5 = View Full Documentation
echo   6 = Exit
echo.
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto web_ui
if "%choice%"=="2" goto cli_import
if "%choice%"=="3" goto system_test
if "%choice%"=="4" goto quick_start
if "%choice%"=="5" goto full_docs
if "%choice%"=="6" goto exit
goto invalid

:web_ui
echo.
echo Starting CSV Import Web UI...
echo Browser will open automatically at http://localhost:5000
echo.
cd /d "%~dp0"
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
    echo Error: Virtual environment not found
    pause
    goto menu
)
python src\run_csv_import_ui.py
goto menu

:cli_import
echo.
echo Starting Command Line Import...
echo.
cd /d "%~dp0"
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
    echo Error: Virtual environment not found
    pause
    goto menu
)
python src\fast_csv_importer.py --csv FileNos_PRO.csv --control-tag PROD
pause
goto menu

:system_test
echo.
echo Running System Test...
echo.
cd /d "%~dp0"
call .venv\Scripts\activate.bat 2>nul
if errorlevel 1 (
    echo Error: Virtual environment not found
    pause
    goto menu
)
python test_system.py
pause
goto menu

:quick_start
echo.
if exist QUICK_START.md (
    start notepad QUICK_START.md
) else (
    echo File not found: QUICK_START.md
    pause
)
goto menu

:full_docs
echo.
if exist CSV_IMPORTER_README.md (
    start notepad CSV_IMPORTER_README.md
) else (
    echo File not found: CSV_IMPORTER_README.md
    pause
)
goto menu

:invalid
echo.
echo Invalid choice. Please enter 1-6.
echo.
pause
cls
goto start

:exit
cls
echo.
echo Thank you for using CSV File Number Importer!
echo.
exit /b 0

endlocal
