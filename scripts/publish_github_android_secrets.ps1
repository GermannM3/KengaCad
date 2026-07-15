# Upload Android keystore to GitHub Secrets for signed APK in releases.
param(
    [string]$KeystorePath = "",
    [string]$Password = "",
    [string]$Alias = "kengacad",
    [string]$Repo = "GermannM3/KengaCad"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$secretsDir = Join-Path $Root "installers\secrets"

if (-not $KeystorePath) {
    $KeystorePath = Join-Path $secretsDir "kengacad-android.keystore"
}
if (-not (Test-Path $KeystorePath)) {
    throw "Keystore not found: $KeystorePath. Run: .\scripts\setup_android_keystore.ps1"
}

if (-not $Password) {
    $passFile = Join-Path $secretsDir "android-signing.password.txt"
    if (Test-Path $passFile) { $Password = (Get-Content $passFile -Raw).Trim() }
}
if (-not $Password) { $Password = Read-Host "Keystore password" }

$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($KeystorePath))

gh auth status | Out-Null
Write-Host "Writing Android signing secrets to $Repo ..."
$b64 | gh secret set KENGACAD_ANDROID_KEYSTORE_BASE64 --repo $Repo
$Password | gh secret set KENGACAD_ANDROID_KEYSTORE_PASS --repo $Repo
$Alias | gh secret set KENGACAD_ANDROID_KEY_ALIAS --repo $Repo
$Password | gh secret set KENGACAD_ANDROID_KEY_PASS --repo $Repo

Write-Host "Updated KENGACAD_ANDROID_KEYSTORE_BASE64, PASS, ALIAS, KEY_PASS"
