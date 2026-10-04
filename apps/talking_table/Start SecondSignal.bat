@echo off
setlocal
cd /d "%~dp0..\.."
if errorlevel 1 goto folder_error
set "PYTHONUTF8=1"
set "PYTHONDONTWRITEBYTECODE=1"
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 goto run_py
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if not errorlevel 1 goto run_python
echo Python 3.10 or newer is needed; its download page is opening.
start "" "https://www.python.org/downloads/"
pause >nul
exit /b 1

:run_py
py -3 -m apps.talking_table
set "table_exit=%errorlevel%"
if not "%table_exit%"=="0" pause >nul
exit /b %table_exit%

:run_python
python -m apps.talking_table
set "table_exit=%errorlevel%"
if not "%table_exit%"=="0" pause >nul
exit /b %table_exit%

:folder_error
echo The table could not start from this folder.
pause >nul
exit /b 1
