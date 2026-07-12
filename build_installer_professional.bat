@echo off
setlocal EnableDelayedExpansion
set "ROOT=%~dp0"
set "DOTNET_CLI_UI_LANGUAGE=en"
set "PROJECT=%ROOT%KengaCAD"
set "PUBLISH=%PROJECT%\publish"
set "ISCC="
set "EXITCODE=0"

if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" (
    echo [WARN] Inno Setup 6 not found. Publish only. Install from https://jrsoftware.org/isdl.php
    set "SKIP_INNO=1"
) else (
    set "SKIP_INNO=0"
)

echo [1/3] Publishing KengaCAD Professional (self-contained win-x64)...
pushd "%PROJECT%"
if exist "%PUBLISH%" rmdir /S /Q "%PUBLISH%"
dotnet publish -c Release -o publish -r win-x64 --self-contained true -p:PublishSingleFile=false -p:IncludeNativeLibrariesForSelfExtract=true --nologo -v q
if errorlevel 1 (
    popd
    echo ERROR: Publish failed.
    exit /b 1
)

if not exist "%PUBLISH%\config" mkdir "%PUBLISH%\config"
if exist "%PROJECT%\config\*.json" xcopy /Y "%PROJECT%\config\*.json" "%PUBLISH%\config\" >nul
if not exist "%PUBLISH%\assets" mkdir "%PUBLISH%\assets"
if exist "%PROJECT%\assets\*" xcopy /E /Y "%PROJECT%\assets\*" "%PUBLISH%\assets\" >nul 2>nul
popd

if "%SKIP_INNO%"=="0" (
    echo [2/3] Building installer (Inno Setup)...
    pushd "%ROOT%installers"
    "%ISCC%" "KengaCAD_Professional.iss"
    set EXITCODE=!errorlevel!
    popd
    echo [3/3] Done.
    if !EXITCODE! equ 0 (
        echo Installer: %ROOT%installers\Output\KengaCAD_Professional_Setup.exe
    ) else (
        echo ERROR: Installer build failed.
    )
) else (
    set EXITCODE=0
    echo [2/3] Skipped (no Inno Setup).
    echo Run: %PUBLISH%\KengaCAD.exe
)
endlocal & exit /b !EXITCODE!
