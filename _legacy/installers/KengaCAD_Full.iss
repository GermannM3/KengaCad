; KengaCAD Inno Setup Script
; Полноценный установщик с лицензией

#define MyAppName "KengaCAD"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "KengaCAD Team"
#define MyAppExeName "KengaCAD.exe"
#define MyAppURL "https://kengacad.local"

[Setup]
AppId={{A7B5C3D1-9E8F-4A2B-B6C7-D8E9F0A1B2C3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
LicenseFile=..\LICENSE.txt
InfoBeforeFile=..\docs\INSTALL_README.txt
OutputDir=..\final_installers
OutputBaseFilename=KengaCAD_{#MyAppVersion}_Setup
SetupIconFile=..\installer_assets\setup_icon.ico
WizardStyle=Modern
Compression=lzma2/max
SolidCompression=yes
WizardResizable=no
MinVersion=10.0.18362
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
SignedUninstaller=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "..\dist\KengaCAD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\KengaCAD\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\docs\INSTALL_README.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\ADVANCED_FEATURES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\COMMAND_REFERENCE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // Проверка минимальных требований
  if not IsAdminInstallMode then
  begin
    MsgBox('Для установки требуются права администратора.', mbError, MB_OK);
    Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Пост-установочные действия
    Log('KengaCAD installation completed successfully');
  end;
end;

function GetCustomSetupExitCode: Integer;
begin
  Result := 0;
end;

procedure InitializeWizard;
begin
  // Настройка приветственной страницы
  WizardForm.WelcomeLabel1.Caption := 'Добро пожаловать в мастер установки KengaCAD v2.0.0';
  WizardForm.WelcomeLabel2.Caption := 'Профессиональная CAD/CAM система для роботов'#13#10#13#10'Мастер установит KengaCAD на ваш компьютер.';
end;

[UninstallDelete]
Type: filesandordirs; Name: "{app}";
Type: files; Name: "{localappdata}\KengaCAD\config\settings.json";

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal\__pycache__";
Type: filesandordirs; Name: "{app}\_internal\ui\__pycache__";
Type: filesandordirs; Name: "{app}\_internal\cad\__pycache__";
