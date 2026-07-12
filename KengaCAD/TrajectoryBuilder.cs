using System;
using System.Collections.Generic;
using System.Linq;
using SkiaSharp;

namespace KengaCAD
{
    public static class TrajectoryBuilder
    {
        public static List<SKPoint> CollectPolylinePoints(IEnumerable<CadEntity> entities)
        {
            var pts = new List<SKPoint>();
            foreach (var ent in entities)
            {
                if (ent is PolylineEntity pl)
                {
                    foreach (var p in pl.Points)
                    {
                        if (pts.Count == 0 || SKPoint.Distance(pts[^1], p) > 0.5f)
                            pts.Add(p);
                    }
                }
                else if (ent is LineEntity line)
                {
                    if (pts.Count == 0 || SKPoint.Distance(pts[^1], line.Start) > 0.5f)
                        pts.Add(line.Start);
                    pts.Add(line.End);
                }
            }
            return pts;
        }

        public static List<SKPoint> CatmullRomSpline(IReadOnlyList<SKPoint> control, int segmentsPerSpan = 8)
        {
            if (control.Count < 2) return control.ToList();
            var result = new List<SKPoint>();
            for (int i = 0; i < control.Count - 1; i++)
            {
                var p0 = i > 0 ? control[i - 1] : control[i];
                var p1 = control[i];
                var p2 = control[i + 1];
                var p3 = i + 2 < control.Count ? control[i + 2] : control[i + 1];
                for (int s = 0; s < segmentsPerSpan; s++)
                {
                    float t = s / (float)segmentsPerSpan;
                    result.Add(EvalCatmull(p0, p1, p2, p3, t));
                }
            }
            result.Add(control[^1]);
            return result;
        }

        private static SKPoint EvalCatmull(SKPoint p0, SKPoint p1, SKPoint p2, SKPoint p3, float t)
        {
            float t2 = t * t, t3 = t2 * t;
            float x = 0.5f * ((2 * p1.X) + (-p0.X + p2.X) * t +
                (2 * p0.X - 5 * p1.X + 4 * p2.X - p3.X) * t2 +
                (-p0.X + 3 * p1.X - 3 * p2.X + p3.X) * t3);
            float y = 0.5f * ((2 * p1.Y) + (-p0.Y + p2.Y) * t +
                (2 * p0.Y - 5 * p1.Y + 4 * p2.Y - p3.Y) * t2 +
                (-p0.Y + 3 * p1.Y - 3 * p2.Y + p3.Y) * t3);
            return new SKPoint(x, y);
        }

        public static List<SKPoint> ChaikinSmooth(IReadOnlyList<SKPoint> points, int iterations = 2)
        {
            if (points.Count < 3) return points.ToList();
            var current = points.ToList();
            for (int iter = 0; iter < iterations; iter++)
            {
                var next = new List<SKPoint> { current[0] };
                for (int i = 0; i < current.Count - 1; i++)
                {
                    var a = current[i];
                    var b = current[i + 1];
                    next.Add(new SKPoint(a.X * 0.75f + b.X * 0.25f, a.Y * 0.75f + b.Y * 0.25f));
                    next.Add(new SKPoint(a.X * 0.25f + b.X * 0.75f, a.Y * 0.25f + b.Y * 0.75f));
                }
                next.Add(current[^1]);
                current = next;
            }
            return current;
        }

        public static List<SKPoint> ArchimedeanSpiral(SKPoint center, float innerRadius, float outerRadius, int turns, int pointsPerTurn = 24)
        {
            var result = new List<SKPoint>();
            int total = Math.Max(2, turns * pointsPerTurn);
            float dr = (outerRadius - innerRadius) / total;
            for (int i = 0; i <= total; i++)
            {
                float angle = (float)(i * turns * 2 * Math.PI / total);
                float r = innerRadius + dr * i;
                result.Add(new SKPoint(center.X + r * (float)Math.Cos(angle), center.Y + r * (float)Math.Sin(angle)));
            }
            return result;
        }

        public static PolylineEntity? BuildTrajectoryPolyline(IEnumerable<CadEntity> entities, string mode, SKPoint? spiralCenter = null)
        {
            var control = CollectPolylinePoints(entities);
            if (control.Count < 2) return null;

            List<SKPoint> pts = mode switch
            {
                "SPLINE" => CatmullRomSpline(control),
                "SMOOTH" => ChaikinSmooth(control),
                "SPIRAL" => ArchimedeanSpiral(
                    spiralCenter ?? control[0],
                    SKPoint.Distance(control[0], control[1]) * 0.2f,
                    SKPoint.Distance(control[0], control[^1]),
                    3),
                _ => control
            };
            return new PolylineEntity(pts, System.Windows.Media.Colors.LimeGreen, "Trajectory");
        }
    }
}
