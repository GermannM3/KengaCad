# Create or reuse PFX for KengaCAD code signing (local + GitHub Actions).
# Self-signed = CI pipeline test. For end-user trust use OV/EV cert from a public CA.
param(
    [string]$Subject = "CN=KengaCAD Team, O=KengaCAD, C=RU",
    [string]$OutDir = "",
    [string]$PfxName = "kengacad_codesign.pfx",
    [string]$Password = "",
    [int]$YearsValid = 3,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
if (-not $OutDir) { $OutDir = Join-Path $Root "installers\secrets" }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$pfxPath = Join-Path $OutDir $PfxName
$metaPath = Join-Path $OutDir "codesign.meta.json"
$passPath = Join-Path $OutDir "codesign.password.txt"

if ((Test-Path $pfxPath) -and -not $Force) {
    Write-Host "PFX already exists: $pfxPath"
    Write-Host "Re-run with -Force to recreate."
    exit 0
}

if (-not $Password) {
    $Password = -join ((48..57 + 65..90 + 97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })
}

$existing = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert -ErrorAction SilentlyContinue |
    Where-Object { $_.Subject -eq $Subject } |
    Sort-Object NotAfter -Descending |
    Select-Object -First 1

if ($Force -and $existing) {
    Remove-Item "Cert:\CurrentUser\My\$($existing.Thumbprint)" -Force
    $existing = $null
}

if (-not $existing) {
    Write-Host "Creating code-signing certificate: $Subject"
    $existing = New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $Subject `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -KeyExportPolicy Exportable `
        -KeySpec Signature `
        -KeyLength 2048 `
        -HashAlgorithm SHA256 `
        -NotAfter (Get-Date).AddYears($YearsValid)
}

$secure = ConvertTo-SecureString -String $Password -Force -AsPlainText
Export-PfxCertificate -Cert $existing -FilePath $pfxPath -Password $secure | Out-Null

$meta = @{
    subject    = $Subject
    thumbprint = $existing.Thumbprint
    notAfter   = $existing.NotAfter.ToString("o")
    pfxPath    = $pfxPath
    note       = "Self-signed for CI. Replace with CA-issued cert for Smart App Control trust."
}
$meta | ConvertTo-Json | Set-Content -Path $metaPath -Encoding UTF8
Set-Content -Path $passPath -Value $Password -Encoding UTF8 -NoNewline

Write-Host ""
Write-Host "Done."
Write-Host "  PFX:      $pfxPath"
Write-Host "  Password: $passPath"
Write-Host "  Next:     .\scripts\publish_github_codesign_secrets.ps1"
