# Полная сборка всех установщиков: Windows + Linux portable + macOS portable (+ AppImage через WSL)
param(
    [switch]$NoPortableZip,
    [switch]$SkipCrossPlatform,
    [string]$Version = "2.1.0"
)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

Write-Host "=== KengaCAD Professional $Version - all platforms ==="

& (Join-Path $Root "build_installer_professional.ps1") @PSBoundParameters

if (-not $SkipCrossPlatform) {
    & (Join-Path $Root "build_crossplatform.ps1") -Version $Version
}

$out = Join-Path $Root "installers\Output"
Write-Host ""
Write-Host "=== Output: $out ==="
Get-ChildItem $out -File | Sort-Object Name | ForEach-Object {
    $mb = [math]::Round($_.Length / 1MB, 2)
    Write-Host ("  {0}  {1} MB" -f $_.Name, $mb)
}
