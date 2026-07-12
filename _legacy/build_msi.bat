@echo off
REM Улучшенный скрипт для создания MSI установщика KengaCAD

echo Подготовка к созданию MSI установщика...

REM Проверяем, установлен ли WiX Toolset
candle.exe -? >nul 2>&1
if errorlevel 1 (
    echo WiX Toolset не установлен или не добавлен в PATH.
    echo Установите WiX Toolset из https://wixtoolset.org/releases/
    echo Или используйте create_msi_installer.bat для автоматической установки.
    pause
    exit /b 1
)

REM Проверяем, существует ли файл Product.wxs
if not exist "Product.wxs" (
    echo Файл Product.wxs не найден.
    echo Создание стандартного файла Product.wxs...
    
    REM Создаем стандартный файл Product.wxs
    echo ^<?xml version="1.0" encoding="UTF-8"?^> > Product.wxs
    echo ^<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi"^> >> Product.wxs
    echo   ^<?define ProductVersion = "1.0.0"?^> >> Product.wxs
    echo   ^<?define ProductUpgradeCode = "12345678-1234-1234-1234-123456789012"?^> >> Product.wxs
    echo. >> Product.wxs
    echo   ^<Product Id="*" ^> >> Product.wxs
    echo            Name="KengaCAD" ^> >> Product.wxs
    echo            Language="1033" ^> >> Product.wxs
    echo            Version="$(var.ProductVersion)" ^> >> Product.wxs
    echo            Manufacturer="KengaCAD Development Team" ^> >> Product.wxs
    echo            UpgradeCode="$(var.ProductUpgradeCode)"^> >> Product.wxs
    echo. >> Product.wxs
    echo     ^<Package Id="*"^> >> Product.wxs
    echo              Keywords="Installer"^> >> Product.wxs
    echo              Description="KengaCAD Installer"^> >> Product.wxs
    echo              Comments="CAD-программа для настройки траекторий роботов"^> >> Product.wxs
    echo              Manufacturer="KengaCAD Development Team"^> >> Product.wxs
    echo              InstallerVersion="500"^> >> Product.wxs
    echo              Languages="1033"^> >> Product.wxs
    echo              Compressed="yes"^> >> Product.wxs
    echo              SummaryCodepage="1251"^> >> Product.wxs
    echo              InstallScope="perMachine" /^> >> Product.wxs
    echo. >> Product.wxs
    echo     ^<MajorUpgrade DowngradeErrorMessage="A newer version of [ProductName] is already installed." /^> >> Product.wxs
    echo     ^<MediaTemplate EmbedCab="yes" /^> >> Product.wxs
    echo. >> Product.wxs
    echo     ^<!-- Иконка продукта --> >> Product.wxs
    echo     ^<Icon Id="ProductIcon" SourceFile="assets\\logo.png" /^> >> Product.wxs
    echo     ^<Property Id="ARPPRODUCTICON" Value="ProductIcon" /^> >> Product.wxs
    echo. >> Product.wxs
    echo     ^<Feature Id="ProductFeature" Title="KengaCAD" Level="1"^> >> Product.wxs
    echo       ^<ComponentGroupRef Id="ProductComponents" /^> >> Product.wxs
    echo       ^<ComponentRef Id="ApplicationShortcut" /^> >> Product.wxs
    echo       ^<ComponentRef Id="ApplicationRegistryEntries" /^> >> Product.wxs
    echo     ^</Feature^> >> Product.wxs
    echo   ^</Product^> >> Product.wxs
    echo. >> Product.wxs
    echo   ^<Fragment^> >> Product.wxs
    echo     ^<Directory Id="TARGETDIR" Name="SourceDir"^> >> Product.wxs
    echo       ^<Directory Id="ProgramFiles64Folder"^> >> Product.wxs
    echo         ^<Directory Id="INSTALLFOLDER" Name="KengaCAD"^> >> Product.wxs
    echo           ^<Component Id="ApplicationRegistryEntries" Guid="PUT-GUID-HERE-1"^> >> Product.wxs
    echo             ^<RegistryValue Root="HKCU" Key="SOFTWARE\\[Manufacturer]\\[ProductName]" Name="installed" Type="integer" Value="1" KeyPath="yes" /^> >> Product.wxs
    echo           ^</Component^> >> Product.wxs
    echo         ^</Directory^> >> Product.wxs
    echo       ^</Directory^> >> Product.wxs
    echo       ^<Directory Id="ProgramMenuFolder"^> >> Product.wxs
    echo         ^<Directory Id="ApplicationProgramsFolder" Name="KengaCAD" /^> >> Product.wxs
    echo       ^</Directory^> >> Product.wxs
    echo     ^</Directory^> >> Product.wxs
    echo   ^</Fragment^> >> Product.wxs
    echo. >> Product.wxs
    echo   ^<Fragment^> >> Product.wxs
    echo     ^<ComponentGroup Id="ProductComponents" Directory="INSTALLFOLDER"^> >> Product.wxs
    echo       ^<!-- Компоненты будут добавлены автоматически через скрипт --> >> Product.wxs
    echo     ^</ComponentGroup^> >> Product.wxs
    echo   ^</Fragment^> >> Product.wxs
    echo. >> Product.wxs
    echo   ^<Fragment^> >> Product.wxs
    echo     ^<Component Id="ApplicationShortcut" Directory="ApplicationProgramsFolder" Guid="PUT-GUID-HERE-2"^> >> Product.wxs
    echo       ^<Shortcut Id="ApplicationStartMenuShortcut" ^>> Product.wxs
    echo                 Name="KengaCAD" ^>> Product.wxs
    echo                 Description="CAD-программа для настройки траекторий роботов" ^>> Product.wxs
    echo                 Target="[#KengaCAD.exe]" ^>> Product.wxs
    echo                 WorkingDirectory="INSTALLFOLDER"^> >> Product.wxs
    echo         ^<Icon Id="ProductIcon" /^> >> Product.wxs
    echo       ^</Shortcut^> >> Product.wxs
    echo       ^<RemoveFolder Id="CleanUpShortCut" Directory="ApplicationProgramsFolder" On="uninstall"/^> >> Product.wxs
    echo       ^<RegistryValue Root="HKCU" Key="Software\\[Manufacturer]\\[ProductName]" Name="installed" Type="integer" Value="1" KeyPath="yes"/^> >> Product.wxs
    echo     ^</Component^> >> Product.wxs
    echo   ^</Fragment^> >> Product.wxs
    echo ^</Wix^> >> Product.wxs
    
    echo Файл Product.wxs создан.
)

REM Проверяем, существует ли директория assets и файл logo.png
if not exist "assets" (
    mkdir assets
    echo Created assets directory
)

if not exist "assets\logo.png" (
    REM Создаем placeholder для логотипа
    echo This is a placeholder for logo.png > assets\logo.txt
    echo Created logo placeholder. Replace with actual logo.png file.
)

REM Собираем приложение
echo Сборка приложения...
if not exist "dist\KengaCAD" (
    python build_scripts\build_windows.py
    if errorlevel 1 (
        echo Ошибка при сборке приложения
        pause
        exit /b 1
    )
) else (
    echo Приложение уже собрано, пропускаем сборку
)

REM Генерируем компоненты WiX
echo Генерация компонентов WiX...
if exist "build_scripts\generate_wix_components.py" (
    python build_scripts\generate_wix_components.py
    if errorlevel 1 (
        echo Ошибка при генерации компонентов WiX, используем стандартные
    )
) else (
    echo Скрипт генерации компонентов не найден
)

REM Компилируем WXS в WIXOBJ
echo Компиляция Product.wxs...
candle.exe Product.wxs -out Product.wixobj
if errorlevel 1 (
    echo Ошибка при компиляции Product.wxs
    pause
    exit /b 1
)

REM Линкуем в MSI
echo Линковка MSI файла...
light.exe Product.wixobj -ext WixUIExtension -ext WixUtilExtension -out KengaCAD.msi
if errorlevel 1 (
    echo Ошибка при линковке MSI файла
    pause
    exit /b 1
)

REM Перемещаем MSI в папку installers
if not exist "installers" (
    mkdir installers
)
move /Y KengaCAD.msi installers\

echo.
echo MSI установщик успешно создан: installers\KengaCAD.msi
echo Установщик готов к использованию!
echo.
echo Для установки запустите: installers\KengaCAD.msi
pause