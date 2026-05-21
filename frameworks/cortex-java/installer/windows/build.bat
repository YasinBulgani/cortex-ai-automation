@echo off
REM ==========================================================
REM  Cortex Otomasyon — Windows Installer Builder
REM ==========================================================
REM  Bu script CortexSetup-VERSION-Windows.exe üretir.
REM  Gereken: Inno Setup 6+ (iscc.exe PATH'te olmalı)
REM
REM  Kullanım:
REM    installer\windows\build.bat [VERSION]
REM ==========================================================
setlocal EnableDelayedExpansion

set VERSION=%1
if "%VERSION%"=="" set VERSION=1.0.0

set SCRIPT_DIR=%~dp0
set REPO_ROOT=%SCRIPT_DIR%..\..
set OUT_DIR=%REPO_ROOT%\installer\out

echo.
echo ============================================================
echo  Cortex Otomasyon — Windows Installer v%VERSION%
echo ============================================================
echo.
echo Repo:   %REPO_ROOT%
echo Cikti:  %OUT_DIR%\CortexSetup-%VERSION%-Windows.exe
echo.

REM Check for iscc.exe
where iscc.exe >nul 2>&1
if errorlevel 1 (
    REM Try default install location
    set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if not exist !ISCC! (
        set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    if not exist !ISCC! (
        echo [HATA] Inno Setup 6 bulunamadi.
        echo        Kurulum: https://jrsoftware.org/isdl.php
        echo        Veya: winget install JRSoftware.InnoSetup
        exit /b 1
    )
) else (
    set ISCC=iscc.exe
)

REM Make sure output directory exists
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

REM Compile
echo [BUILD] Inno Setup derleniyor...
%ISCC% /DMyAppVersion=%VERSION% "%SCRIPT_DIR%CortexSetup.iss"
if errorlevel 1 (
    echo [HATA] Inno Setup derleme basarisiz.
    exit /b 1
)

echo.
echo ============================================================
echo  BASARILI
echo ============================================================
echo  Cikti: %OUT_DIR%\CortexSetup-%VERSION%-Windows.exe
echo.
echo  Test icin sag-tik / "As administrator" gerek YOK
echo  (lowest privileges, per-user kurulum).
echo.

endlocal
