; Фирменный установщик KengaCAD
; Приложение + движок в одном EXE

[Setup]
AppName=KengaCAD
AppVersion=1.0.0
AppPublisher=KengaCAD Team
AppPublisherURL=https://github.com/GermannM3/KengaCAD
AppSupportURL=https://github.com/GermannM3/KengaCAD
AppUpdatesURL=https://github.com/GermannM3/KengaCAD
DefaultDirName={autopf}\KengaCAD
DefaultGroupName=KengaCAD
OutputDir=dist
OutputBaseFilename=KengaCAD_Setup
Compression=lzma2
SolidCompression=yes
LZMAUseSeparateProcess=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=no
UninstallDisplayIcon={app}\KengaCAD.exe
VersionInfoCompany=KengaCAD Team
VersionInfoDescription=KengaCAD — CAD для траекторий роботов
VersionInfoProductName=KengaCAD
VersionInfoProductVersion=1.0.0
SetupIconFile="assets\logo.ico"
WizardImageFile="installer_assets\WizardImage.bmp"
WizardSmallImageFile="installer_assets\WizardSmallImage.bmp"
; Закрыть KengaCAD при переустановке, чтобы заменить файлы
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать иконку на рабочем столе"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
Source: "dist\KengaCAD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs overwritereadonly

[Icons]
Name: "{group}\KengaCAD"; Filename: "{app}\KengaCAD.exe"; Comment: "KengaCAD"
Name: "{group}\Удалить KengaCAD"; Filename: "{uninstallexe}"
Name: "{commondesktop}\KengaCAD"; Filename: "{app}\KengaCAD.exe"; Tasks: desktopicon; Comment: "KengaCAD"

[Run]
Filename: "{app}\KengaCAD.exe"; Description: "Запустить KengaCAD"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\KengaCAD"
