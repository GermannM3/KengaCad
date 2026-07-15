# Generate Android release keystore for APK sideloading (not debug).
param(
    [string]$OutDir = "",
    [string]$StorePass = "",
    [string]$KeyPass = "",
    [string]$Alias = "kengacad",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
if (-not $OutDir) { $OutDir = Join-Path $Root "installers\secrets" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$keystore = Join-Path $OutDir "kengacad-android.keystore"
$propsPath = Join-Path $OutDir "android-signing.props"
$passPath = Join-Path $OutDir "android-signing.password.txt"

if ((Test-Path $keystore) -and -not $Force) {
    Write-Host "Keystore exists: $keystore"
    if (-not (Test-Path $passPath)) { throw "Missing password file. Re-run with -Force." }
    $StorePass = (Get-Content $passPath -Raw).Trim()
    if (-not $KeyPass) { $KeyPass = $StorePass }
}
else {
    if (-not $StorePass) {
        $StorePass = -join ((48..57 + 65..90 + 97..122) | Get-Random -Count 28 | ForEach-Object { [char]$_ })
    }
    if (-not $KeyPass) { $KeyPass = $StorePass }

    $keytoolPath = $null
    $cmd = Get-Command keytool -ErrorAction SilentlyContinue
    if ($cmd) { $keytoolPath = $cmd.Source }
    if (-not $keytoolPath) {
        $hit = Get-Item "${env:ProgramFiles}\Microsoft\jdk-*\bin\keytool.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hit) { $keytoolPath = $hit.FullName }
    }
    if (-not $keytoolPath) { throw "keytool.exe not found. Install JDK 17+." }

    if ((Test-Path $keystore) -and $Force) { Remove-Item $keystore -Force }

    & $keytoolPath -genkeypair -v `
        -storetype PKCS12 `
        -keystore $keystore `
        -alias $Alias `
        -keyalg RSA `
        -keysize 2048 `
        -validity 10000 `
        -storepass $StorePass `
        -keypass $KeyPass `
        -dname "CN=KengaCAD Mobile, OU=KengaCAD, O=KengaCAD Team, L=Moscow, C=RU"
    if ($LASTEXITCODE -ne 0) { throw "keytool failed: $LASTEXITCODE" }
    Set-Content -Path $passPath -Value $StorePass -Encoding ASCII -NoNewline
}

if (-not $KeyPass) { $KeyPass = $StorePass }

$xml = @"
<Project>
  <PropertyGroup>
    <AndroidKeyStore>true</AndroidKeyStore>
    <AndroidSigningKeyStore>`$(MSBuildThisFileDirectory)kengacad-android.keystore</AndroidSigningKeyStore>
    <AndroidSigningKeyAlias>$Alias</AndroidSigningKeyAlias>
    <AndroidSigningStorePass>$StorePass</AndroidSigningStorePass>
    <AndroidSigningKeyPass>$KeyPass</AndroidSigningKeyPass>
  </PropertyGroup>
</Project>
"@
Set-Content -Path $propsPath -Value $xml -Encoding UTF8

Write-Host "Done. Keystore=$keystore Props=$propsPath"
Write-Host "Next: .\scripts\publish_github_android_secrets.ps1"
