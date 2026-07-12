using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows.Media;
using SkiaSharp;

namespace KengaCAD
{
    public abstract class CadEntity
    {
        public Color Color { get; set; }
        public string Layer { get; set; } = "0";
        public bool IsSelected { get; set; }

        public abstract void Draw(SKCanvas canvas);
        public abstract bool IsHit(SKPoint point);
        public abstract CadEntity Clone();
        public abstract void GetBounds(out float minX, out float minY, out float maxX, out float maxY);
    }

    public class LineEntity : CadEntity
    {
        public SKPoint Start { get; set; }
        public SKPoint End { get; set; }

        public LineEntity(SKPoint start, SKPoint end, Color color, string layer)
        {
            Start = start;
            End = end;
            Color = color;
            Layer = layer;
        }

        public override CadEntity Clone() => new LineEntity(Start, End, Color, Layer);

        public override void GetBounds(out float minX, out float minY, out float maxX, out float maxY)
        {
            minX = Math.Min(Start.X, End.X);
            minY = Math.Min(Start.Y, End.Y);
            maxX = Math.Max(Start.X, End.X);
            maxY = Math.Max(Start.Y, End.Y);
        }

        public override void Draw(SKCanvas canvas)
        {
            using var paint = CreatePaint();
            canvas.DrawLine(Start, End, paint);
            if (IsSelected) DrawEndpoints(canvas);
        }

        public override bool IsHit(SKPoint point) =>
            CadGeometry.DistancePointToSegment(point, Start, End) < 10;

        private SKPaint CreatePaint() => new()
        {
            Color = CadEntitySkia.ToSkColor(Color),
            StrokeWidth = IsSelected ? 3f : 2f,
            IsAntialias = true,
            IsStroke = true
        };

        private void DrawEndpoints(SKCanvas canvas)
        {
            using var sel = new SKPaint { Color = SKColors.Cyan, StrokeWidth = 1f, IsAntialias = true, IsStroke = true };
            canvas.DrawCircle(Start, 5, sel);
            canvas.DrawCircle(End, 5, sel);
        }
    }

    public class CircleEntity : CadEntity
    {
        public SKPoint Center { get; set; }
        public float Radius { get; set; }

        public CircleEntity(SKPoint center, float radius, Color color, string layer)
        {
            Center = center;
            Radius = radius;
            Color = color;
            Layer = layer;
        }

        public override CadEntity Clone() => new CircleEntity(Center, Radius, Color, Layer);

        public override void GetBounds(out float minX, out float minY, out float maxX, out float maxY)
        {
            minX = Center.X - Radius;
            minY = Center.Y - Radius;
            maxX = Center.X + Radius;
            maxY = Center.Y + Radius;
        }

        public override void Draw(SKCanvas canvas)
        {
            using var paint = new SKPaint
            {
                Color = CadEntitySkia.ToSkColor(Color),
                StrokeWidth = IsSelected ? 3f : 2f,
                IsAntialias = true,
                IsStroke = true
            };
            canvas.DrawCircle(Center, Radius, paint);
            if (IsSelected)
            {
                using var sel = new SKPaint { Color = SKColors.Cyan, StrokeWidth = 1f, IsAntialias = true, IsStroke = true };
                canvas.DrawCircle(Center, Radius + 5, sel);
            }
        }

        public override bool IsHit(SKPoint point) =>
            Math.Abs(SKPoint.Distance(point, Center) - Radius) < 10;
    }

    public class RectangleEntity : CadEntity
    {
        public float X0 { get; set; }
        public float Y0 { get; set; }
        public float X1 { get; set; }
        public float Y1 { get; set; }

        public RectangleEntity(SKPoint a, SKPoint b, Color color, string layer)
        {
            X0 = Math.Min(a.X, b.X);
            Y0 = Math.Min(a.Y, b.Y);
            X1 = Math.Max(a.X, b.X);
            Y1 = Math.Max(a.Y, b.Y);
            Color = color;
            Layer = layer;
        }

        public override CadEntity Clone() => new RectangleEntity(new SKPoint(X0, Y0), new SKPoint(X1, Y1), Color, Layer);

        public override void GetBounds(out float minX, out float minY, out float maxX, out float maxY)
        {
            minX = X0; minY = Y0; maxX = X1; maxY = Y1;
        }

        public override void Draw(SKCanvas canvas)
        {
            using var paint = new SKPaint
            {
                Color = CadEntitySkia.ToSkColor(Color),
                StrokeWidth = IsSelected ? 3f : 2f,
                IsAntialias = true,
                IsStroke = true
            };
            canvas.DrawLine(X0, Y0, X1, Y0, paint);
            canvas.DrawLine(X1, Y0, X1, Y1, paint);
            canvas.DrawLine(X1, Y1, X0, Y1, paint);
            canvas.DrawLine(X0, Y1, X0, Y0, paint);
        }

        public override bool IsHit(SKPoint point)
        {
            if (point.X < X0 - 5 || point.X > X1 + 5 || point.Y < Y0 - 5 || point.Y > Y1 + 5) return false;
            float d = 5;
            return point.X <= X0 + d || point.X >= X1 - d || point.Y <= Y0 + d || point.Y >= Y1 - d;
        }
    }

    public class PolylineEntity : CadEntity
    {
        public List<SKPoint> Points { get; }

        public PolylineEntity(List<SKPoint> points, Color color, string layer)
        {
            Points = new List<SKPoint>(points);
            Color = color;
            Layer = layer;
        }

        public override CadEntity Clone() => new PolylineEntity(Points, Color, Layer);

        public override void GetBounds(out float minX, out float minY, out float maxX, out float maxY)
        {
            minX = minY = float.MaxValue;
            maxX = maxY = float.MinValue;
            foreach (var p in Points)
            {
                minX = Math.Min(minX, p.X); maxX = Math.Max(maxX, p.X);
                minY = Math.Min(minY, p.Y); maxY = Math.Max(maxY, p.Y);
            }
            if (Points.Count == 0) { minX = minY = maxX = maxY = 0; }
        }

        public override void Draw(SKCanvas canvas)
        {
            if (Points.Count < 2) return;
            using var paint = new SKPaint
            {
                Color = CadEntitySkia.ToSkColor(Color),
                StrokeWidth = IsSelected ? 3f : 2f,
                IsAntialias = true,
                IsStroke = true
            };
            for (int i = 0; i < Points.Count - 1; i++)
                canvas.DrawLine(Points[i], Points[i + 1], paint);
        }

        public override bool IsHit(SKPoint point)
        {
            for (int i = 0; i < Points.Count - 1; i++)
                if (CadGeometry.DistancePointToSegment(point, Points[i], Points[i + 1]) < 10)
                    return true;
            return false;
        }
    }

    public class ArcEntity : CadEntity
    {
        public SKPoint Center { get; set; }
        public float Radius { get; set; }
        public float StartAngle { get; set; }
        public float SweepAngle { get; set; }

        public ArcEntity(SKPoint center, float radius, float startAngle, float sweepAngle, Color color, string layer)
        {
            Center = center;
            Radius = radius;
            StartAngle = startAngle;
            SweepAngle = sweepAngle;
            Color = color;
            Layer = layer;
        }

        public override CadEntity Clone() => new ArcEntity(Center, Radius, StartAngle, SweepAngle, Color, Layer);

        public override void GetBounds(out float minX, out float minY, out float maxX, out float maxY)
        {
            minX = Center.X - Radius;
            minY = Center.Y - Radius;
            maxX = Center.X + Radius;
            maxY = Center.Y + Radius;
        }

        public static ArcEntity? From3Points(SKPoint p1, SKPoint p2, SKPoint p3, Color color, string layer)
        {
            float ax = p1.X, ay = p1.Y;
            float bx = p2.X, by = p2.Y;
            float cx = p3.X, cy = p3.Y;
            float D = 2f * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by));
            if (Math.Abs(D) < 1e-6f) return null;

            float ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / D;
            float uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / D;
            var center = new SKPoint(ux, uy);
            float radius = SKPoint.Distance(center, p1);

            float a1 = (float)(Math.Atan2(ay - uy, ax - ux) * 180.0 / Math.PI);
            float a2 = (float)(Math.Atan2(by - uy, bx - ux) * 180.0 / Math.PI);
            float a3 = (float)(Math.Atan2(cy - uy, cx - ux) * 180.0 / Math.PI);
            float sweep = SweepThrough(a1, a2, a3);
            return new ArcEntity(center, radius, a1, sweep, color, layer);
        }

        private static float NormAngle(float a)
        {
            a %= 360f;
            if (a < 0) a += 360f;
            return a;
        }

        private static float SweepThrough(float startDeg, float midDeg, float endDeg)
        {
            float s = NormAngle(startDeg);
            float m = NormAngle(midDeg);
            float e = NormAngle(endDeg);
            float ccw = NormAngle(e - s);
            float cw = -(360f - ccw);
            float midCcw = NormAngle(m - s);
            return midCcw <= ccw ? ccw : cw;
        }

        public override void Draw(SKCanvas canvas)
        {
            using var paint = new SKPaint
            {
                Color = CadEntitySkia.ToSkColor(Color),
                StrokeWidth = IsSelected ? 3f : 2f,
                IsAntialias = true,
                IsStroke = true,
                Style = SKPaintStyle.Stroke
            };
            var rect = new SKRect(Center.X - Radius, Center.Y - Radius, Center.X + Radius, Center.Y + Radius);
            using var path = new SKPath();
            path.AddArc(rect, StartAngle, SweepAngle);
            canvas.DrawPath(path, paint);
            if (IsSelected)
            {
                using var sel = new SKPaint { Color = SKColors.Cyan, StrokeWidth = 1f, IsAntialias = true, IsStroke = true };
                canvas.DrawCircle(Center, 5, sel);
            }
        }

        public override bool IsHit(SKPoint point)
        {
            float dist = SKPoint.Distance(point, Center);
            if (Math.Abs(dist - Radius) > 10) return false;
            float angle = NormAngle((float)(Math.Atan2(point.Y - Center.Y, point.X - Center.X) * 180.0 / Math.PI));
            float s = NormAngle(StartAngle);
            float sweep = SweepAngle;
            if (sweep >= 0)
                return NormAngle(angle - s) <= sweep;
            return NormAngle(s - angle) <= -sweep;
        }
    }

    public class TextEntity : CadEntity
    {
        public SKPoint Position { get; set; }
        public string Text { get; set; }
        public float Height { get; set; } = 24f;

        public TextEntity(SKPoint position, string text, Color color, string layer, float height = 24f)
        {
            Position = position;
            Text = text;
            Height = height;
            Color = color;
            Layer = layer;
        }

        public override CadEntity Clone() => new TextEntity(Position, Text, Color, Layer, Height);

        public override void GetBounds(out float minX, out float minY, out float maxX, out float maxY)
        {
            minX = Position.X;
            minY = Position.Y - Height;
            maxX = Position.X + Text.Length * Height * 0.6f;
            maxY = Position.Y;
        }

        public override void Draw(SKCanvas canvas)
        {
            using var paint = new SKPaint
            {
                Color = CadEntitySkia.ToSkColor(Color),
                TextSize = Height,
                IsAntialias = true,
                IsStroke = false
            };
            canvas.DrawText(Text, Position.X, Position.Y, paint);
            if (IsSelected)
            {
                GetBounds(out float minX, out float minY, out float maxX, out float maxY);
                using var sel = new SKPaint { Color = SKColors.Cyan, StrokeWidth = 1f, IsAntialias = true, IsStroke = true };
                canvas.DrawRect(minX - 2, minY - 2, maxX - minX + 4, maxY - minY + 4, sel);
            }
        }

        public override bool IsHit(SKPoint point)
        {
            GetBounds(out float minX, out float minY, out float maxX, out float maxY);
            return point.X >= minX - 5 && point.X <= maxX + 5 && point.Y >= minY - 5 && point.Y <= maxY + 5;
        }
    }

    public class DimLinearEntity : CadEntity
    {
        public SKPoint P1 { get; set; }
        public SKPoint P2 { get; set; }
        public SKPoint DimLinePoint { get; set; }

        public DimLinearEntity(SKPoint p1, SKPoint p2, SKPoint dimLinePoint, Color color, string layer)
        {
            P1 = p1; P2 = p2; DimLinePoint = dimLinePoint;
            Color = color; Layer = layer;
        }

        public override CadEntity Clone() => new DimLinearEntity(P1, P2, DimLinePoint, Color, Layer);

        public override void GetBounds(out float minX, out float minY, out float maxX, out float maxY)
        {
            minX = Math.Min(Math.Min(P1.X, P2.X), DimLinePoint.X);
            minY = Math.Min(Math.Min(P1.Y, P2.Y), DimLinePoint.Y);
            maxX = Math.Max(Math.Max(P1.X, P2.X), DimLinePoint.X);
            maxY = Math.Max(Math.Max(P1.Y, P2.Y), DimLinePoint.Y);
        }

        public override void Draw(SKCanvas canvas)
        {
            float dist = SKPoint.Distance(P1, P2);
            using var paint = new SKPaint
            {
                Color = CadEntitySkia.ToSkColor(Color),
                StrokeWidth = IsSelected ? 2f : 1f,
                IsAntialias = true,
                IsStroke = true
            };
            using var textPaint = new SKPaint
            {
                Color = CadEntitySkia.ToSkColor(Color),
                TextSize = 14f,
                IsAntialias = true
            };
            canvas.DrawLine(P1, P2, paint);
            var mid = new SKPoint((P1.X + P2.X) * 0.5f, (P1.Y + P2.Y) * 0.5f);
            canvas.DrawLine(mid, DimLinePoint, paint);
            canvas.DrawText($"{dist:F1}", DimLinePoint.X, DimLinePoint.Y - 4, textPaint);
        }

        public override bool IsHit(SKPoint point) =>
            CadGeometry.DistancePointToSegment(point, P1, P2) < 10 ||
            CadGeometry.DistancePointToSegment(point, new SKPoint((P1.X + P2.X) * 0.5f, (P1.Y + P2.Y) * 0.5f), DimLinePoint) < 10;
    }

    public class DimRadiusEntity : CadEntity
    {
        public SKPoint Center { get; set; }
        public float Radius { get; set; }
        public SKPoint LabelPoint { get; set; }

        public DimRadiusEntity(SKPoint center, float radius, SKPoint labelPoint, Color color, string layer)
        {
            Center = center; Radius = radius; LabelPoint = labelPoint;
            Color = color; Layer = layer;
        }

        public override CadEntity Clone() => new DimRadiusEntity(Center, Radius, LabelPoint, Color, Layer);

        public override void GetBounds(out float minX, out float minY, out float maxX, out float maxY)
        {
            minX = Math.Min(Center.X - Radius, LabelPoint.X);
            minY = Math.Min(Center.Y - Radius, LabelPoint.Y);
            maxX = Math.Max(Center.X + Radius, LabelPoint.X);
            maxY = Math.Max(Center.Y + Radius, LabelPoint.Y);
        }

        public override void Draw(SKCanvas canvas)
        {
            using var paint = new SKPaint
            {
                Color = CadEntitySkia.ToSkColor(Color),
                StrokeWidth = IsSelected ? 2f : 1f,
                IsAntialias = true,
                IsStroke = true
            };
            using var textPaint = new SKPaint { Color = CadEntitySkia.ToSkColor(Color), TextSize = 14f, IsAntialias = true };
            var edge = new SKPoint(Center.X + Radius, Center.Y);
            canvas.DrawLine(Center, edge, paint);
            canvas.DrawLine(edge, LabelPoint, paint);
            canvas.DrawText($"R{Radius:F1}", LabelPoint.X, LabelPoint.Y - 4, textPaint);
        }

        public override bool IsHit(SKPoint point) =>
            CadGeometry.DistancePointToSegment(point, Center, new SKPoint(Center.X + Radius, Center.Y)) < 10;
    }

    public class CadBlockDefinition
    {
        public string Name { get; set; } = "";
        public List<CadEntity> Entities { get; set; } = new();
        public SKPoint BasePoint { get; set; }
    }

    internal static class CadEntitySkia
    {
        internal static SKColor ToSkColor(Color color) =>
            SKColor.Parse($"#{color.R:X2}{color.G:X2}{color.B:X2}");
    }
}
