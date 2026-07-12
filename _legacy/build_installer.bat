@echo off
REM Скрипт для компиляции установщика KengaCAD с помощью Inno Setup

echo Проверка наличия Inno Setup компилятора...

REM Проверяем, установлен ли ISCC (Inno Setup Compiler)
where ISCC >nul 2>&1
if %errorlevel% neq 0 (
    echo Inno Setup не установлен или не добавлен в PATH.
    echo Скачайте и установите Inno Setup из: http://www.jrsoftware.org/isdl.php
    echo После установки убедитесь, что путь к ISCC.exe добавлен в PATH.
    echo.
    echo Альтернативно, вы можете вручную открыть installers\kengacad_installer_fixed.iss
    echo в Inno Setup Compiler и выполнить компиляцию.
    pause
    exit /b 1
)

echo Inno Setup найден. Компиляция установщика...

REM Запускаем компиляцию
ISCC.exe "installers\kengacad_installer_fixed.iss"

if %errorlevel% neq 0 (
    echo Ошибка при компиляции установщика
    pause
    exit /b 1
)

echo Установщик успешно создан!
echo Файл установщика находится в папке installers\Output
echo.
pause