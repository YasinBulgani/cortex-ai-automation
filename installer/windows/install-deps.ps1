# ============================================================
#  Cortex AI Automation — Windows Dependency Installer
# ============================================================
#  Bu PowerShell script Inno Setup [Run] section'ı tarafından
#  çağrılır. Java 17+, Python 3.10+, Playwright Chromium'u
#  otomatik kontrol eder ve kurar.
#
#  Çağrı:
#    powershell.exe -ExecutionPolicy Bypass -File install-deps.ps1 -InstallDir "C:\Program Files\Cortex"
# ============================================================
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$InstallDir,
    [switch]$NoLaunch
)

$ErrorActionPreference = 'Continue'  # don't fail-fast; report each step
$ProgressPreference     = 'SilentlyContinue'  # speed up downloads

function Log-Info ($msg)  { Write-Host "[INFO] $msg"  -ForegroundColor Cyan }
function Log-Ok   ($msg)  { Write-Host "[OK]   $msg"  -ForegroundColor Green }
function Log-Warn ($msg)  { Write-Host "[WARN] $msg"  -ForegroundColor Yellow }
function Log-Err  ($msg)  { Write-Host "[FAIL] $msg"  -ForegroundColor Red }
function Header   ($msg)  { Write-Host "`n=== $msg ===`n" -ForegroundColor Blue }

Header "Cortex AI Automation — Windows Setup"
Log-Info "Hedef:  $InstallDir"

# ── Detect winget (Windows 10 19h1+ has it) ──────────────────
$HasWinget = $null -ne (Get-Command winget -ErrorAction SilentlyContinue)

# ── 1. JAVA 17 ───────────────────────────────────────────────
function Test-Java17 {
    $cmd = Get-Command java -ErrorAction SilentlyContinue
    if (-not $cmd) { return $false }
    $verLine = (& java -version 2>&1) | Select-Object -First 1
    if ($verLine -match '"(\d+)\.') {
        return [int]$Matches[1] -ge 17
    }
    return $false
}

function Install-Java17 {
    if ($HasWinget) {
        Log-Info "winget ile Eclipse Temurin JDK 17 kuruluyor..."
        $args = @('install', '--id', 'EclipseAdoptium.Temurin.17.JDK',
                  '--silent', '--accept-package-agreements', '--accept-source-agreements')
        & winget $args
        if ($LASTEXITCODE -eq 0) {
            Log-Ok "JDK 17 kuruldu (winget)."
            # Refresh PATH from registry
            $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
            return $true
        }
        Log-Warn "winget başarısız (exit $LASTEXITCODE). Manuel indirme deneniyor..."
    }

    # Fallback: direct download from Adoptium API
    Log-Info "Adoptium Temurin 17 doğrudan indiriliyor..."
    $arch = if ([System.Environment]::Is64BitOperatingSystem) { 'x64' } else { 'x86' }
    $url  = "https://api.adoptium.net/v3/installer/latest/17/ga/windows/$arch/jdk/hotspot/normal/eclipse?project=jdk"
    $msi  = Join-Path $env:TEMP "Cortex-OpenJDK17.msi"

    try {
        Invoke-WebRequest -Uri $url -OutFile $msi -UseBasicParsing
    } catch {
        Log-Err "JDK indirilemedi: $_"
        return $false
    }

    Log-Info "MSI sessiz kuruluyor..."
    $proc = Start-Process msiexec.exe -ArgumentList @(
        '/i', "`"$msi`"",
        'ADDLOCAL=FeatureMain,FeatureEnvironment,FeatureJarFileRunWith',
        '/quiet', '/norestart'
    ) -Wait -PassThru
    Remove-Item $msi -ErrorAction SilentlyContinue
    if ($proc.ExitCode -eq 0) {
        Log-Ok "JDK 17 kuruldu (MSI)."
        $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
        return $true
    }
    Log-Err "JDK MSI kurulumu başarısız (exit $($proc.ExitCode))."
    return $false
}

Header "1/5 · Java 17 kontrolü"
if (Test-Java17) {
    $v = (& java -version 2>&1) | Select-Object -First 1
    Log-Ok "Java mevcut: $v"
} else {
    Log-Warn "Java 17 bulunamadı."
    if (-not (Install-Java17)) {
        Log-Err "Java kurulumu başarısız. https://adoptium.net adresinden manuel kurun."
        exit 1
    }
}

# ── 2. PYTHON 3.10+ ──────────────────────────────────────────
function Test-Python310 {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
    if (-not $py) { return $false }
    $verJson = & $py.Source -c "import sys, json; print(json.dumps([sys.version_info.major, sys.version_info.minor]))" 2>$null
    if (-not $verJson) { return $false }
    $arr = $verJson | ConvertFrom-Json
    return ($arr[0] -gt 3) -or ($arr[0] -eq 3 -and $arr[1] -ge 10)
}

function Install-Python {
    if ($HasWinget) {
        Log-Info "winget ile Python 3.11 kuruluyor..."
        $args = @('install', '--id', 'Python.Python.3.11',
                  '--silent', '--accept-package-agreements', '--accept-source-agreements')
        & winget $args
        if ($LASTEXITCODE -eq 0) {
            Log-Ok "Python 3.11 kuruldu (winget)."
            $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
            return $true
        }
    }

    Log-Info "python.org'dan Python 3.11 doğrudan indiriliyor..."
    $arch = if ([System.Environment]::Is64BitOperatingSystem) { 'amd64' } else { 'win32' }
    $url  = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-$arch.exe"
    $exe  = Join-Path $env:TEMP "python-installer.exe"

    try {
        Invoke-WebRequest -Uri $url -OutFile $exe -UseBasicParsing
    } catch {
        Log-Err "Python indirilemedi: $_"
        return $false
    }

    Log-Info "Python kuruluyor (sessiz)..."
    $proc = Start-Process $exe -ArgumentList @(
        '/quiet', 'InstallAllUsers=0', 'PrependPath=1',
        'Include_test=0', 'Include_launcher=1', 'Include_pip=1'
    ) -Wait -PassThru
    Remove-Item $exe -ErrorAction SilentlyContinue
    if ($proc.ExitCode -eq 0) {
        Log-Ok "Python kuruldu."
        $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
        return $true
    }
    Log-Err "Python kurulumu başarısız."
    return $false
}

Header "2/5 · Python 3.10+ kontrolü"
if (Test-Python310) {
    $v = & python --version 2>&1
    Log-Ok "Python mevcut: $v"
} else {
    if (-not (Install-Python)) {
        Log-Err "Python kurulumu başarısız."
        exit 1
    }
}

# ── 3. Maven via mvnw (project-bundled wrapper) ──────────────
Header "3/5 · Maven wrapper kontrolü"
# Detect framework/ subdir vs legacy flat layout
$FrameworkDir = Join-Path $InstallDir "framework"
if (-not (Test-Path (Join-Path $FrameworkDir "pom.xml"))) {
    $FrameworkDir = $InstallDir
}
Log-Info "Framework dizini: $FrameworkDir"
Push-Location $FrameworkDir
$mvnw = Join-Path $FrameworkDir "mvnw.cmd"
if (-not (Test-Path $mvnw)) {
    Log-Err "mvnw.cmd bulunamadı: $mvnw — paket bütün değil mi?"
    Pop-Location
    exit 1
}
Log-Info "Maven bağımlılıkları çözümleniyor (ilk seferinde 3-5 dk)..."
$mvnArgs = @('-q', '-DskipTests', 'dependency:resolve')
& $mvnw $mvnArgs
if ($LASTEXITCODE -ne 0) {
    Log-Warn "Maven dependency:resolve başarısız (exit $LASTEXITCODE). İlk koşumda çözülecek."
} else {
    Log-Ok "Maven bağımlılıkları hazır."
}

Log-Info "Playwright Chromium indiriliyor..."
& $mvnw '-q' 'exec:java' '-Dexec.mainClass=com.microsoft.playwright.CLI' '-Dexec.args=install chromium' 2>$null
if ($LASTEXITCODE -ne 0) {
    Log-Warn "Playwright kurulumu otomatik yapılamadı; ilk recorder kullanımında otomatik kurulacak."
} else {
    Log-Ok "Playwright Chromium kuruldu."
}
Pop-Location

# ── 4. Python venv + requirements ────────────────────────────
Header "4/5 · Python sanal ortam + bağımlılıklar"
Push-Location $FrameworkDir
$venv = Join-Path $FrameworkDir ".venv"
if (-not (Test-Path $venv)) {
    Log-Info ".venv oluşturuluyor: $venv"
    & python -m venv .venv
}

$pip = Join-Path $venv "Scripts\pip.exe"
$py  = Join-Path $venv "Scripts\python.exe"
& $pip install --quiet --upgrade pip
& $pip install --quiet -r (Join-Path $FrameworkDir 'python_server\requirements.txt')

# Train ML model if missing
$modelPath = Join-Path $FrameworkDir 'python_server\final_model.pkl'
if ((Test-Path (Join-Path $FrameworkDir 'python_server\train_model.py')) -and (-not (Test-Path $modelPath))) {
    Log-Info "ML modeli eğitiliyor..."
    Push-Location (Join-Path $FrameworkDir 'python_server')
    & $py train_model.py
    Pop-Location
}
Pop-Location
Log-Ok "Python ortamı hazır."

# ── 5. Create launcher .bat + desktop shortcut ───────────────
Header "5/5 · Launcher + kısayollar"
$launcher = Join-Path $InstallDir 'Cortex-Baslat.bat'
$launcherContent = @"
@echo off
title Cortex AI Automation Dashboard
cd /d "$FrameworkDir"
call .venv\Scripts\activate.bat
cd python_server
start "" http://localhost:5001
python flask_api.py
"@
Set-Content -LiteralPath $launcher -Value $launcherContent -Encoding ASCII

# Desktop shortcut
$shortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Cortex AI Automation.lnk'
$ws = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($shortcut)
$lnk.TargetPath = $launcher
$lnk.WorkingDirectory = $InstallDir
$lnk.Description = 'Cortex AI Automation Dashboard'
$ico = Join-Path $InstallDir 'installer\windows\cortex.ico'
if (Test-Path $ico) { $lnk.IconLocation = $ico }
$lnk.Save()
Log-Ok "Masaüstü kısayolu oluşturuldu."

Log-Ok "Kurulum tamamlandı."
Log-Info "Başlatmak için: çift tıklayın → Masaüstü\Cortex AI Automation"

if (-not $NoLaunch) {
    Log-Info "Dashboard başlatılıyor..."
    Start-Process $launcher
}

exit 0
