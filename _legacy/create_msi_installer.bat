@echo off
REM Скрипт для установки WiX Toolset и создания MSI установщика для KengaCAD

echo Установка WiX Toolset...

REM Проверяем, установлен ли WiX Toolset
wix --version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo WiX Toolset уже установлен
) else (
    echo WiX Toolset не найден. Установка...
    REM Скачивание и установка WiX Toolset через Chocolatey (если доступно)
    choco --version >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        echo Установка через Chocolatey...
        choco install wixtoolset -y
    ) else (
        echo Установите WiX Toolset вручную из https://wixtoolset.org/releases/
        echo Или установите Chocolatey и повторите попытку
        pause
        exit /b 1
    )
)

REM Проверяем, установлены ли компоненты WiX
candle.exe -h >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Candle не найден. Проверьте установку WiX Toolset.
    pause
    exit /b 1
)

light.exe -h >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Light не найден. Проверьте установку WiX Toolset.
    pause
    exit /b 1
)

echo WiX Toolset установлен и готов к использованию.

REM Сборка приложения
echo Сборка KengaCAD...
python build_scripts\build_windows.py

if %ERRORLEVEL% neq 0 (
    echo Ошибка при сборке приложения
    pause
    exit /b 1
)

REM Генерация компонентов WiX
echo Генерация компонентов WiX...
python build_scripts\generate_wix_components.py

if %ERRORLEVEL% neq 0 (
    echo Ошибка при генерации компонентов WiX
    pause
    exit /b 1
)

REM Компиляция WXS файла
echo Компиляция WXS файла...
candle.exe installers\Product.wxs -out installers\

if %ERRORLEVEL% neq 0 (
    echo Ошибка при компиляции WXS файла
    pause
    exit /b 1
)

REM Линковка MSI файла
echo Линковка MSI файла...
light.exe installers\Product.wixobj -ext WixUIExtension -ext WixUtilExtension -out installers\KengaCAD.msi

if %ERRORLEVEL% neq 0 (
    echo Ошибка при линковке MSI файла
    pause
    exit /b 1
)

echo MSI установщик успешно создан: installers\KengaCAD.msi
echo Установщик готов к использованию!
pause