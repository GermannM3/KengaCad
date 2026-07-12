# Сборка движка GoEngineKenga для KengaCAD (без окна Ebiten)
# Запускать из корня проекта KengaCAD или указать путь к движку

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$engineDir = Join-Path $projectRoot "GoEngineKenga"
$distDir = Join-Path $engineDir "dist"

if (-not (Test-Path $engineDir)) {
    Write-Host "Ошибка: GoEngineKenga не найден в $engineDir" -ForegroundColor Red
    exit 1
}

Write-Host "Сборка движка из $engineDir" -ForegroundColor Cyan
Set-Location $engineDir

$env:GOOS = "windows"
$env:GOARCH = "amd64"
$env:CGO_ENABLED = "0"

go build -o "dist/kenga.exe" ./cmd/kenga
if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка сборки" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $distDir | Out-Null
Copy-Item "dist/kenga.exe" "dist/kenga-windows-amd64.exe" -Force

# Копируем в engine_bin проекта
$engineBin = Join-Path $projectRoot "engine_bin"
New-Item -ItemType Directory -Force -Path $engineBin | Out-Null
Copy-Item "dist/kenga-windows-amd64.exe" (Join-Path $engineBin "kenga.exe") -Force

Write-Host ("Готово. Движок: " + (Join-Path $engineBin "kenga.exe")) -ForegroundColor Green
