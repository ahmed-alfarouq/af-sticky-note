; Inno Setup Script for Daily Sticky
; Builds an installation package deploying PyInstaller onedir output.
; - Per-user installation (no admin rights); the user's SQLite database is never touched.
; - Detects an installed copy and updates it in place (see [Code]).
; - The version is passed in by packaging\build_windows.ps1 (/DMyAppVersion=X.Y.Z), which reads
;   it from APP_VERSION in app\config\settings.py: that file is the only place to change it.

#ifndef MyAppVersion
  #error MyAppVersion is not defined. Build with packaging\build_windows.ps1, or pass /DMyAppVersion=X.Y.Z to ISCC.
#endif

#define MyAppName "Daily Sticky"
#define MyAppPublisher "Daily Sticky Project"
#define MyAppExeName "DailySticky.exe"
#define RunKey "Software\Microsoft\Windows\CurrentVersion\Run"

[Setup]
; Unique application GUID. NEVER change it: it is how an installed copy is recognised on update.
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
; An update reuses the folder of the installed copy, so the page is skipped then
UsePreviousAppDir=yes
DisableDirPage=auto
DisableProgramGroupPage=auto
UninstallDisplayIcon={app}\{#MyAppExeName}
; The app hides to the tray instead of closing, so setup stops it itself (see PrepareToInstall)
CloseApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.NewerInstalled=A newer version of {#MyAppName} (%1) is already installed, so this setup (version %2) will not replace it.%n%nTo go back to this version, uninstall the newer one first. Your tasks are kept when you uninstall.
english.SameVersionInstalled=Version %1 of {#MyAppName} is already installed.%n%nDo you want to reinstall it?
english.UpdateWelcome=Setup will update {#MyAppName} from version %1 to version %2.%n%nYour tasks and settings are kept. If {#MyAppName} is running, setup will close it and start it again when it finishes.
english.ReinstallWelcome=Setup will reinstall {#MyAppName} version %1.%n%nYour tasks and settings are kept. If {#MyAppName} is running, setup will close it and start it again when it finishes.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
; Offered on a fresh install only. An update never changes the user's choice, which they
; can also change from the app's settings.
Name: "autostart"; Description: "Start Daily Sticky automatically with Windows"; GroupDescription: "Windows Integration:"; Check: not IsUpgrade

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
; Fresh install with the autostart task chosen: per-user autostart under the HKCU Run key
Root: HKCU; Subkey: "{#RunKey}"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart
; Update: only refresh an entry that already exists, so it keeps pointing at this install
Root: HKCU; Subkey: "{#RunKey}"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Check: RunEntryExists

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; The app lives in the tray: stop it so its files can be removed
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; RunOnceId: "StopDailySticky"

[Code]
var
  InstalledVersion: String;

{ The uninstall key Inno Setup writes for this AppId (ExpandConstant turns the doubled brace into one). }
function UninstallKeyPath(): String;
begin
  Result := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1');
end;

{ The version of the installed copy, or '' when none is installed. }
function ReadInstalledVersion(): String;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, UninstallKeyPath(), 'DisplayVersion', Result) then
    if not RegQueryStringValue(HKEY_LOCAL_MACHINE, UninstallKeyPath(), 'DisplayVersion', Result) then
      Result := '';
end;

{ Removes and returns the first number of a dotted version ("0.6.1" -> 0, leaving "6.1"). }
function TakeNumber(var Version: String): Integer;
var
  Dot: Integer;
begin
  Dot := Pos('.', Version);
  if Dot = 0 then
  begin
    Result := StrToIntDef(Version, 0);
    Version := '';
  end
  else
  begin
    Result := StrToIntDef(Copy(Version, 1, Dot - 1), 0);
    Delete(Version, 1, Dot);
  end;
end;

{ -1 when A is older than B, 0 when equal, 1 when newer. }
function CompareVersions(A, B: String): Integer;
var
  X, Y: Integer;
begin
  Result := 0;
  while (Result = 0) and ((A <> '') or (B <> '')) do
  begin
    X := TakeNumber(A);
    Y := TakeNumber(B);
    if X < Y then
      Result := -1
    else if X > Y then
      Result := 1;
  end;
end;

function IsUpgrade(): Boolean;
begin
  Result := InstalledVersion <> '';
end;

function RunEntryExists(): Boolean;
begin
  Result := RegValueExists(HKEY_CURRENT_USER, '{#RunKey}', '{#MyAppName}');
end;

function InitializeSetup(): Boolean;
var
  Order: Integer;
begin
  Result := True;
  InstalledVersion := ReadInstalledVersion();
  if not IsUpgrade() then
    Exit;

  Order := CompareVersions(InstalledVersion, '{#MyAppVersion}');
  if Order > 0 then
  begin
    { Never replace a newer copy with an older one. }
    SuppressibleMsgBox(FmtMessage(CustomMessage('NewerInstalled'), [InstalledVersion, '{#MyAppVersion}']),
      mbError, MB_OK, IDOK);
    Result := False;
  end
  else if Order = 0 then
    Result := SuppressibleMsgBox(FmtMessage(CustomMessage('SameVersionInstalled'), [InstalledVersion]),
      mbConfirmation, MB_YESNO, IDYES) = IDYES;
end;

procedure InitializeWizard();
begin
  if not IsUpgrade() then
    Exit;

  if CompareVersions(InstalledVersion, '{#MyAppVersion}') = 0 then
    WizardForm.WelcomeLabel2.Caption := FmtMessage(CustomMessage('ReinstallWelcome'), [InstalledVersion])
  else
    WizardForm.WelcomeLabel2.Caption := FmtMessage(CustomMessage('UpdateWelcome'), [InstalledVersion, '{#MyAppVersion}']);
end;

{ The app hides to the tray when its window is closed, so it has to be stopped to replace its files. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(600);
  Result := '';
end;
