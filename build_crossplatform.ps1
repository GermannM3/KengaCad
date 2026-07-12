# Сборка portable-пакетов Linux/macOS (PyQt legacy + конфиги из KengaCAD Professional)
# AppImage/DMG требуют Linux/macOS — здесь создаём tar.gz + скрипты для CI/ручной сборки.
param(
    [string]$Version = "2.1.0"
)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Out = Join-Path $Root "installers\Output"
$StagingRoot = Join-Path $Out "crossplatform-staging"
$Legacy = Join-Path $Root "_legacy"
$ConfigSrc = Join-Path $Root "KengaCAD\config"

function Sync-CrossPlatformStaging {
    param([string]$TargetDir)
    if (Test-Path $TargetDir) { Remove-Item $TargetDir -Recurse -Force }
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

    $exclude = @('__pycache__', '.venv-build', '.venv', 'build', 'dist', '*.pyc')
    robocopy $Legacy $TargetDir /E /XD __pycache__ .venv .venv-build build dist /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy legacy failed: $LASTEXITCODE" }

    $cfgDst = Join-Path $TargetDir "config"
    if (Test-Path $cfgDst) { Remove-Item $cfgDst -Recurse -Force }
    Copy-Item $ConfigSrc $cfgDst -Recurse -Force

    @"
#!/bin/bash
set -euo pipefail
cd "`$(dirname "`$0")"
python3 -m venv .venv
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "KengaCAD Cross-Platform готов. Запуск: ./run.sh"
"@ | Set-Content -Path (Join-Path $TargetDir "install.sh") -Encoding UTF8 -NoNewline

    @"
#!/bin/bash
cd "`$(dirname "`$0")"
if [[ ! -d .venv ]]; then
  echo "Сначала: chmod +x install.sh && ./install.sh"
  exit 1
fi
source .venv/bin/activate
exec python3 main.py "`$@"
"@ | Set-Content -Path (Join-Path $TargetDir "run.sh") -Encoding UTF8 -NoNewline

    @"
#!/bin/bash
# Сборка AppImage на Linux: ../../installers/linux/build_appimage.sh
cd "`$(dirname "`$0")"
chmod +x ../../installers/linux/build_appimage.sh 2>/dev/null || true
bash ../../installers/linux/build_appimage.sh
"@ | Set-Content -Path (Join-Path $TargetDir "build_appimage_here.sh") -Encoding UTF8 -NoNewline

    @"
KengaCAD Professional Cross-Platform $Version
==========================================

Windows: используйте KengaCAD_Professional_Setup.exe (C#/WPF).

Linux / macOS: PyQt-клиент из _legacy с конфигами Professional 2.x.

Быстрый старт (Linux/macOS):
  chmod +x install.sh run.sh
  ./install.sh
  ./run.sh

AppImage (только Linux):
  bash installers/linux/build_appimage.sh

DMG (только macOS):
  bash installers/macos/build_dmg.sh
"@ | Set-Content -Path (Join-Path $TargetDir "README.txt") -Encoding UTF8
}

Write-Host "[Cross] Linux portable tar.gz..."
$linuxDir = Join-Path $StagingRoot "linux"
Sync-CrossPlatformStaging -TargetDir $linuxDir
$linuxTar = Join-Path $Out "KengaCAD_Professional_${Version}_linux-x64_portable.tar.gz"
if (Test-Path $linuxTar) { Remove-Item $linuxTar -Force }
tar -czf $linuxTar -C $linuxDir .
$linuxMb = [math]::Round((Get-Item $linuxTar).Length / 1MB, 1)
Write-Host "      $linuxTar ($linuxMb MB)"

Write-Host "[Cross] macOS portable tar.gz..."
$macDir = Join-Path $StagingRoot "macos"
Sync-CrossPlatformStaging -TargetDir $macDir

@'
#!/bin/bash
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then ./install.sh; fi
source .venv/bin/activate
exec python3 main.py "$@"
'@ | Set-Content -Path (Join-Path $macDir "KengaCAD.command") -Encoding UTF8

$macTar = Join-Path $Out "KengaCAD_Professional_${Version}_macos_portable.tar.gz"
if (Test-Path $macTar) { Remove-Item $macTar -Force }
tar -czf $macTar -C $macDir .
$macMb = [math]::Round((Get-Item $macTar).Length / 1MB, 1)
Write-Host "      $macTar ($macMb MB)"

# WSL AppImage (optional)
$wsl = Get-Command wsl -ErrorAction SilentlyContinue
if ($wsl) {
    Write-Host "[Cross] WSL detected - trying AppImage..."
    $wslRoot = ($Root -replace '\\','/') -replace '^([A-Z]):','/mnt/$1'
    $wslRoot = $wslRoot.ToLower()
    $wslCmd = "cd '$wslRoot'; chmod +x installers/linux/build_appimage.sh; KENGACAD_VERSION=$Version ./installers/linux/build_appimage.sh"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & wsl bash -lc $wslCmd 2>&1 | Out-Host
    $wslExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($wslExit -ne 0) {
        Write-Warning "AppImage via WSL failed (install WSL2 or use Linux CI). Portable tar.gz is ready."
    }
} else {
    Write-Host "[Cross] No WSL - AppImage/DMG: run installers/linux/build_appimage.sh or installers/macos/build_dmg.sh on target OS."
}

Write-Host "[Cross] Done."
