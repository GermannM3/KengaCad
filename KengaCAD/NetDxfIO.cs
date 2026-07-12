using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Windows.Media;
using netDxf;
using netDxf.Entities;
using SkiaSharp;
using DxfLine = netDxf.Entities.Line;
using WpfColor = System.Windows.Media.Color;

namespace KengaCAD
{
    public static class NetDxfIO
    {
        public static List<CadEntity> Import(string filePath)
        {
            var doc = DxfDocument.Load(filePath);
            var result = new List<CadEntity>();
            foreach (var line in doc.Entities.Lines)
                result.Add(new LineEntity(
                    new SKPoint((float)line.StartPoint.X, (float)line.StartPoint.Y),
                    new SKPoint((float)line.EndPoint.X, (float)line.EndPoint.Y),
                    ToWpfColor(line.Color), line.Layer.Name));
            foreach (var circle in doc.Entities.Circles)
                result.Add(new CircleEntity(
                    new SKPoint((float)circle.Center.X, (float)circle.Center.Y),
                    (float)circle.Radius, ToWpfColor(circle.Color), circle.Layer.Name));
            foreach (var arc in doc.Entities.Arcs)
            {
                float start = (float)arc.StartAngle;
                float end = (float)arc.EndAngle;
                float sweep = end - start;
                if (sweep < 0) sweep += 360;
                result.Add(new ArcEntity(
                    new SKPoint((float)arc.Center.X, (float)arc.Center.Y),
                    (float)arc.Radius, start, sweep, ToWpfColor(arc.Color), arc.Layer.Name));
            }
            foreach (var pl in doc.Entities.Polylines2D)
            {
                var pts = pl.Vertexes.Select(v => new SKPoint((float)v.Position.X, (float)v.Position.Y)).ToList();
                if (pts.Count >= 2)
                    result.Add(new PolylineEntity(pts, ToWpfColor(pl.Color), pl.Layer.Name));
            }
            foreach (var pl3 in doc.Entities.Polylines3D)
            {
                var pts = pl3.Vertexes.Select(v => new SKPoint((float)v.X, (float)v.Y)).ToList();
                if (pts.Count >= 2)
                    result.Add(new PolylineEntity(pts, ToWpfColor(pl3.Color), pl3.Layer.Name));
            }
            foreach (var text in doc.Entities.Texts)
                result.Add(new TextEntity(
                    new SKPoint((float)text.Position.X, (float)text.Position.Y),
                    text.Value, ToWpfColor(text.Color), text.Layer.Name, (float)text.Height));
            return result;
        }

        public static void Export(string filePath, IEnumerable<CadEntity> entities)
        {
            var doc = new DxfDocument();
            foreach (var ent in entities)
            {
                switch (ent)
                {
                    case LineEntity l:
                        doc.Entities.Add(new DxfLine(
                            new netDxf.Vector3(l.Start.X, l.Start.Y, 0),
                            new netDxf.Vector3(l.End.X, l.End.Y, 0)) { Layer = new netDxf.Tables.Layer(ent.Layer) });
                        break;
                    case CircleEntity c:
                        doc.Entities.Add(new Circle(
                            new netDxf.Vector3(c.Center.X, c.Center.Y, 0), c.Radius)
                        { Layer = new netDxf.Tables.Layer(ent.Layer) });
                        break;
                    case ArcEntity a:
                        doc.Entities.Add(new Arc(
                            new netDxf.Vector3(a.Center.X, a.Center.Y, 0), a.Radius,
                            a.StartAngle, a.StartAngle + a.SweepAngle)
                        { Layer = new netDxf.Tables.Layer(ent.Layer) });
                        break;
                    case PolylineEntity pl when pl.Points.Count >= 2:
                        var poly = new Polyline2D(pl.Points.Select(p => new Polyline2DVertex(p.X, p.Y)).ToList(), false);
                        poly.Layer = new netDxf.Tables.Layer(ent.Layer);
                        doc.Entities.Add(poly);
                        break;
                    case RectangleEntity r:
                        doc.Entities.Add(new DxfLine(new netDxf.Vector3(r.X0, r.Y0, 0), new netDxf.Vector3(r.X1, r.Y0, 0)));
                        doc.Entities.Add(new DxfLine(new netDxf.Vector3(r.X1, r.Y0, 0), new netDxf.Vector3(r.X1, r.Y1, 0)));
                        doc.Entities.Add(new DxfLine(new netDxf.Vector3(r.X1, r.Y1, 0), new netDxf.Vector3(r.X0, r.Y1, 0)));
                        doc.Entities.Add(new DxfLine(new netDxf.Vector3(r.X0, r.Y1, 0), new netDxf.Vector3(r.X0, r.Y0, 0)));
                        break;
                    case TextEntity t:
                        doc.Entities.Add(new Text(t.Text, new netDxf.Vector3(t.Position.X, t.Position.Y, 0), t.Height));
                        break;
                }
            }
            doc.Save(filePath);
        }

        private static WpfColor ToWpfColor(netDxf.AciColor color)
        {
            var c = color.ToColor();
            return WpfColor.FromRgb(c.R, c.G, c.B);
        }
    }
}
