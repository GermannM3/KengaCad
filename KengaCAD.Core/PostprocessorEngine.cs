using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Scriban;
using Scriban.Runtime;

namespace KengaCAD
{
    public static class PostprocessorEngine
    {
        private static readonly Dictionary<string, Dictionary<string, JsonElement>> _configCache = new();

        public static string GetConfigDirectory() => AppPaths.GetConfigDirectory();

        public static bool TryExport(string brandKey, IReadOnlyList<TrajectoryPoint> points, string filePath, double speedOverride = 0)
        {
            if (points == null || points.Count == 0) return false;
            try
            {
                var configDir = GetConfigDirectory();
                if (!LoadBrandConfig(configDir, brandKey, out var cfg)) return false;
                string templateName = cfg.TryGetValue("template", out var tEl) ? tEl.GetString() ?? "" : "";
                if (string.IsNullOrEmpty(templateName)) return false;
                templateName = Path.ChangeExtension(templateName, ".sbn");
                var templatePath = Path.Combine(configDir, "templates", templateName);
                if (!File.Exists(templatePath))
                    templatePath = Path.Combine(configDir, "templates", Path.GetFileNameWithoutExtension(templateName) + ".sbn");
                if (!File.Exists(templatePath)) return false;

                var templateText = File.ReadAllText(templatePath);
                var template = Template.Parse(templateText);
                if (template.HasErrors) return false;

                var scriptObj = new ScriptObject();
                foreach (var kv in cfg)
                    scriptObj.Add(kv.Key, JsonToObject(kv.Value));

                double speed = speedOverride > 0 ? speedOverride :
                    cfg.TryGetValue("default_speed_mms", out var sp) ? sp.GetDouble() : 100.0;
                scriptObj.Add("speed_mms", speed);
                scriptObj.Add("date", DateTime.Now.ToString("yyyy/MM/dd HH:mm"));
                scriptObj.Add("points", BuildPointList(points));

                var context = new TemplateContext();
                context.PushGlobal(scriptObj);
                var result = template.Render(context);
                File.WriteAllText(filePath, result);
                return true;
            }
            catch
            {
                return false;
            }
        }

        private static List<object> BuildPointList(IReadOnlyList<TrajectoryPoint> points)
        {
            var list = new List<object>(points.Count);
            foreach (var pt in points)
            {
                var q = pt.Quaternion;
                list.Add(new
                {
                    x = pt.X, y = pt.Y, z = pt.Z,
                    rx = pt.Rx, ry = pt.Ry, rz = pt.Rz,
                    q1 = q.Q1, q2 = q.Q2, q3 = q.Q3, q4 = q.Q4
                });
            }
            return list;
        }

        private static bool LoadBrandConfig(string configDir, string brandKey, out Dictionary<string, JsonElement> cfg)
        {
            cfg = new Dictionary<string, JsonElement>();
            if (!_configCache.TryGetValue(brandKey, out cfg!))
            {
                var jsonPath = Path.Combine(configDir, "postprocessors.json");
                if (!File.Exists(jsonPath)) return false;
                var root = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(File.ReadAllText(jsonPath));
                if (root == null || !root.TryGetValue(brandKey, out var brandEl)) return false;
                cfg = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(brandEl.GetRawText())
                      ?? new Dictionary<string, JsonElement>();
                _configCache[brandKey] = cfg;
            }
            return cfg.Count > 0;
        }

        private static object? JsonToObject(JsonElement el) => el.ValueKind switch
        {
            JsonValueKind.String => el.GetString(),
            JsonValueKind.Number => el.TryGetInt64(out var l) ? l : el.GetDouble(),
            JsonValueKind.True => true,
            JsonValueKind.False => false,
            JsonValueKind.Null => null,
            _ => el.GetRawText()
        };
    }
}
