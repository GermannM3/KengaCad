# Upload PFX to GitHub Secrets for release.yml
param(
    [string]$PfxPath = "",
    [string]$Password = "",
    [string]$Repo = "GermannM3/KengaCad"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$secretsDir = Join-Path $Root "installers\secrets"

if (-not $PfxPath) {
    $PfxPath = Join-Path $secretsDir "kengacad_codesign.pfx"
}
if (-not (Test-Path $PfxPath)) {
    throw "PFX not found: $PfxPath. Run: .\scripts\setup_codesign_cert.ps1"
}

if (-not $Password) {
    $passFile = Join-Path $secretsDir "codesign.password.txt"
    if (Test-Path $passFile) {
        $Password = Get-Content -Path $passFile -Raw
    }
}
if (-not $Password) {
    $Password = Read-Host "PFX password"
}

$bytes = [IO.File]::ReadAllBytes($PfxPath)
$b64 = [Convert]::ToBase64String($bytes)

gh auth status | Out-Null

Write-Host "Writing secrets to $Repo ..."
$b64 | gh secret set KENGACAD_CODESIGN_PFX_BASE64 --repo $Repo
$Password | gh secret set KENGACAD_CODESIGN_PASS --repo $Repo

Write-Host "Updated KENGACAD_CODESIGN_PFX_BASE64 and KENGACAD_CODESIGN_PASS"
Write-Host "Retag to rebuild signed Setup: git tag -f v2.2.1 && git push origin v2.2.1 --force"
