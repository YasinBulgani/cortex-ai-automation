; =====================================================
;  Cortex AI Automation - Windows Installer (Inno Setup 6+)
;
;  Bu installer:
;    • Proje dosyalarını C:\Program Files\Cortex'e kopyalar
;    • install-deps.ps1'i çağırır (Java, Python, Maven, Playwright)
;    • Masaüstü/Start Menu kısayolu oluşturur
;    • Dashboard'u başlatır
;
;  Derleme:    iscc installer\windows\CortexSetup.iss
;  Çıktı:      installer\out\CortexSetup-1.0.0.exe
; =====================================================

#define MyAppName "Cortex AI Automation"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Bilge Adam"
#define MyAppURL "https://cortex-test.bgtsai.com/"
#define MyAppExeName "Cortex-Baslat.bat"
#define MyAppId "{{F2C0E3E6-9D9E-4B1D-9E4A-CB1D6B8E1A77}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}

DefaultDirName={autopf}\Cortex_Ai_Automation
DefaultGroupName=Cortex AI Automation
DisableProgramGroupPage=yes
OutputDir=..\out
OutputBaseFilename=CortexSetup-{#MyAppVersion}-Windows
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

LicenseFile=..\..\LICENSE.txt
; Custom installer icon — uncomment after dropping cortex.ico in this folder
; SetupIconFile=cortex.ico
; UninstallDisplayIcon={app}\installer\windows\cortex.ico
; Wizard images — use Inno Setup defaults (file names changed in 6.5+)
ShowLanguageDialog=auto
DisableWelcomePage=no

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "Masaustu kisayolu olustur";         GroupDescription: "Ek gorevler:"
Name: "startmenu";      Description: "Baslat menusune ekle";              GroupDescription: "Ek gorevler:"; Flags: checkablealone
Name: "quicklaunchicon";Description: "Hizli baslat kisayolu";             GroupDescription: "Ek gorevler:"; Flags: unchecked
Name: "autostart";      Description: "Windows acilirken otomatik baslat"; GroupDescription: "Ek gorevler:"; Flags: unchecked

[Files]
; --- Java framework under framework/ ---
Source: "..\..\framework\pom.xml";       DestDir: "{app}\framework";          Flags: ignoreversion
Source: "..\..\framework\mvnw";          DestDir: "{app}\framework";          Flags: ignoreversion
Source: "..\..\framework\mvnw.cmd";      DestDir: "{app}\framework";          Flags: ignoreversion
Source: "..\..\framework\.mvn\*";        DestDir: "{app}\framework\.mvn";     Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\framework\src\*";         DestDir: "{app}\framework\src";      Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\framework\python_server\*"; DestDir: "{app}\framework\python_server"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\framework\dashboard\*";   DestDir: "{app}\framework\dashboard"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\framework\docs\*";        DestDir: "{app}\framework\docs";     Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\..\framework\scripts\*";     DestDir: "{app}\framework\scripts";  Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "..\..\framework\recorder.properties"; DestDir: "{app}\framework";    Flags: ignoreversion
Source: "..\..\framework\.env.example";  DestDir: "{app}\framework";          Flags: ignoreversion skipifsourcedoesntexist

; --- Next.js monorepo (apps/ + packages/ + workspace configs) ---
Source: "..\..\apps\*";        DestDir: "{app}\apps";                Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Excludes: "node_modules\*,*\node_modules\*,.next\*,*\.next\*,.turbo\*,*\.turbo\*,tsconfig.tsbuildinfo"
Source: "..\..\packages\*";    DestDir: "{app}\packages";            Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist; Excludes: "node_modules\*,*\node_modules\*,.turbo\*,*\.turbo\*,dist\*,*\dist\*,tsconfig.tsbuildinfo"
Source: "..\..\package.json";  DestDir: "{app}";                     Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\turbo.json";    DestDir: "{app}";                     Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\tsconfig.base.json"; DestDir: "{app}";                Flags: ignoreversion skipifsourcedoesntexist

; --- Project root docs ---
Source: "..\..\README.md";     DestDir: "{app}";                     Flags: ignoreversion isreadme
Source: "..\..\LICENSE.txt";   DestDir: "{app}";                     Flags: ignoreversion
Source: "..\..\CHANGELOG.md";  DestDir: "{app}";                     Flags: ignoreversion skipifsourcedoesntexist

; --- Installer support files (powershell + icon) ---
Source: "install-deps.ps1";    DestDir: "{app}\installer\windows";   Flags: ignoreversion
Source: "cortex.ico";          DestDir: "{app}\installer\windows";   Flags: ignoreversion skipifsourcedoesntexist

; --- Optional: bundled portable JRE (uncomment + place files in runtime/) ---
; Source: "runtime\jre\*";   DestDir: "{app}\runtime\jre";   Flags: ignoreversion recursesubdirs createallsubdirs
; Source: "runtime\maven\*"; DestDir: "{app}\runtime\maven"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";        Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}";  Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "CortexOtomasyon"; \
    ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Run dependency installer (Java/Python/Maven/Playwright) after files are extracted
Filename: "powershell.exe"; \
    Parameters: "-ExecutionPolicy Bypass -NoProfile -File ""{app}\installer\windows\install-deps.ps1"" -InstallDir ""{app}"" -NoLaunch"; \
    StatusMsg: "Bagimliliklar kuruluyor (Java, Python, Maven, Playwright)... Bu birkac dakika surebilir."; \
    Flags: runhidden waituntilterminated

; Launch the dashboard immediately after install
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Cortex AI Automation Dashboard'u simdi baslat"; \
    Flags: nowait postinstall skipifsilent shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}\framework\.venv"
Type: filesandordirs; Name: "{app}\framework\target"
Type: filesandordirs; Name: "{app}\framework\logs"
Type: filesandordirs; Name: "{app}\web\node_modules"
Type: filesandordirs; Name: "{app}\web\.next"

[Code]
// Preflight: Inno Setup tarafında temel check'ler.
// Internet bağlantısı zorunlu (deps indirileceği için).

function IsWindows10OrLater(): Boolean;
var
  Version: TWindowsVersion;
begin
  GetWindowsVersionEx(Version);
  Result := (Version.NTPlatform) and (Version.Major >= 10);
end;

function InitializeSetup(): Boolean;
begin
  if not IsWindows10OrLater() then begin
    MsgBox('Cortex AI Automation Windows 10 veya daha yeni bir surum gerektirir.',
           mbError, MB_OK);
    Result := False;
    Exit;
  end;
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    // Allow PowerShell script execution
    // (PrivilegesRequired=lowest means we cannot modify Machine policy,
    //  but the -ExecutionPolicy Bypass on the invocation handles it)
  end;
end;
