using System;
using System.IO;

namespace KengaCAD
{
    /// <summary>Подсказки по импорту CAD без внешних конвертеров.</summary>
    public static class CadImportHints
    {
        public const string DxfNative = "DXF читается напрямую (Save As DXF в AutoCAD/FreeCAD).";

        public static string DwgHint =>
            "DWG: встроенного чтения нет. Сохраните как DXF или укажите ODA File Converter в config/settings.json.";

        public static string StepHint =>
            "STEP/IGES: для mesh-импорта укажите FreeCAD в config/settings.json, либо конвертируйте в STL/OBJ офлайн.";

        public static bool IsNativeDxf(string path)
            => path.EndsWith(".dxf", StringComparison.OrdinalIgnoreCase);

        public static bool IsNativeMesh(string path)
        {
            var ext = Path.GetExtension(path).ToLowerInvariant();
            return ext is ".stl" or ".obj" or ".gltf" or ".glb";
        }
    }
}
