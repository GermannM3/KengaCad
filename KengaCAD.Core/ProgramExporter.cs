using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;

namespace KengaCAD;

/// <summary>
/// Экспорт программы с MoveL/MoveJ + Wait + IO (впрыск / сварка / захват)
/// в код контроллера — то, что уходит с ноутбука в цех.
/// </summary>
public static class ProgramExporter
{
    public static bool Export(
        string brand,
        IReadOnlyList<ProgramWaypoint> waypoints,
        IReadOnlyList<ProgramOperation> operations,
        string filePath,
        double defaultSpeedMmS = 100)
    {
        if (waypoints == null || waypoints.Count == 0) return false;
        var ops = operations is { Count: > 0 }
            ? operations.ToList()
            : waypoints.Select((_, i) => new ProgramOperation
            {
                Index = i + 1,
                Type = "MoveL",
                WaypointIndex = i + 1,
                Speed = waypoints[i].Speed > 0 ? waypoints[i].Speed : defaultSpeedMmS
            }).ToList();

        return brand.ToLowerInvariant() switch
        {
            "kuka" or "krl" => WriteKuka(waypoints, ops, filePath, defaultSpeedMmS),
            "abb" or "rapid" => WriteAbb(waypoints, ops, filePath, defaultSpeedMmS),
            "fanuc" or "tp" => WriteFanuc(waypoints, ops, filePath, defaultSpeedMmS),
            "ur" => WriteUr(waypoints, ops, filePath, defaultSpeedMmS),
            _ => WriteKuka(waypoints, ops, filePath, defaultSpeedMmS)
        };
    }

    private static ProgramWaypoint? FindWp(IReadOnlyList<ProgramWaypoint> wps, int index)
        => wps.FirstOrDefault(w => w.Index == index) ?? (index >= 1 && index <= wps.Count ? wps[index - 1] : null);

    private static int ChannelNum(string channel)
    {
        var m = Regex.Match(channel ?? "", @"\d+");
        return m.Success && int.TryParse(m.Value, out var n) ? n : 1;
    }

    private static bool WriteKuka(IReadOnlyList<ProgramWaypoint> wps, List<ProgramOperation> ops, string path, double defSpeed)
    {
        var sb = new StringBuilder();
        sb.AppendLine("DEF KengaCAD_Cell()");
        sb.AppendLine("  ; Offline program — KengaCAD Professional");
        sb.AppendLine("  ; DO: захват / впрыск (герметик) / сварка — сверьте номера $OUT с ячейкой");
        sb.AppendLine("  $TOOL = TOOL_DATA[1]");
        sb.AppendLine("  $BASE = BASE_DATA[0]");
        sb.AppendLine();
        foreach (var op in ops)
        {
            switch (op.Type.ToUpperInvariant())
            {
                case "IO":
                    int ch = ChannelNum(op.IoChannel);
                    string val = op.IoValue ? "TRUE" : "FALSE";
                    sb.AppendLine($"  ; IO {op.IoChannel}={(op.IoValue ? 1 : 0)}");
                    sb.AppendLine($"  $OUT[{ch}] = {val}");
                    break;
                case "WAIT":
                    sb.AppendLine($"  WAIT SEC {Math.Max(0.01, op.WaitMs / 1000.0):F3}");
                    break;
                case "MOVEJ":
                {
                    var wp = FindWp(wps, op.WaypointIndex);
                    if (wp == null) break;
                    double vel = Math.Max(0.01, (op.Speed > 0 ? op.Speed : defSpeed) / 1000.0);
                    sb.AppendLine($"  $VEL.CP = {vel:F3}");
                    sb.AppendLine($"  PTP {{X {wp.X:F3}, Y {wp.Y:F3}, Z {wp.Z:F3}, A {wp.Rz:F3}, B {wp.Ry:F3}, C {wp.Rx:F3}}}");
                    break;
                }
                default: // MoveL
                {
                    var wp = FindWp(wps, op.WaypointIndex);
                    if (wp == null) break;
                    double vel = Math.Max(0.01, (op.Speed > 0 ? op.Speed : defSpeed) / 1000.0);
                    sb.AppendLine($"  $VEL.CP = {vel:F3}");
                    sb.AppendLine($"  LIN {{X {wp.X:F3}, Y {wp.Y:F3}, Z {wp.Z:F3}, A {wp.Rz:F3}, B {wp.Ry:F3}, C {wp.Rx:F3}}} C_DIS");
                    break;
                }
            }
        }
        sb.AppendLine("END");
        try { File.WriteAllText(path, sb.ToString(), Encoding.UTF8); return true; }
        catch { return false; }
    }

    private static bool WriteAbb(IReadOnlyList<ProgramWaypoint> wps, List<ProgramOperation> ops, string path, double defSpeed)
    {
        var sb = new StringBuilder();
        sb.AppendLine("MODULE KengaCAD_Cell");
        sb.AppendLine("  ! Offline — KengaCAD. Remap SetDO names to cell signals.");
        sb.AppendLine("  PERS tooldata tool0 := [TRUE,[[0,0,0],[1,0,0,0]],[0.001,[0,0,0.001],[1,0,0,0],0,0,0]];");
        sb.AppendLine("  PROC main()");
        sb.AppendLine("    ConfL \\Off;");
        foreach (var op in ops)
        {
            switch (op.Type.ToUpperInvariant())
            {
                case "IO":
                    int ch = ChannelNum(op.IoChannel);
                    sb.AppendLine($"    ! {op.IoChannel}={(op.IoValue ? 1 : 0)}");
                    sb.AppendLine($"    SetDO do{ch}, {(op.IoValue ? 1 : 0)};");
                    break;
                case "WAIT":
                    sb.AppendLine($"    WaitTime {Math.Max(0.01, op.WaitMs / 1000.0):F3};");
                    break;
                case "MOVEJ":
                {
                    var wp = FindWp(wps, op.WaypointIndex);
                    if (wp == null) break;
                    int v = (int)Math.Round(op.Speed > 0 ? op.Speed : defSpeed);
                    var q = TrajectoryPoint.FromXyz(wp.X, wp.Y, wp.Z, wp.Rx, wp.Ry, wp.Rz).Quaternion;
                    sb.AppendLine($"    MoveJ [[{wp.X:F3},{wp.Y:F3},{wp.Z:F3}],[{q.Q1:F6},{q.Q2:F6},{q.Q3:F6},{q.Q4:F6}],[0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]], v{v}, fine, tool0;");
                    break;
                }
                default:
                {
                    var wp = FindWp(wps, op.WaypointIndex);
                    if (wp == null) break;
                    int v = (int)Math.Round(op.Speed > 0 ? op.Speed : defSpeed);
                    var q = TrajectoryPoint.FromXyz(wp.X, wp.Y, wp.Z, wp.Rx, wp.Ry, wp.Rz).Quaternion;
                    sb.AppendLine($"    MoveL [[{wp.X:F3},{wp.Y:F3},{wp.Z:F3}],[{q.Q1:F6},{q.Q2:F6},{q.Q3:F6},{q.Q4:F6}],[0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]], v{v}, fine, tool0;");
                    break;
                }
            }
        }
        sb.AppendLine("  ENDPROC");
        sb.AppendLine("ENDMODULE");
        try { File.WriteAllText(path, sb.ToString(), Encoding.UTF8); return true; }
        catch { return false; }
    }

    private static bool WriteFanuc(IReadOnlyList<ProgramWaypoint> wps, List<ProgramOperation> ops, string path, double defSpeed)
    {
        var points = new List<ProgramWaypoint>();
        var sb = new StringBuilder();
        sb.AppendLine("/PROG  KENGACAD_CELL");
        sb.AppendLine("/ATTR");
        sb.AppendLine("COMMENT     = \"KengaCAD cell program\";");
        sb.AppendLine("/MN");
        sb.AppendLine("   1:  UTOOL_NUM=1 ;");
        sb.AppendLine("   2:  UFRAME_NUM=0 ;");
        int line = 3;
        int pnum = 1;
        foreach (var op in ops)
        {
            switch (op.Type.ToUpperInvariant())
            {
                case "IO":
                    int ch = ChannelNum(op.IoChannel);
                    sb.AppendLine($"   {line}:  DO[{ch}]={(op.IoValue ? "ON" : "OFF")} ;");
                    line++;
                    break;
                case "WAIT":
                    sb.AppendLine($"   {line}:  WAIT  {Math.Max(0.01, op.WaitMs / 1000.0):F2} sec ;");
                    line++;
                    break;
                default:
                {
                    var wp = FindWp(wps, op.WaypointIndex);
                    if (wp == null) break;
                    points.Add(wp);
                    double spd = op.Speed > 0 ? op.Speed : defSpeed;
                    string motion = op.Type.Equals("MoveJ", StringComparison.OrdinalIgnoreCase) ? "J" : "L";
                    sb.AppendLine($"   {line}:{motion} P[{pnum}] {spd:F0}mm/sec FINE    ;");
                    line++;
                    pnum++;
                    break;
                }
            }
        }
        sb.AppendLine("/POS");
        for (int i = 0; i < points.Count; i++)
        {
            var wp = points[i];
            sb.AppendLine($"P[{i + 1}]{{");
            sb.AppendLine("  GP1:");
            sb.AppendLine("  UF : 0, UT : 1,");
            sb.AppendLine($"  X = {wp.X:F3}  mm, Y = {wp.Y:F3}  mm, Z = {wp.Z:F3}  mm,");
            sb.AppendLine($"  W = {wp.Rx:F3}  deg, P = {wp.Ry:F3}  deg, R = {wp.Rz:F3}  deg");
            sb.AppendLine("};");
        }
        sb.AppendLine("/END");
        try { File.WriteAllText(path, sb.ToString(), Encoding.UTF8); return true; }
        catch { return false; }
    }

    private static bool WriteUr(IReadOnlyList<ProgramWaypoint> wps, List<ProgramOperation> ops, string path, double defSpeed)
    {
        var sb = new StringBuilder();
        sb.AppendLine("def kengacad_cell():");
        sb.AppendLine("  # KengaCAD — remap digital_out indices to cell");
        foreach (var op in ops)
        {
            switch (op.Type.ToUpperInvariant())
            {
                case "IO":
                    int ch = ChannelNum(op.IoChannel);
                    sb.AppendLine($"  set_digital_out({Math.Max(0, ch - 1)}, {(op.IoValue ? "True" : "False")})");
                    break;
                case "WAIT":
                    sb.AppendLine($"  sleep({Math.Max(0.01, op.WaitMs / 1000.0):F3})");
                    break;
                default:
                {
                    var wp = FindWp(wps, op.WaypointIndex);
                    if (wp == null) break;
                    double s = Math.Max(0.01, (op.Speed > 0 ? op.Speed : defSpeed) / 1000.0);
                    var q = TrajectoryPoint.FromXyz(wp.X, wp.Y, wp.Z, wp.Rx, wp.Ry, wp.Rz).Quaternion;
                    // UR pose: xyz in meters + rx ry rz as rotation vector approx from RPY — keep xyz + zeros for simplicity of offline
                    sb.AppendLine($"  movel(p[{wp.X / 1000.0:F5}, {wp.Y / 1000.0:F5}, {wp.Z / 1000.0:F5}, {wp.Rx * Math.PI / 180.0:F4}, {wp.Ry * Math.PI / 180.0:F4}, {wp.Rz * Math.PI / 180.0:F4}], a=1.2, v={s:F3})");
                    break;
                }
            }
        }
        sb.AppendLine("end");
        try { File.WriteAllText(path, sb.ToString(), Encoding.UTF8); return true; }
        catch { return false; }
    }
}
