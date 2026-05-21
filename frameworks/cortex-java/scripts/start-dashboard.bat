@echo off
REM ==============================================
REM  Cortex Dashboard - Windows starter
REM  Dev kullanim icin. Production'da CortexDashboard.exe kullanin.
REM ==============================================

setlocal
cd /d "%~dp0\.."

where python >nul 2>&1
if errorlevel 1 (
  echo HATA: Python kurulu degil. https://www.python.org adresinden Python 3.10+ indirin.
  pause
  exit /b 1
)

if not exist .venv (
  echo Creating virtual environment...
  python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
python -m pip install -r python_server\requirements.txt

set DASHBOARD_PORT=5001
start "" http://localhost:%DASHBOARD_PORT%
python python_server\flask_api.py

endlocal
