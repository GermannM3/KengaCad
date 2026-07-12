param(
    [string]$Version = "2.2.0"
)
$Root = Split-Path $PSScriptRoot -Parent
$dst = Join-Path $Root "KengaCAD.Mobile\Resources\Raw\config"
$tpl = Join-Path $dst "templates"
New-Item -ItemType Directory -Force -Path $tpl | Out-Null
Copy-Item "$Root\KengaCAD\config\*.json" $dst -Force
Copy-Item "$Root\KengaCAD\config\templates\*" $tpl -Force
Write-Host "Mobile config synced to $dst"
