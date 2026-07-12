@echo off
REM Сборка KengaCAD Professional на C# WPF

echo ============================================================
echo KengaCAD Professional v2.0.0 - Сборка
echo ============================================================
echo.

REM Проверка .NET SDK
dotnet --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ОШИБКА: .NET SDK не найден!
    echo.
    echo Установите .NET 8.0 SDK:
    echo https://dotnet.microsoft.com/download/dotnet/8.0
    echo.
    pause
    exit /b 1
)

echo Найден .NET SDK
echo.

REM Переход в директорию проекта
cd /d "%~dp0KengaCAD"

REM Очистка
echo Очистка...
dotnet clean

REM Восстановление пакетов
echo Восстановление пакетов...
dotnet restore

REM Сборка Release
echo Сборка Release версии...
dotnet publish -c Release -r win-x64 --self-contained true -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ОШИБКА сборки!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo Сборка завершена успешно!
echo ============================================================
echo.
echo Исполняемый файл: bin\Release\net8.0-windows\win-x64\publish\KengaCAD.exe
echo.

REM Копирование конфигурации
echo Копирование конфигурационных файлов...
mkdir "bin\Release\net8.0-windows\win-x64\publish\config" 2>nul
copy "..\config\*.json" "bin\Release\net8.0-windows\win-x64\publish\config\" 2>nul

REM Копирование assets
echo Копирование ресурсов...
mkdir "bin\Release\net8.0-windows\win-x64\publish\assets" 2>nul
copy "..\assets\*.*" "bin\Release\net8.0-windows\win-x64\publish\assets\" 2>nul

echo.
dir /b "bin\Release\net8.0-windows\win-x64\publish\*.exe"
echo.
pause
