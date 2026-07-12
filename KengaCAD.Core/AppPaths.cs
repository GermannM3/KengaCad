using System;
using System.IO;

namespace KengaCAD
{
    /// <summary>Общие пути к config (desktop, mobile).</summary>
    public static class AppPaths
    {
        public static string? ConfigRootOverride { get; set; }

        public static string GetConfigDirectory()
        {
            if (!string.IsNullOrWhiteSpace(ConfigRootOverride) && Directory.Exists(ConfigRootOverride))
                return ConfigRootOverride;

            var baseDir = AppDomain.CurrentDomain.BaseDirectory;
            var configDir = Path.Combine(baseDir, "config");
            if (Directory.Exists(configDir))
                return configDir;

            var cwd = Path.Combine(Directory.GetCurrentDirectory(), "config");
            if (Directory.Exists(cwd))
                return cwd;

            return configDir;
        }
    }
}
