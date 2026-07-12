# Authenticode signing helper (Setup.exe, KengaCAD.exe, etc.)
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Files,
    [string]$PfxPath = $env:KENGACAD_CODESIGN_PFX,
    [string]$Password = $env:KENGACAD_CODESIGN_PASS,
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

function Find-SignTool {
    $cmd = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $roots = @("${env:ProgramFiles(x86)}\Windows Kits\10\bin", "${env:ProgramFiles}\Windows Kits\10\bin")
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        $found = Get-ChildItem -Path $root -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\' } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($found) { return $found.FullName }
    }
    return $null
}

if (-not $PfxPath -or -not (Test-Path $PfxPath)) {
    throw "PFX not found. Set KENGACAD_CODESIGN_PFX or -PfxPath."
}
if (-not $Password) {
    $Password = Read-Host "PFX password"
}

$signExe = Find-SignTool
if (-not $signExe) {
    throw "signtool.exe not found. Install Windows SDK (Signing Tools for Desktop Apps)."
}

foreach ($file in $Files) {
    if (-not (Test-Path $file)) { throw "File not found: $file" }
    Write-Host "Signing: $file"
    & $signExe sign /fd SHA256 /td SHA256 /tr $TimestampUrl /f $PfxPath /p $Password $file
    if ($LASTEXITCODE -ne 0) { throw "signtool sign failed ($LASTEXITCODE): $file" }
    & $signExe verify /pa $file 2>$null | Out-Null
    $sig = Get-AuthenticodeSignature $file
    if ($sig.Status -eq 'NotSigned') {
        throw "File has no signature after sign: $file"
    }
    if ($sig.Status -eq 'Valid') {
        Write-Host "OK (trusted): $file"
    } else {
        Write-Warning "Signed ($($sig.Status)): $file — self-signed or untrusted root; use CA cert for Smart App Control."
    }
}

$global:LASTEXITCODE = 0
