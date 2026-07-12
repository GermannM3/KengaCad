# Подписать уже собранный Setup.exe через signtool (Authenticode).
# Требуется Windows SDK (signtool).
#
# Переменные среды:
#   KENGACAD_CODESIGN_PFX   — полный путь к .pfx
#   KENGACAD_CODESIGN_PASS  — пароль PFX (если не задан — интерактивный ввод)
#
# Пример:
#   $env:KENGACAD_CODESIGN_PFX = "C:\certs\company.pfx"
#   $env:KENGACAD_CODESIGN_PASS = "secret"
#   .\installers\sign_installer.ps1

$ErrorActionPreference = "Stop"
$setup = Join-Path $PSScriptRoot "Output\KengaCAD_Professional_Setup.exe"
if (-not (Test-Path $setup)) { throw "Не найден: $setup — сначала build_installer_professional.ps1" }

function Find-SignTool {
    $cmd = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $roots = @("${env:ProgramFiles(x86)}\Windows Kits\10\bin", "${env:ProgramFiles}\Windows Kits\10\bin")
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        $found = Get-ChildItem -Path $root -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\' } |
            Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

$signExe = Find-SignTool
if (-not $signExe) { throw "signtool.exe не найден. Установите Windows SDK (Signing Tools for Desktop Apps)." }

$pfx = $env:KENGACAD_CODESIGN_PFX
if (-not $pfx -or -not (Test-Path $pfx)) { throw "Задайте KENGACAD_CODESIGN_PFX на существующий .pfx файл" }

$plainPass = $env:KENGACAD_CODESIGN_PASS
if (-not $plainPass) { $plainPass = Read-Host "Пароль PFX" }

& $signExe sign /fd SHA256 /td SHA256 /tr "http://timestamp.digicert.com" /f $pfx /p $plainPass $setup
if ($LASTEXITCODE -ne 0) { throw "signtool sign завершился с кодом $LASTEXITCODE" }
Write-Host "Подписано: $setup"
& $signExe verify /pa $setup
