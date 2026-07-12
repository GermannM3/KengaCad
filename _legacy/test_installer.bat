@echo off
REM Скрипт для тестирования установщика KengaCAD

echo Тестирование установщика KengaCAD...
echo.

REM Проверяем, что установщик существует
if not exist "dist\KengaCAD_Installer.exe" (
    echo Установщик не найден: dist\KengaCAD_Installer.exe
    echo Сначала создайте установщик с помощью create_installer_exe.py
    pause
    exit /b 1
)

echo Установщик найден: KengaCAD_Installer.exe
echo.

REM Запускаем установщик
echo Запуск установщика...
start "" "dist\KengaCAD_Installer.exe"

echo.
echo Установщик запущен. Следуйте инструкциям на экране.
echo.
echo Для проверки установки:
echo 1. После установки проверьте папку Program Files\KengaCAD
echo 2. Найдите ярлыки в меню "Пуск" и на рабочем столе
echo 3. Попробуйте запустить KengaCAD
echo.
pause