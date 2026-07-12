; Установщик KengaCAD Professional (C# WPF)
; Собирается после: dotnet publish -c Release -o ..\KengaCAD\publish
;
; Подпись Authenticode (снимает блокировки Smart App Control / SmartScreen у пользователей):
; 1) В Inno: Tools → Configure Sign Tools — см. CodeSigning.example.ini
; 2) Раскомментируйте SignTool и SignedUninstaller ниже и укажите имя своего инструмента.
; 3) Либо подпишите готовый Setup.exe скриптом sign_installer.ps1 (переменные среды).

[Setup]
AppName=KengaCAD Professional
AppVersion=2.2.0
AppPublisher=KengaCAD Team
AppPublisherURL=https://github.com/GermannM3/KengaCad
AppSupportURL=https://github.com/GermannM3/KengaCad
AppUpdatesURL=https://github.com/GermannM3/KengaCad/releases
DefaultDirName={autopf}\KengaCAD Professional
DefaultGroupName=KengaCAD Professional
OutputDir=Output
OutputBaseFilename=KengaCAD_Professional_Setup
LicenseFile=..\LICENSE.txt
InfoBeforeFile=install_info_before_ru.txt
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
VersionInfoDescription=KengaCAD Professional — CAD/CAM для роботов
VersionInfoProductName=KengaCAD Professional
VersionInfoProductVersion=2.1.0.0
SetupIconFile=logo.ico
CloseApplications=yes
CloseApplicationsFilter=*KengaCAD*
; Резерв места на диске (в КБ) — ~200 МБ поверх расчёта по файлам; соответствует self-contained .NET 8 + WPF
ExtraDiskSpaceRequired=204800

; Раскомментируйте после настройки Sign Tool в Inno (имя должно совпадать):
;SignTool=signtool
;SignedUninstaller=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать иконку на рабочем столе"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
Source: "..\KengaCAD\publish\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\KengaCAD Professional"; Filename: "{app}\KengaCAD.exe"; Comment: "KengaCAD Professional"
Name: "{group}\Удалить KengaCAD Professional"; Filename: "{uninstallexe}"
Name: "{commondesktop}\KengaCAD Professional"; Filename: "{app}\KengaCAD.exe"; Tasks: desktopicon; Comment: "KengaCAD Professional"

[Run]
Filename: "{app}\KengaCAD.exe"; Description: "Запустить KengaCAD Professional"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
