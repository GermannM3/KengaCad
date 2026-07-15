using KengaCAD;

var outDir = Path.Combine("installers", "Output", "ux_smoke");
Directory.CreateDirectory(outDir);

var wps = new List<ProgramWaypoint>
{
    new() { Index = 1, X = 100, Y = 0, Z = 200, Speed = 80 },
    new() { Index = 2, X = 100, Y = 0, Z = 50, Speed = 60 },
    new() { Index = 3, X = 400, Y = 0, Z = 50, Speed = 60 },
    new() { Index = 4, X = 400, Y = 0, Z = 200, Speed = 80 },
};
var ops = new List<ProgramOperation>
{
    new() { Index = 1, Type = "MoveJ", WaypointIndex = 1, Speed = 80 },
    new() { Index = 2, Type = "MoveL", WaypointIndex = 2, Speed = 60 },
    new() { Index = 3, Type = "IO", WaypointIndex = 2, IoChannel = "DO3", IoValue = true },
    new() { Index = 4, Type = "MoveL", WaypointIndex = 3, Speed = 60 },
    new() { Index = 5, Type = "IO", WaypointIndex = 3, IoChannel = "DO3", IoValue = false },
    new() { Index = 6, Type = "MoveL", WaypointIndex = 4, Speed = 80 },
};

var kuka = Path.Combine(outDir, "cell.src");
var abb = Path.Combine(outDir, "cell.mod");
var fanuc = Path.Combine(outDir, "cell.ls");
Console.WriteLine($"export kuka={ProgramExporter.Export("kuka", wps, ops, kuka)}");
Console.WriteLine($"export abb={ProgramExporter.Export("abb", wps, ops, abb)}");
Console.WriteLine($"export fanuc={ProgramExporter.Export("fanuc", wps, ops, fanuc)}");

var fk = RobotKinematics.FkFull(new double[] { 0, 0, 0, 0, 0, 0 });
Console.WriteLine($"FK TCP Z={fk.TcpPos.Z:F1}");

var probe = await RobotLinkProbe.ProbeAsync("127.0.0.1", 1);
Console.WriteLine($"probe closed: ok={probe.Ok} msg={probe.Message}");

var text = await File.ReadAllTextAsync(kuka);
Console.WriteLine($"KRL has OUT TRUE={text.Contains("$OUT[3] = TRUE")} FALSE={text.Contains("$OUT[3] = FALSE")}");
Console.WriteLine("--- KRL ---");
Console.WriteLine(string.Join('\n', text.Split('\n').Take(22)));
