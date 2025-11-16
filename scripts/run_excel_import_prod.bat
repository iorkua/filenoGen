@echo off
setlocal
cd /d "%~dp0.."
set "REPO_ROOT=%CD%"

start "" powershell -NoExit -Command ^
 "cd '%REPO_ROOT%'; ^
  & .\.venv\Scripts\Activate.ps1; ^
  $env:EXCEL_IMPORT_FILE='FileNos_PRO.xlsx'; ^
  $env:EXCEL_IMPORT_NROWS='0'; ^
  $env:EXCEL_IMPORT_CONTROL='PROD'; ^
  python src\excel_importer.py"
