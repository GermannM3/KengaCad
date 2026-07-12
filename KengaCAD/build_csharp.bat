@echo off
chcp 65001 >nul
setlocal
set "PROJECT_DIR=%~dp0"
set "OUTPUT=%PROJECT_DIR%bin\Release\net8.0-windows"
set "PUBLISH=%PROJECT_DIR%publish"

echo [1/3] Сборка Release...
dotnet build -c Release
if errorlevel 1 exit /b 1

echo [2/3] Публикация (single-file optional)...
if not exist "%PUBLISH%" mkdir "%PUBLISH%"
dotnet publish -c Release -o "%PUBLISH%" --no-build
if errorlevel 1 exit /b 1

echo [3/3] Копирование config и assets в publish...
xcopy /E /Y "%PROJECT_DIR%config" "%PUBLISH%\config\" >nul 2>&1
if exist "%PROJECT_DIR%assets" xcopy /E /Y "%PROJECT_DIR%assets" "%PUBLISH%\assets\" >nul 2>&1

echo.
echo Сборка завершена.
echo Исполняемый файл: %PUBLISH%\KengaCAD.exe
echo.
echo Для создания MSI установщика установите WiX Toolset и выполните:
echo   cd "%PROJECT_DIR%"
echo   candle -dPublishDir="%PUBLISH%" -dConfiguration=Release KengaCAD.wxs
echo   light -out KengaCAD_Setup.msi KengaCAD.wixobj
echo.
endlocal
