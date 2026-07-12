using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

namespace KengaCAD
{
    /// <summary>Импорт/экспорт траекторий CSV/JSON (RoboCAD-совместимый).</summary>
    public static class TrajectoryIO
    {
        public static List<ProgramWaypoint> ImportCsv(string filePath)
        {
            var result = new List<ProgramWaypoint>();
            using var reader = new StreamReader(filePath, Encoding.UTF8);
            string? headerLine = reader.ReadLine();
            int xi = 0, yi = 1, zi = 2;
            if (headerLine != null)
            {
                var headers = headerLine.Split(',', ';').Select(h => h.Trim().ToLowerInvariant()).ToArray();
                if (headers.Length >= 3 && headers.Contains("x") && headers.Contains("y"))
                {
                    xi = Array.IndexOf(headers, "x");
                    yi = Array.IndexOf(headers, "y");
                    zi = headers.Contains("z") ? Array.IndexOf(headers, "z") : 2;
                }
                else if (double.TryParse(headers[0], NumberStyles.Float, CultureInfo.InvariantCulture, out _))
                {
                    TryAddRow(result, headers, xi, yi, zi);
                }
            }
            while (!reader.EndOfStream)
            {
                var line = reader.ReadLine();
                if (string.IsNullOrWhiteSpace(line)) continue;
                var row = line.Split(',', ';');
                TryAddRow(result, row, xi, yi, zi);
            }
            for (int i = 0; i < result.Count; i++)
                result[i].Index = i + 1;
            return result;
        }

        private static void TryAddRow(List<ProgramWaypoint> result, string[] row, int xi, int yi, int zi)
        {
            if (row.Length < 3) return;
            if (!double.TryParse(row[xi].Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out var x)) return;
            if (!double.TryParse(row[yi].Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out var y)) return;
            double z = 0;
            if (zi < row.Length)
                double.TryParse(row[zi].Trim(), NumberStyles.Float, CultureInfo.InvariantCulture, out z);
            result.Add(new ProgramWaypoint { X = x, Y = y, Z = z, Speed = 120, Accel = 300 });
        }

        public static bool ExportCsv(IReadOnlyList<TrajectoryPoint> points, string filePath)
        {
            var sb = new StringBuilder();
            sb.AppendLine("X,Y,Z,Rx,Ry,Rz");
            foreach (var p in points)
                sb.AppendLine(string.Join(",",
                    p.X.ToString("F3", CultureInfo.InvariantCulture),
                    p.Y.ToString("F3", CultureInfo.InvariantCulture),
                    p.Z.ToString("F3", CultureInfo.InvariantCulture),
                    p.Rx.ToString("F3", CultureInfo.InvariantCulture),
                    p.Ry.ToString("F3", CultureInfo.InvariantCulture),
                    p.Rz.ToString("F3", CultureInfo.InvariantCulture)));
            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
            return true;
        }

        public static bool ExportCsvWaypoints(IReadOnlyList<ProgramWaypoint> waypoints, string filePath)
        {
            var sb = new StringBuilder();
            sb.AppendLine("X,Y,Z,Rx,Ry,Rz,Speed");
            foreach (var p in waypoints)
                sb.AppendLine(string.Join(",",
                    p.X.ToString("F3", CultureInfo.InvariantCulture),
                    p.Y.ToString("F3", CultureInfo.InvariantCulture),
                    p.Z.ToString("F3", CultureInfo.InvariantCulture),
                    p.Rx.ToString("F3", CultureInfo.InvariantCulture),
                    p.Ry.ToString("F3", CultureInfo.InvariantCulture),
                    p.Rz.ToString("F3", CultureInfo.InvariantCulture),
                    p.Speed.ToString("F1", CultureInfo.InvariantCulture)));
            File.WriteAllText(filePath, sb.ToString(), Encoding.UTF8);
            return true;
        }
    }
}
