# Sign Setup.exe (and optionally KengaCAD.exe in publish).
param(
    [switch]$SignPublishExe
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$signScript = Join-Path $PSScriptRoot "Sign-Authenticode.ps1"

$toSign = @()
if ($SignPublishExe) {
    $appExe = Join-Path $Root "KengaCAD\publish\KengaCAD.exe"
    if (Test-Path $appExe) { $toSign += $appExe }
}

$setup = Get-ChildItem (Join-Path $PSScriptRoot "Output") -Filter "KengaCAD_Professional*_Setup.exe" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $setup) { throw "Setup.exe not found in Output. Run build_installer_professional.ps1 first." }
$toSign += $setup.FullName

& $signScript -Files $toSign
Write-Host "Signed $($toSign.Count) file(s)."
