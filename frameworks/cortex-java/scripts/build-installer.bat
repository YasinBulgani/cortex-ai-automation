@echo off
REM =====================================================
REM  Cortex Otomasyon - Full Windows Installer Build
REM =====================================================
REM  Tek seferde sirasiyla:
REM    1) Python ortamini hazirla
REM    2) PyInstaller ile CortexDashboard.exe uret
REM    3) Inno Setup ile CortexSetup-x.y.z.exe uret
REM
REM  Onkosullar (Windows uzerinde):
REM    - Python 3.10+
REM    - Inno Setup 6 (https://jrsoftware.org/isdl.php)
REM    - JDK 17 + Maven (test framework calistirmak icin)
REM =====================================================

setlocal
cd /d "%~dp0\.."

echo [1/3] Python ortami hazirlaniyor...
if not exist .venv (python -m venv .venv)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r python_server\requirements.txt
python -m pip install pyinstaller==6.6.0

echo [2/3] PyInstaller ile CortexDashboard.exe uretiliyor...
pyinstaller --clean --noconfirm installer\launcher.spec
if errorlevel 1 (
  echo HATA: PyInstaller basarisiz.
  exit /b 1
)

echo [3/3] Inno Setup ile installer uretiliyor...
where iscc >nul 2>&1
if errorlevel 1 (
  echo UYARI: 'iscc' PATH'te yok. Inno Setup'i (https://jrsoftware.org/isdl.php) kurun
  echo ve "C:\Program Files (x86)\Inno Setup 6" yolunu PATH'e ekleyin.
  echo PyInstaller cikti hazir: dist\CortexDashboard\CortexDashboard.exe
  exit /b 1
)
iscc installer\CortexSetup.iss
if errorlevel 1 (
  echo HATA: Inno Setup basarisiz.
  exit /b 1
)

echo.
echo === BASARILI ===
echo Installer: installer\out\CortexSetup-*.exe
echo Standalone: dist\CortexDashboard\CortexDashboard.exe

endlocal
