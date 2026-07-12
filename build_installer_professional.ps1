# Build KengaCAD Professional installer (publish + Inno Setup)
# Self-contained: в установку входит .NET 8 + WindowsDesktop + нативные библиотеки SkiaSharp (~170+ МБ распакованных).
param(
    [switch]$NoPortableZip  # skip portable ZIP (faster build)
)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Project = Join-Path $Root "KengaCAD"
$Publish = Join-Path $Project "publish"
$Iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Iscc)) { $Iscc = "C:\Program Files\Inno Setup 6\ISCC.exe" }

Write-Host "[1/3] Publishing KengaCAD Professional (self-contained win-x64)..."
Push-Location $Project
try {
    if (Test-Path $Publish) { Remove-Item $Publish -Recurse -Force }
    dotnet publish -c Release -o publish -r win-x64 --self-contained true `
        -p:PublishSingleFile=false -p:IncludeNativeLibrariesForSelfExtract=true `
        --nologo -v minimal
    if ($LASTEXITCODE -ne 0) { throw "Publish failed" }
    if (-not (Test-Path "$Publish\config")) { New-Item -ItemType Directory -Path "$Publish\config" -Force | Out-Null }
    Copy-Item "$Project\config\*.json" "$Publish\config\" -Force -ErrorAction SilentlyContinue
    $tplSrc = Join-Path $Project "config\templates"
    if (Test-Path $tplSrc) {
        $tplDst = Join-Path $Publish "config\templates"
        if (-not (Test-Path $tplDst)) { New-Item -ItemType Directory -Path $tplDst -Force | Out-Null }
        Copy-Item "$tplSrc\*" $tplDst -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-Path "$Publish\assets")) { New-Item -ItemType Directory -Path "$Publish\assets" -Force | Out-Null }
    Copy-Item "$Project\assets\*" "$Publish\assets\" -Recurse -Force -ErrorAction SilentlyContinue

    $exe = Join-Path $Publish "KengaCAD.exe"
    if (-not (Test-Path $exe)) { throw "Publish incomplete: KengaCAD.exe missing" }
    $clr = Get-ChildItem $Publish -Filter "clrjit.dll" -File -ErrorAction SilentlyContinue
    if (-not $clr) { throw "Publish looks framework-dependent: clrjit.dll not in publish root. Use --self-contained true." }
    $bytes = (Get-ChildItem $Publish -Recurse -File | Measure-Object -Property Length -Sum).Sum
    $mb = [math]::Round($bytes / 1MB, 1)
    Write-Host "      Published: $mb MB, files: $((Get-ChildItem $Publish -Recurse -File).Count)"
    if ($mb -lt 80) { Write-Warning "Publish folder is smaller than expected for self-contained .NET 8 + WPF; verify publish output." }

    $outDir = Join-Path $Root "installers\Output"
    if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
    $manifestPath = Join-Path $outDir "PUBLISH_MANIFEST.txt"
    $crit = @(
        "KengaCAD.exe", "clrjit.dll", "coreclr.dll", "SkiaSharp.dll",
        "PresentationFramework.dll", "wpfgfx_cor3.dll"
    )
    $lines = @(
        "KengaCAD Professional - publish folder manifest (self-contained win-x64)",
        "Generated (local time): $(Get-Date -Format 'yyyy-MM-dd HH:mm')",
        "",
        "Unpacked size: $mb MB",
        "File count: $((Get-ChildItem $Publish -Recurse -File).Count)",
        "",
        "Key files (publish root):"
    )
    foreach ($n in $crit) {
        $ok = Test-Path (Join-Path $Publish $n)
        $status = if ($ok) { "OK" } else { "MISSING" }
        $lines += "  ${n}: $status"
    }
    $skiNative = Get-ChildItem -Path $Publish -Recurse -Filter "libSkiaSharp.dll" -File -ErrorAction SilentlyContinue | Select-Object -First 1
    $lines += ""
    $skiLine = if ($skiNative) { $skiNative.FullName } else { "MISSING" }
    $lines += "libSkiaSharp.dll (native): $skiLine"
    $lines | Set-Content -Path $manifestPath -Encoding UTF8
    Write-Host "      Manifest: $manifestPath"
} finally { Pop-Location }

if (-not $NoPortableZip) {
    Write-Host "[2a] Portable ZIP (full publish; same payload as installer unpacks)..."
    $zipOut = Join-Path $Root "installers\Output\KengaCAD_Professional_win-x64_self-contained.zip"
    if (Test-Path $zipOut) { Remove-Item $zipOut -Force }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::CreateFromDirectory($Publish, $zipOut, [System.IO.Compression.CompressionLevel]::Optimal, $false)
    $zipMb = [math]::Round((Get-Item $zipOut).Length / 1MB, 1)
    Write-Host "      ZIP: $zipOut ($zipMb MB)"
}

if (Test-Path $Iscc) {
    Write-Host "[2/3] Building installer (Inno Setup)..."
    $installersDir = Join-Path $Root "installers"
    Copy-Item (Join-Path $Project "assets\logo.ico") (Join-Path $installersDir "logo.ico") -Force -ErrorAction SilentlyContinue
    Push-Location $installersDir
    try {
        & $Iscc "KengaCAD_Professional.iss"
        if ($LASTEXITCODE -eq 0) {
            $setupExe = Join-Path $installersDir "Output\KengaCAD_Professional_Setup.exe"
            $hash = Get-FileHash -Path $setupExe -Algorithm SHA256
            $hashPath = Join-Path $installersDir "Output\KengaCAD_Professional_Setup.sha256"
            "$($hash.Hash)  KengaCAD_Professional_Setup.exe" | Set-Content -Path $hashPath -Encoding ASCII
            $setupMb = [math]::Round((Get-Item $setupExe).Length / 1MB, 1)
            Write-Host "[3/3] Done."
            Write-Host "      Installer: $setupExe ($setupMb MB compressed; ~$mb MB on disk after install)"
            Write-Host "      SHA256:    $hashPath"
            Write-Host "      Unsigned builds are blocked by Smart App Control: see docs\WINDOWS_TRUST_AND_SIGNING.md"
            if ($env:KENGACAD_CODESIGN_PFX -and (Test-Path $env:KENGACAD_CODESIGN_PFX)) {
                Write-Host "[3b] Code signing..."
                & (Join-Path $Root "installers\sign_installer.ps1")
            }
        } else { Write-Host "ERROR: Installer build failed."; exit 1 }
    } finally { Pop-Location }
} else {
    Write-Host "[2/3] Inno Setup not found. Run: $Publish\KengaCAD.exe"
}
