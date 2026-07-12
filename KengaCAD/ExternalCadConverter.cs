using System;
using System.Diagnostics;
using System.IO;
using System.Text.Json;

namespace KengaCAD
{
    /// <summary>Конвертация DWG/STEP через ODA File Converter или FreeCAD (если установлены).</summary>
    public static class ExternalCadConverter
    {
        public static string? TryConvertToDxf(string sourcePath, string targetFormat = "dxf")
        {
            var settings = LoadSettings();
            string ext = Path.GetExtension(sourcePath).ToLowerInvariant();
            string tempDir = Path.Combine(Path.GetTempPath(), "KengaCAD", Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(tempDir);

            if (TryOdaConvert(sourcePath, tempDir, settings, out var odaOut))
                return odaOut;

            if ((ext == ".step" || ext == ".stp" || ext == ".iges" || ext == ".igs") && TryFreeCadConvert(sourcePath, tempDir, settings, out var fcOut))
                return fcOut;

            return null;
        }

        public static string? TryConvertStepToStl(string stepPath)
        {
            var tempDir = Path.Combine(Path.GetTempPath(), "KengaCAD", Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(tempDir);
            var settings = LoadSettings();
            if (TryFreeCadConvert(stepPath, tempDir, settings, out var stlPath) && stlPath.EndsWith(".stl", StringComparison.OrdinalIgnoreCase))
                return stlPath;
            return null;
        }

        private static bool TryOdaConvert(string input, string outDir, CadSettings settings, out string? outputPath)
        {
            outputPath = null;
            var oda = settings.OdaConverterPath;
            if (string.IsNullOrWhiteSpace(oda) || !File.Exists(oda)) return false;
            try
            {
                var inDir = Path.GetDirectoryName(input)!;
                var outFmt = "ACAD2018";
                var psi = new ProcessStartInfo(oda, $"\"{inDir}\" \"{outDir}\" \"{outFmt}\" \"DXF\" \"0\" \"1\" \"{Path.GetFileName(input)}\"")
                {
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                };
                using var p = Process.Start(psi);
                p?.WaitForExit(120000);
                var dxf = Path.Combine(outDir, Path.GetFileNameWithoutExtension(input) + ".dxf");
                if (File.Exists(dxf)) { outputPath = dxf; return true; }
            }
            catch { }
            return false;
        }

        private static bool TryFreeCadConvert(string input, string outDir, CadSettings settings, out string? outputPath)
        {
            outputPath = null;
            var freeCad = settings.FreeCadPath;
            if (string.IsNullOrWhiteSpace(freeCad) || !File.Exists(freeCad)) return false;
            string outFile = Path.Combine(outDir, Path.GetFileNameWithoutExtension(input) + ".stl");
            string py = $"import FreeCAD, Mesh, Part; doc=FreeCAD.newDocument(); Part.insert(r\"{input.Replace("\\", "\\\\")}\", doc.Name); doc.recompute(); objs=[o for o in doc.Objects if hasattr(o,'Shape')]; Mesh.export(objs, r\"{outFile.Replace("\\", "\\\\")}\"); FreeCAD.closeDocument(doc.Name)";
            try
            {
                var psi = new ProcessStartInfo(freeCad, $"-c \"{py}\"")
                {
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true
                };
                using var p = Process.Start(psi);
                p?.WaitForExit(180000);
                if (File.Exists(outFile)) { outputPath = outFile; return true; }
            }
            catch { }
            return false;
        }

        private static CadSettings LoadSettings()
        {
            try
            {
                var path = Path.Combine(PostprocessorEngine.GetConfigDirectory(), "settings.json");
                if (!File.Exists(path)) return new CadSettings();
                using var doc = JsonDocument.Parse(File.ReadAllText(path));
                var cad = doc.RootElement.TryGetProperty("cad", out var c) ? c : default;
                return new CadSettings
                {
                    OdaConverterPath = cad.TryGetProperty("oda_converter_path", out var o) ? o.GetString() ?? "" : "",
                    FreeCadPath = cad.TryGetProperty("freecad_path", out var f) ? f.GetString() ?? "" : ""
                };
            }
            catch { return new CadSettings(); }
        }

        private class CadSettings
        {
            public string OdaConverterPath { get; set; } = "";
            public string FreeCadPath { get; set; } = @"C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe";
        }
    }
}
