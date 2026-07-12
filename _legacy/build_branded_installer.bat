@echo off
chcp 65001 >nul
echo Сборка фирменного установщика KengaCAD...
echo.

python build_scripts\build_branded_installer.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo Ошибка сборки.
    pause
    exit /b 1
)

echo.
echo Установщик: dist\KengaCAD_Setup.exe
pause
