using System.Collections.Generic;
using System.IO;
using SkiaSharp;

namespace KengaCAD
{
    public static class PdfExporter
    {
        public static bool ExportDrawing(IEnumerable<CadEntity> entities, string filePath, float width = 1200, float height = 800)
        {
            using var stream = File.OpenWrite(filePath);
            using var doc = SKDocument.CreatePdf(stream, new SKDocumentPdfMetadata
            {
                Title = "KengaCAD Drawing",
                Author = "KengaCAD Professional",
                Creator = "KengaCAD Professional v2.1"
            });
            using var canvas = doc.BeginPage(width, height);
            canvas.Clear(SKColor.Parse("#FFFFFF"));
            canvas.Translate(40, 40);
            float scale = ComputeScale(entities, width - 80, height - 80);
            canvas.Scale(scale, scale);
            foreach (var ent in entities)
            {
                var clone = ent.Clone();
                if (clone.Color.R + clone.Color.G + clone.Color.B > 600)
                    clone.Color = System.Windows.Media.Colors.Black;
                clone.Draw(canvas);
            }
            doc.EndPage();
            doc.Close();
            return true;
        }

        private static float ComputeScale(IEnumerable<CadEntity> entities, float viewW, float viewH)
        {
            float minX = float.MaxValue, minY = float.MaxValue, maxX = float.MinValue, maxY = float.MinValue;
            foreach (var e in entities)
            {
                e.GetBounds(out float x0, out float y0, out float x1, out float y1);
                minX = System.Math.Min(minX, x0); minY = System.Math.Min(minY, y0);
                maxX = System.Math.Max(maxX, x1); maxY = System.Math.Max(maxY, y1);
            }
            float w = System.Math.Max(50, maxX - minX);
            float h = System.Math.Max(50, maxY - minY);
            return System.Math.Min(viewW / w, viewH / h) * 0.9f;
        }
    }
}
