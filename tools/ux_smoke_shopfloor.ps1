# UX smoke: shop-floor logic as a technologist would use it (no GUI clicks required for Core)
$ErrorActionPreference = "Stop"
Add-Type -Path "d:\KengaCAD\KengaCAD.Core\bin\Release\net8.0\KengaCAD.Core.dll"

$wps = [System.Collections.Generic.List[KengaCAD.ProgramWaypoint]]::new()
$ops = [System.Collections.Generic.List[KengaCAD.ProgramOperation]]::new()

# P1 approach
$wps.Add([KengaCAD.ProgramWaypoint]@{ Index=1; X=100; Y=0; Z=200; Speed=80 })
# P2 start of seal bead
$wps.Add([KengaCAD.ProgramWaypoint]@{ Index=2; X=100; Y=0; Z=50; Speed=60 })
# P3 along bead
$wps.Add([KengaCAD.ProgramWaypoint]@{ Index=3; X=400; Y=0; Z=50; Speed=60 })
# P4 retract
$wps.Add([KengaCAD.ProgramWaypoint]@{ Index=4; X=400; Y=0; Z=200; Speed=80 })

$ops.Add([KengaCAD.ProgramOperation]@{ Index=1; Type="MoveJ"; WaypointIndex=1; Speed=80 })
$ops.Add([KengaCAD.ProgramOperation]@{ Index=2; Type="MoveL"; WaypointIndex=2; Speed=60 })
$ops.Add([KengaCAD.ProgramOperation]@{ Index=3; Type="IO"; WaypointIndex=2; IoChannel="DO3"; IoValue=$true })  # spray ON
$ops.Add([KengaCAD.ProgramOperation]@{ Index=4; Type="MoveL"; WaypointIndex=3; Speed=60 })
$ops.Add([KengaCAD.ProgramOperation]@{ Index=5; Type="IO"; WaypointIndex=3; IoChannel="DO3"; IoValue=$false }) # spray OFF
$ops.Add([KengaCAD.ProgramOperation]@{ Index=6; Type="MoveL"; WaypointIndex=4; Speed=80 })

$outDir = "d:\KengaCAD\installers\Output\ux_smoke"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$files = @{
  kuka = Join-Path $outDir "cell.src"
  abb  = Join-Path $outDir "cell.mod"
  fanuc= Join-Path $outDir "cell.ls"
}

$ok1 = [KengaCAD.ProgramExporter]::Export("kuka", $wps, $ops, $files.kuka)
$ok2 = [KengaCAD.ProgramExporter]::Export("abb", $wps, $ops, $files.abb)
$ok3 = [KengaCAD.ProgramExporter]::Export("fanuc", $wps, $ops, $files.fanuc)

Write-Host "export kuka=$ok1 abb=$ok2 fanuc=$ok3"

# FK sanity
$fk = [KengaCAD.RobotKinematics]::FkFull(@(0.0,0,0,0,0,0), $null)
Write-Host ("FK TCP Z={0:F1}" -f $fk.TcpPos.Z)

# probe closed port (expect fail) and localhost:80 maybe
$probeFail = [KengaCAD.RobotLinkProbe]::ProbeAsync("127.0.0.1", 1).GetAwaiter().GetResult()
Write-Host "probe closed port: Ok=$($probeFail.Item1) Msg=$($probeFail.Item2)"

# Check spray lines in KRL
$krl = Get-Content $files.kuka -Raw
$hasOn = $krl -match '\$OUT\[3\] = TRUE'
$hasOff = $krl -match '\$OUT\[3\] = FALSE'
$hasLin = ($krl -split "`n" | Where-Object { $_ -match 'LIN ' }).Count
Write-Host "KRL spray ON=$hasOn OFF=$hasOff LIN_count=$hasLin"
Write-Host "--- KRL preview ---"
Get-Content $files.kuka | Select-Object -First 25

# UI Automation: enumerate top window buttons briefly
try {
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
  $root = [System.Windows.Automation.AutomationElement]::RootElement
  $cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty, "KengaCAD Professional v2.4.0")
  $win = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
  if ($win) {
    Write-Host "UIA window found: $($win.Current.Name)"
    $btnCond = New-Object System.Windows.Automation.PropertyCondition(
      [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
      [System.Windows.Automation.ControlType]::Button)
    $buttons = $win.FindAll([System.Windows.Automation.TreeScope]::Descendants, $btnCond)
    $names = @()
    foreach ($b in $buttons) {
      $n = $b.Current.Name
      if ($n) { $names += $n }
    }
    Write-Host ("UI buttons sample ({0}): {1}" -f $names.Count, (($names | Select-Object -First 40) -join " | "))
    $hasProbe = $names -contains "Проверить"
    $hasFtp = $names -contains "Залить FTP"
    $hasSpray = ($names -contains "Впрыск ВКЛ") -or ($names -match "Впрыск")
    Write-Host "UI Цех: Проверить=$hasProbe FTP=$hasFtp Впрыск=$hasSpray"
  } else {
    Write-Host "UIA: window not found by title"
  }
} catch {
  Write-Host "UIA skip: $_"
}
