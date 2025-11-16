@echo off
REM Production File Number Generation Script
REM This script will generate all 7.2M file numbers with tracking IDs

echo ==========================================
echo FILE NUMBER PRODUCTION GENERATION
echo ==========================================
echo.
echo Configuration:
echo - Total Records: 7,200,000
echo - Categories: 16
echo - Years: 1981-2025 (45 years^)
echo - Numbers per year: 10,000
echo - Batch size: 1,000 records
echo - Transaction size: 10,000 records
echo.
echo Features:
echo - Tracking ID: TRK-XXXXXXXX-XXXXX format
echo - Registry: 1, 2, 3 (updated format^)
echo - Group/Batch: sys_batch_no and registry_batch_no counters
echo.
echo Estimated time: ~65 minutes
echo ==========================================
echo.

REM Navigate to script directory
cd /d "%~dp0"

REM Run with virtual environment Python
echo Starting production file number generation...
.venv\Scripts\python.exe src\production_insertion.py

echo.
echo ==========================================
echo Production generation completed!
echo Check the logs for details and statistics.
echo ==========================================
pause