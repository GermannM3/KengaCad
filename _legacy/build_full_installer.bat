@echo off
REM Скрипт сборки полноценного установщика KengaCAD

echo ============================================================
echo KengaCAD v2.0.0 - Сборка установщика
echo ============================================================
echo.

REM Проверка наличия Inno Setup
set ISCC_PATH=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set ISCC_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set ISCC_PATH="C:\Program Files\Inno Setup 6\ISCC.exe"
)

if "%ISCC_PATH%"=="" (
    echo ОШИБКА: Inno Setup 6 не найден!
    echo.
    echo Установите Inno Setup 6:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

echo Найден Inno Setup: %ISCC_PATH%
echo.

REM Переход в директорию установщика
cd /d "%~dp0installers"

REM Сборка установщика
echo Сборка установщика...
%ISCC_PATH% KengaCAD_Full.iss

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ОШИБКА сборки установщика!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Сборка завершена успешно!
echo ============================================================
echo.
echo Установщик находится в: %~dp0final_installers\
echo.
dir /b ..\final_installers\*.exe
echo.
pause
