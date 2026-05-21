; =====================================================
;  Cortex Otomasyon - Windows Installer (Inno Setup 6+)
; =====================================================
;  Bu script CortexDashboard.exe + Java framework
;  + Python ML modeli + chromedriver'i tek bir
;  Windows installer halinde paketler.
;
;  Derleme:
;    iscc installer\CortexSetup.iss
;  Cikti:
;    installer\out\CortexSetup-x.y.z.exe
; =====================================================

#define MyAppName "Cortex Otomasyon Dashboard"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Bilge Adam"
#define MyAppURL "https://cortex-test.bgtsai.com/"
#define MyAppExeName "CortexDashboard.exe"

[Setup]
AppId={{F2C0E3E6-9D9E-4B1D-9E4A-CB1D6B8E1A77}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\Cortex\Dashboard
DefaultGroupName=Cortex Otomasyon
DisableProgramGroupPage=yes
OutputDir=out
OutputBaseFilename=CortexSetup-{#MyAppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
LicenseFile=..\LICENSE.txt
SetupIconFile=cortex.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";   Description: "Masaustu kisayolu olustur"; GroupDescription: "Ek gorevler:"
Name: "quicklaunchicon"; Description: "Hizli baslat kisayolu"; GroupDescription: "Ek gorevler:"; Flags: unchecked
Name: "autostart";     Description: "Windows aciliminda otomatik baslat"; GroupDescription: "Ek gorevler:"; Flags: unchecked

[Files]
; --- Dashboard (PyInstaller cikti klasoru) ---
Source: "..\dist\CortexDashboard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; --- Java framework kaynagi (test koshumu icin) ---
Source: "..\src\*";          DestDir: "{app}\framework\src";       Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\pom.xml";        DestDir: "{app}\framework";           Flags: ignoreversion
Source: "..\python_server\*";DestDir: "{app}\framework\python_server"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dashboard\*";    DestDir: "{app}\framework\dashboard"; Flags: ignoreversion recursesubdirs createallsubdirs

; --- README / lisans / .env example ---
Source: "..\README.md";      DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "..\.env.example";   DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE.txt";    DestDir: "{app}"; Flags: ignoreversion

; --- Onemli: JRE ve Maven runtime'larini Files'a ekleyin ---
; Pre-paketlemek isterseniz:
;   - jre/         (Adoptium Temurin 17 portable)
;   - maven/       (apache-maven-3.x portable)
; Aciklamali sablonlar:
;Source: "runtime\jre\*";   DestDir: "{app}\jre";   Flags: ignoreversion recursesubdirs createallsubdirs
;Source: "runtime\maven\*"; DestDir: "{app}\maven"; Flags: ignoreversion recursesubdirs createallsubdirs
;Source: "runtime\chromedriver.exe"; DestDir: "{app}\drivers"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";        Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";  Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; \
    Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "CortexDashboard"; \
    ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Cortex Dashboard'u simdi baslat"; \
    Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  // Burada JRE/Python varligi gibi on-kosullari kontrol edebilirsiniz.
end;
