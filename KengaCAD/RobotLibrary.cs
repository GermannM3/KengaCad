using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;

namespace KengaCAD
{
    public class RobotDefinition
    {
        public string Id { get; set; } = "";
        public string Name { get; set; } = "";
        public string Manufacturer { get; set; } = "";
        public string Description { get; set; } = "";
        public DhParams[] DhParams { get; set; } = Array.Empty<DhParams>();
        public double[] JointMin { get; set; } = new double[6];
        public double[] JointMax { get; set; } = new double[6];
        public double MaxReachMm { get; set; }
        public double PayloadKg { get; set; }

        public string DisplayName =>
            string.IsNullOrWhiteSpace(Manufacturer) ? Name : $"{Manufacturer} {Name}";
    }

    /// <summary>Загрузка библиотеки роботов из config/robots.json.</summary>
    public static class RobotLibrary
    {
        private static List<RobotDefinition>? _robots;

        public static IReadOnlyList<RobotDefinition> Robots
        {
            get
            {
                if (_robots == null) Load();
                return _robots!;
            }
        }

        public static void Load()
        {
            _robots = new List<RobotDefinition>();
            string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "config", "robots.json");
            if (!File.Exists(path))
            {
                _robots.Add(CreateFallback("demo", "Демо (6 осей)", "", RobotKinematics.DefaultDh,
                    new[] { -180.0, -120.0, -170.0, -190.0, -120.0, -350.0 },
                    new[] { 180.0, 120.0, 170.0, 190.0, 120.0, 350.0 }));
                return;
            }

            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(path));
                if (!doc.RootElement.TryGetProperty("robots", out var arr)) return;
                foreach (var item in arr.EnumerateArray())
                {
                    var id = item.GetProperty("id").GetString() ?? "";
                    var name = item.GetProperty("name").GetString() ?? id;
                    var mfr = item.TryGetProperty("manufacturer", out var m) ? m.GetString() ?? "" : "";
                    var desc = item.TryGetProperty("description", out var d) ? d.GetString() ?? "" : "";
                    var dh = ParseDh(item);
                    var (jMin, jMax) = ParseJointLimits(item);
                    double reach = item.TryGetProperty("max_reach_mm", out var r) ? r.GetDouble() : 0;
                    double payload = item.TryGetProperty("payload_kg", out var p) ? p.GetDouble() : 0;
                    _robots.Add(new RobotDefinition
                    {
                        Id = id,
                        Name = name,
                        Manufacturer = mfr,
                        Description = desc,
                        DhParams = dh,
                        JointMin = jMin,
                        JointMax = jMax,
                        MaxReachMm = reach,
                        PayloadKg = payload
                    });
                }
            }
            catch
            {
                _robots.Clear();
                _robots.Add(CreateFallback("demo", "Демо (6 осей)", "", RobotKinematics.DefaultDh,
                    new[] { -180.0, -120.0, -170.0, -190.0, -120.0, -350.0 },
                    new[] { 180.0, 120.0, 170.0, 190.0, 120.0, 350.0 }));
            }
        }

        public static RobotDefinition? FindByDisplayName(string displayName)
        {
            return Robots.FirstOrDefault(r =>
                r.DisplayName.Equals(displayName, StringComparison.OrdinalIgnoreCase) ||
                r.Name.Equals(displayName, StringComparison.OrdinalIgnoreCase));
        }

        public static RobotDefinition? FindById(string id)
            => Robots.FirstOrDefault(r => r.Id.Equals(id, StringComparison.OrdinalIgnoreCase));

        private static DhParams[] ParseDh(JsonElement item)
        {
            if (!item.TryGetProperty("dh_params", out var arr)) return RobotKinematics.DefaultDh;
            var list = new List<DhParams>();
            foreach (var row in arr.EnumerateArray())
            {
                var vals = row.EnumerateArray().Select(v => v.GetDouble()).ToArray();
                if (vals.Length >= 4)
                    list.Add(new DhParams(vals[0], vals[1], vals[2], vals[3]));
            }
            return list.Count >= 6 ? list.ToArray() : RobotKinematics.DefaultDh;
        }

        private static (double[] Min, double[] Max) ParseJointLimits(JsonElement item)
        {
            var jMin = Enumerable.Repeat(-180.0, 6).ToArray();
            var jMax = Enumerable.Repeat(180.0, 6).ToArray();
            if (!item.TryGetProperty("joint_limits", out var arr)) return (jMin, jMax);
            int i = 0;
            foreach (var pair in arr.EnumerateArray())
            {
                if (i >= 6) break;
                var vals = pair.EnumerateArray().Select(v => v.GetDouble()).ToArray();
                if (vals.Length >= 2)
                {
                    jMin[i] = vals[0];
                    jMax[i] = vals[1];
                }
                i++;
            }
            return (jMin, jMax);
        }

        private static RobotDefinition CreateFallback(string id, string name, string mfr, DhParams[] dh,
            double[] jMin, double[] jMax) => new()
        {
            Id = id,
            Name = name,
            Manufacturer = mfr,
            DhParams = dh,
            JointMin = jMin,
            JointMax = jMax
        };
    }
}
