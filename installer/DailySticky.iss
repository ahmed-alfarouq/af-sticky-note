; Inno Setup Script for Daily Sticky
; Builds an installation package deploying PyInstaller onedir output
; Enforces per-user installation (non-admin), preserves user SQLite database,
; and implements the installer-owned default startup registration.

#define MyAppName "Daily Sticky"
#define MyAppVersion "0.5.0"
#define MyAppPublisher "Daily Sticky Project"
#define MyAppExeName "DailySticky.exe"

[Setup]
; Unique application GUID for version updates and uninstall tracking
AppId={{D37E8C21-6A18-4F92-B72F-89E3A59102B4}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist\installer
OutputBaseFilename=DailySticky-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
; Per-user install: does not require administrative elevation or UAC prompts
PrivilegesRequired=lowest
DisableDirPage=auto
DisableProgramGroupPage=auto
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
; Installer-owned startup task: checked by default per Phase 5H-B architectural decision
Name: "autostart"; Description: "Start Daily Sticky automatically with Windows"; GroupDescription: "Windows Integration:"

[Files]
; Copy all files produced by PyInstaller onedir distribution
Source: "..\dist\DailySticky\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: User SQLite database is stored in %LOCALAPPDATA%\DailySticky\daily_sticky.db
; and is NEVER deployed or overwritten by this installer.

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Installer-owned per-user autostart registration under HKCU Run key
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
