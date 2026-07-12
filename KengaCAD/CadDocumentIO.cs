using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Windows.Media;
using SkiaSharp;

namespace KengaCAD
{
    public class CadDocumentDto
    {
        public string Version { get; set; } = "2.1.0";
        public List<CadEntityDto> Entities { get; set; } = new();
        public List<CadBlockDto> Blocks { get; set; } = new();
    }

    public class CadEntityDto
    {
        public string Type { get; set; } = "";
        public string Layer { get; set; } = "0";
        public string Color { get; set; } = "White";
        public float X0 { get; set; }
        public float Y0 { get; set; }
        public float X1 { get; set; }
        public float Y1 { get; set; }
        public float Radius { get; set; }
        public float StartAngle { get; set; }
        public float SweepAngle { get; set; }
        public List<float[]>? Points { get; set; }
        public string? Text { get; set; }
        public float TextHeight { get; set; } = 24f;
    }

    public class CadBlockDto
    {
        public string Name { get; set; } = "";
        public float BaseX { get; set; }
        public float BaseY { get; set; }
        public List<CadEntityDto> Entities { get; set; } = new();
    }

    public static class CadDocumentIO
    {
        public static string SaveNative(string path, IEnumerable<CadEntity> entities, IEnumerable<CadBlockDefinition> blocks)
        {
            var dto = new CadDocumentDto
            {
                Entities = entities.Select(ToDto).ToList(),
                Blocks = blocks.Select(b => new CadBlockDto
                {
                    Name = b.Name,
                    BaseX = b.BasePoint.X,
                    BaseY = b.BasePoint.Y,
                    Entities = b.Entities.Select(ToDto).ToList()
                }).ToList()
            };
            var json = JsonSerializer.Serialize(dto, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(path, json);
            return path;
        }

        public static (List<CadEntity> entities, List<CadBlockDefinition> blocks) LoadNative(string path)
        {
            var json = File.ReadAllText(path);
            var dto = JsonSerializer.Deserialize<CadDocumentDto>(json)
                ?? throw new InvalidDataException("Некорректный файл KengaCAD.");
            var entities = dto.Entities.Select(FromDto).Where(e => e != null).Cast<CadEntity>().ToList();
            var blocks = dto.Blocks.Select(b => new CadBlockDefinition
            {
                Name = b.Name,
                BasePoint = new SKPoint(b.BaseX, b.BaseY),
                Entities = b.Entities.Select(FromDto).Where(e => e != null).Cast<CadEntity>().ToList()
            }).ToList();
            return (entities, blocks);
        }

        public static List<CadEntity> ImportDxf(string path) => NetDxfIO.Import(path);

        public static void ExportDxf(string path, IEnumerable<CadEntity> entities) => NetDxfIO.Export(path, entities);

        private static CadEntityDto ToDto(CadEntity ent)
        {
            var dto = new CadEntityDto { Layer = ent.Layer, Color = ent.Color.ToString() };
            switch (ent)
            {
                case LineEntity l:
                    dto.Type = "LINE"; dto.X0 = l.Start.X; dto.Y0 = l.Start.Y; dto.X1 = l.End.X; dto.Y1 = l.End.Y; break;
                case CircleEntity c:
                    dto.Type = "CIRCLE"; dto.X0 = c.Center.X; dto.Y0 = c.Center.Y; dto.Radius = c.Radius; break;
                case ArcEntity a:
                    dto.Type = "ARC"; dto.X0 = a.Center.X; dto.Y0 = a.Center.Y; dto.Radius = a.Radius;
                    dto.StartAngle = a.StartAngle; dto.SweepAngle = a.SweepAngle; break;
                case RectangleEntity r:
                    dto.Type = "RECT"; dto.X0 = r.X0; dto.Y0 = r.Y0; dto.X1 = r.X1; dto.Y1 = r.Y1; break;
                case PolylineEntity pl:
                    dto.Type = "POLYLINE"; dto.Points = pl.Points.Select(p => new[] { p.X, p.Y }).ToList(); break;
                case TextEntity t:
                    dto.Type = "TEXT"; dto.X0 = t.Position.X; dto.Y0 = t.Position.Y; dto.Text = t.Text; dto.TextHeight = t.Height; break;
                case DimLinearEntity d:
                    dto.Type = "DIMLINEAR"; dto.X0 = d.P1.X; dto.Y0 = d.P1.Y; dto.X1 = d.P2.X; dto.Y1 = d.P2.Y;
                    dto.Radius = d.DimLinePoint.X; dto.StartAngle = d.DimLinePoint.Y; break;
                case DimRadiusEntity dr:
                    dto.Type = "DIMRADIUS"; dto.X0 = dr.Center.X; dto.Y0 = dr.Center.Y; dto.Radius = dr.Radius;
                    dto.X1 = dr.LabelPoint.X; dto.Y1 = dr.LabelPoint.Y; break;
            }
            return dto;
        }

        private static CadEntity? FromDto(CadEntityDto dto)
        {
            var color = (Color)ColorConverter.ConvertFromString(dto.Color);
            return dto.Type switch
            {
                "LINE" => new LineEntity(new SKPoint(dto.X0, dto.Y0), new SKPoint(dto.X1, dto.Y1), color, dto.Layer),
                "CIRCLE" => new CircleEntity(new SKPoint(dto.X0, dto.Y0), dto.Radius, color, dto.Layer),
                "ARC" => new ArcEntity(new SKPoint(dto.X0, dto.Y0), dto.Radius, dto.StartAngle, dto.SweepAngle, color, dto.Layer),
                "RECT" => new RectangleEntity(new SKPoint(dto.X0, dto.Y0), new SKPoint(dto.X1, dto.Y1), color, dto.Layer),
                "POLYLINE" => new PolylineEntity(dto.Points?.Select(p => new SKPoint(p[0], p[1])).ToList() ?? new(), color, dto.Layer),
                "TEXT" => new TextEntity(new SKPoint(dto.X0, dto.Y0), dto.Text ?? "", color, dto.Layer, dto.TextHeight),
                "DIMLINEAR" => new DimLinearEntity(new SKPoint(dto.X0, dto.Y0), new SKPoint(dto.X1, dto.Y1),
                    new SKPoint(dto.Radius, dto.StartAngle), color, dto.Layer),
                "DIMRADIUS" => new DimRadiusEntity(new SKPoint(dto.X0, dto.Y0), dto.Radius,
                    new SKPoint(dto.X1, dto.Y1), color, dto.Layer),
                _ => null
            };
        }
    }
}
