@echo off
cd /d "%~dp0.."
cd GoEngineKenga
if not exist ".\cmd\kenga" (
    echo GoEngineKenga not found
    exit /b 1
)
set GOOS=windows
set GOARCH=amd64
set CGO_ENABLED=0
go build -o dist/kenga.exe ./cmd/kenga
if errorlevel 1 exit /b 1
if not exist dist mkdir dist
copy /Y dist\kenga.exe dist\kenga-windows-amd64.exe
if not exist ..\engine_bin mkdir ..\engine_bin
copy /Y dist\kenga-windows-amd64.exe ..\engine_bin\kenga.exe
echo Done. Engine: ..\engine_bin\kenga.exe
