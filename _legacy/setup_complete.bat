@echo off
REM Финальный скрипт для подготовки KengaCAD к работе

echo Подготовка KengaCAD к установке и запуску...
echo.

echo 1. Проверка Python...
python --version
if errorlevel 1 (
    echo ERROR: Python не установлен. Установите Python 3.8+
    pause
    exit /b 1
)
echo OK: Python установлен
echo.

echo 2. Установка зависимостей Python...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Ошибка при установке зависимостей
    pause
    exit /b 1
)
echo OK: Зависимости установлены
echo.

echo 3. Создание исполняемого файла приложения...
if not exist "dist\KengaCAD.exe" (
    echo Создание исполняемого файла...
    python -m PyInstaller --onefile --windowed --name KengaCAD ^
        --add-data "ui;ui" ^
        --add-data "engine;engine" ^
        --add-data "robot;robot" ^
        --add-data "cad;cad" ^
        --add-data "config;config" ^
        --hidden-import=PyQt6 ^
        --hidden-import=websockets ^
        --hidden-import=ezdxf ^
        main.py
    if errorlevel 1 (
        echo ERROR: Ошибка при создании исполняемого файла
        pause
        exit /b 1
    )
    echo OK: Исполняемый файл создан
) else (
    echo Исполняемый файл уже существует
)
echo.

echo 4. Подготовка установщика Windows (Inno Setup)...
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    echo Inno Setup найден. Создание установщика...
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /Q installers\kengacad_installer_fixed.iss
    if errorlevel 1 (
        echo WARNING: Ошибка при создании установщика Inno Setup
        echo Убедитесь, что Inno Setup установлен правильно
    ) else (
        echo OK: Установщик Windows создан
    )
) else (
    echo ВНИМАНИЕ: Inno Setup не найден
    echo Установите Inno Setup для создания установщика Windows
    echo Скачать можно по адресу: http://www.jrsoftware.org/isdl.php
)
echo.

echo 5. Подготовка установочных пакетов для Linux...
echo Файлы для Linux пакетов созданы в соответствующих поддиректориях installers/
echo Для создания пакетов выполните соответствующие команды в Linux:
echo   - Для DEB: dpkg-deb --build installers/deb_package/kengacad-1.0.0
echo   - Для RPM: rpmbuild -bb installers/rpm_package/SPECS/kengacad.spec
echo   - Для Arch: makepkg -si в директории installers/arch_package
echo.

echo 6. Установка движка Kenga...
echo Для полноценной работы KengaCAD требуется движок Kenga.
echo Установите его отдельно из репозитория: https://github.com/GermannM3/GoEngineKenga
echo.

echo Установка KengaCAD подготовлена!
echo.
echo Для запуска приложения:
echo   - Windows: запустите dist\KengaCAD.exe
echo   - Или установите через установщик: installers\Output\KengaCAD_Setup.exe (если создан)
echo.
echo Для запуска с визуализацией:
echo   1. Запустите движок Kenga: kenga run --project . --scene scene.json --ws-port 127.0.0.1:7777
echo   2. Запустите KengaCAD
echo.
pause