using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows.Media;
using SkiaSharp;

namespace KengaCAD
{
    public static class CadGeometry
    {
        public static float DistancePointToSegment(SKPoint p, SKPoint a, SKPoint b)
        {
            float dx = b.X - a.X, dy = b.Y - a.Y;
            float lenSq = dx * dx + dy * dy;
            if (lenSq < 1e-6f) return SKPoint.Distance(a, p);
            float t = Math.Clamp(((p.X - a.X) * dx + (p.Y - a.Y) * dy) / lenSq, 0, 1);
            var proj = new SKPoint(a.X + t * dx, a.Y + t * dy);
            return SKPoint.Distance(proj, p);
        }

        public static SKPoint RotatePoint(SKPoint p, SKPoint center, double angleRad)
        {
            double cos = Math.Cos(angleRad), sin = Math.Sin(angleRad);
            double dx = p.X - center.X, dy = p.Y - center.Y;
            return new SKPoint(
                (float)(center.X + dx * cos - dy * sin),
                (float)(center.Y + dx * sin + dy * cos));
        }

        public static void RotateEntity(CadEntity ent, SKPoint center, double angleRad)
        {
            switch (ent)
            {
                case LineEntity l:
                    l.Start = RotatePoint(l.Start, center, angleRad);
                    l.End = RotatePoint(l.End, center, angleRad);
                    break;
                case CircleEntity c:
                    c.Center = RotatePoint(c.Center, center, angleRad);
                    break;
                case RectangleEntity r:
                    var p0 = RotatePoint(new SKPoint(r.X0, r.Y0), center, angleRad);
                    var p1 = RotatePoint(new SKPoint(r.X1, r.Y1), center, angleRad);
                    r.X0 = Math.Min(p0.X, p1.X); r.Y0 = Math.Min(p0.Y, p1.Y);
                    r.X1 = Math.Max(p0.X, p1.X); r.Y1 = Math.Max(p0.Y, p1.Y);
                    break;
                case PolylineEntity pl:
                    for (int i = 0; i < pl.Points.Count; i++)
                        pl.Points[i] = RotatePoint(pl.Points[i], center, angleRad);
                    break;
                case ArcEntity a:
                    a.Center = RotatePoint(a.Center, center, angleRad);
                    a.StartAngle += (float)(angleRad * 180.0 / Math.PI);
                    break;
                case TextEntity t:
                    t.Position = RotatePoint(t.Position, center, angleRad);
                    break;
                case DimLinearEntity d:
                    d.P1 = RotatePoint(d.P1, center, angleRad);
                    d.P2 = RotatePoint(d.P2, center, angleRad);
                    d.DimLinePoint = RotatePoint(d.DimLinePoint, center, angleRad);
                    break;
                case DimRadiusEntity dr:
                    dr.Center = RotatePoint(dr.Center, center, angleRad);
                    dr.LabelPoint = RotatePoint(dr.LabelPoint, center, angleRad);
                    break;
            }
        }

        public static void ScaleEntity(CadEntity ent, SKPoint center, double factor)
        {
            SKPoint ScalePt(SKPoint p) => new(
                (float)(center.X + (p.X - center.X) * factor),
                (float)(center.Y + (p.Y - center.Y) * factor));

            switch (ent)
            {
                case LineEntity l:
                    l.Start = ScalePt(l.Start);
                    l.End = ScalePt(l.End);
                    break;
                case CircleEntity c:
                    c.Center = ScalePt(c.Center);
                    c.Radius = (float)(c.Radius * factor);
                    break;
                case RectangleEntity r:
                    var p0 = ScalePt(new SKPoint(r.X0, r.Y0));
                    var p1 = ScalePt(new SKPoint(r.X1, r.Y1));
                    r.X0 = Math.Min(p0.X, p1.X); r.Y0 = Math.Min(p0.Y, p1.Y);
                    r.X1 = Math.Max(p0.X, p1.X); r.Y1 = Math.Max(p0.Y, p1.Y);
                    break;
                case PolylineEntity pl:
                    for (int i = 0; i < pl.Points.Count; i++)
                        pl.Points[i] = ScalePt(pl.Points[i]);
                    break;
                case ArcEntity a:
                    a.Center = ScalePt(a.Center);
                    a.Radius = (float)(a.Radius * factor);
                    break;
                case TextEntity t:
                    t.Position = ScalePt(t.Position);
                    t.Height = (float)(t.Height * factor);
                    break;
                case DimLinearEntity d:
                    d.P1 = ScalePt(d.P1); d.P2 = ScalePt(d.P2); d.DimLinePoint = ScalePt(d.DimLinePoint);
                    break;
                case DimRadiusEntity dr:
                    dr.Center = ScalePt(dr.Center);
                    dr.Radius = (float)(dr.Radius * factor);
                    dr.LabelPoint = ScalePt(dr.LabelPoint);
                    break;
            }
        }

        public static void MirrorEntity(CadEntity ent, SKPoint a, SKPoint b)
        {
            SKPoint MirrorPt(SKPoint p)
            {
                float dx = b.X - a.X, dy = b.Y - a.Y;
                float lenSq = dx * dx + dy * dy;
                if (lenSq < 1e-6f) return p;
                float t = ((p.X - a.X) * dx + (p.Y - a.Y) * dy) / lenSq;
                var proj = new SKPoint(a.X + t * dx, a.Y + t * dy);
                return new SKPoint(2 * proj.X - p.X, 2 * proj.Y - p.Y);
            }

            switch (ent)
            {
                case LineEntity l:
                    l.Start = MirrorPt(l.Start);
                    l.End = MirrorPt(l.End);
                    break;
                case CircleEntity c:
                    c.Center = MirrorPt(c.Center);
                    break;
                case RectangleEntity r:
                    var p0 = MirrorPt(new SKPoint(r.X0, r.Y0));
                    var p1 = MirrorPt(new SKPoint(r.X1, r.Y1));
                    r.X0 = Math.Min(p0.X, p1.X); r.Y0 = Math.Min(p0.Y, p1.Y);
                    r.X1 = Math.Max(p0.X, p1.X); r.Y1 = Math.Max(p0.Y, p1.Y);
                    break;
                case PolylineEntity pl:
                    for (int i = 0; i < pl.Points.Count; i++)
                        pl.Points[i] = MirrorPt(pl.Points[i]);
                    break;
                case ArcEntity arc:
                    arc.Center = MirrorPt(arc.Center);
                    arc.StartAngle = -arc.StartAngle;
                    arc.SweepAngle = -arc.SweepAngle;
                    break;
                case TextEntity t:
                    t.Position = MirrorPt(t.Position);
                    break;
                case DimLinearEntity d:
                    d.P1 = MirrorPt(d.P1); d.P2 = MirrorPt(d.P2); d.DimLinePoint = MirrorPt(d.DimLinePoint);
                    break;
                case DimRadiusEntity dr:
                    dr.Center = MirrorPt(dr.Center);
                    dr.LabelPoint = MirrorPt(dr.LabelPoint);
                    break;
            }
        }

        public static void MoveEntity(CadEntity ent, SKPoint delta)
        {
            switch (ent)
            {
                case LineEntity l:
                    l.Start = new SKPoint(l.Start.X + delta.X, l.Start.Y + delta.Y);
                    l.End = new SKPoint(l.End.X + delta.X, l.End.Y + delta.Y);
                    break;
                case CircleEntity c:
                    c.Center = new SKPoint(c.Center.X + delta.X, c.Center.Y + delta.Y);
                    break;
                case RectangleEntity r:
                    r.X0 += delta.X; r.Y0 += delta.Y; r.X1 += delta.X; r.Y1 += delta.Y;
                    break;
                case PolylineEntity pl:
                    for (int i = 0; i < pl.Points.Count; i++)
                        pl.Points[i] = new SKPoint(pl.Points[i].X + delta.X, pl.Points[i].Y + delta.Y);
                    break;
                case ArcEntity a:
                    a.Center = new SKPoint(a.Center.X + delta.X, a.Center.Y + delta.Y);
                    break;
                case TextEntity t:
                    t.Position = new SKPoint(t.Position.X + delta.X, t.Position.Y + delta.Y);
                    break;
                case DimLinearEntity d:
                    d.P1 = new SKPoint(d.P1.X + delta.X, d.P1.Y + delta.Y);
                    d.P2 = new SKPoint(d.P2.X + delta.X, d.P2.Y + delta.Y);
                    d.DimLinePoint = new SKPoint(d.DimLinePoint.X + delta.X, d.DimLinePoint.Y + delta.Y);
                    break;
                case DimRadiusEntity dr:
                    dr.Center = new SKPoint(dr.Center.X + delta.X, dr.Center.Y + delta.Y);
                    dr.LabelPoint = new SKPoint(dr.LabelPoint.X + delta.X, dr.LabelPoint.Y + delta.Y);
                    break;
            }
        }

        public static CadEntity? CloneEntity(CadEntity ent, SKPoint delta)
        {
            var copy = ent.Clone();
            if (delta.X != 0 || delta.Y != 0)
                MoveEntity(copy, delta);
            return copy;
        }

        public static List<(SKPoint A, SKPoint B)> GetSegments(CadEntity ent)
        {
            var segs = new List<(SKPoint, SKPoint)>();
            switch (ent)
            {
                case LineEntity l:
                    segs.Add((l.Start, l.End));
                    break;
                case RectangleEntity r:
                    segs.Add((new(r.X0, r.Y0), new(r.X1, r.Y0)));
                    segs.Add((new(r.X1, r.Y0), new(r.X1, r.Y1)));
                    segs.Add((new(r.X1, r.Y1), new(r.X0, r.Y1)));
                    segs.Add((new(r.X0, r.Y1), new(r.X0, r.Y0)));
                    break;
                case PolylineEntity pl:
                    for (int i = 0; i < pl.Points.Count - 1; i++)
                        segs.Add((pl.Points[i], pl.Points[i + 1]));
                    break;
            }
            return segs;
        }

        public static bool TrySegmentIntersection(SKPoint a1, SKPoint a2, SKPoint b1, SKPoint b2, out SKPoint hit)
        {
            hit = default;
            float d = (a2.X - a1.X) * (b2.Y - b1.Y) - (a2.Y - a1.Y) * (b2.X - b1.X);
            if (Math.Abs(d) < 1e-6f) return false;
            float ua = ((b2.X - b1.X) * (a1.Y - b1.Y) - (b2.Y - b1.Y) * (a1.X - b1.X)) / d;
            float ub = ((a2.X - a1.X) * (a1.Y - b1.Y) - (a2.Y - a1.Y) * (a1.X - b1.X)) / d;
            if (ua < 0 || ua > 1 || ub < 0 || ub > 1) return false;
            hit = new SKPoint(a1.X + ua * (a2.X - a1.X), a1.Y + ua * (a2.Y - a1.Y));
            return true;
        }

        public static bool TryTrimLine(LineEntity line, CadEntity boundary, SKPoint pickPoint, out LineEntity? result)
        {
            result = null;
            var boundarySegs = GetSegments(boundary);
            var hits = new List<(SKPoint pt, float t)>();
            foreach (var (b1, b2) in boundarySegs)
            {
                if (TrySegmentIntersection(line.Start, line.End, b1, b2, out var hit))
                {
                    float t = ParamOnSegment(line.Start, line.End, hit);
                    if (t > 0.001f && t < 0.999f)
                        hits.Add((hit, t));
                }
            }
            if (hits.Count == 0) return false;

            float pickT = ParamOnSegment(line.Start, line.End, pickPoint);
            hits.Sort((x, y) => x.t.CompareTo(y.t));
            var nearest = hits.OrderBy(h => Math.Abs(h.t - pickT)).First();
            if (pickT < nearest.t)
                result = new LineEntity(line.Start, nearest.pt, line.Color, line.Layer);
            else
                result = new LineEntity(nearest.pt, line.End, line.Color, line.Layer);
            return result != null;
        }

        public static bool TryExtendLine(LineEntity line, CadEntity boundary, SKPoint pickPoint, out LineEntity? result)
        {
            result = null;
            var boundarySegs = GetSegments(boundary);
            var dir = new SKPoint(line.End.X - line.Start.X, line.End.Y - line.Start.Y);
            float len = (float)Math.Sqrt(dir.X * dir.X + dir.Y * dir.Y);
            if (len < 1e-6f) return false;
            dir = new SKPoint(dir.X / len, dir.Y / len);

            float pickTStart = SKPoint.Distance(pickPoint, line.Start);
            float pickTEnd = SKPoint.Distance(pickPoint, line.End);
            bool extendFromStart = pickTStart < pickTEnd;

            SKPoint rayStart = extendFromStart ? line.Start : line.End;
            SKPoint rayDir = extendFromStart ? new(-dir.X, -dir.Y) : dir;
            SKPoint rayEnd = new(rayStart.X + rayDir.X * 10000, rayStart.Y + rayDir.Y * 10000);

            SKPoint? bestHit = null;
            float bestDist = float.MaxValue;
            foreach (var (b1, b2) in boundarySegs)
            {
                if (TryRaySegmentIntersection(rayStart, rayEnd, b1, b2, out var hit))
                {
                    float d = SKPoint.Distance(rayStart, hit);
                    if (d > 1f && d < bestDist)
                    {
                        bestDist = d;
                        bestHit = hit;
                    }
                }
            }
            if (bestHit == null) return false;
            result = extendFromStart
                ? new LineEntity(bestHit.Value, line.End, line.Color, line.Layer)
                : new LineEntity(line.Start, bestHit.Value, line.Color, line.Layer);
            return true;
        }

        private static bool TryRaySegmentIntersection(SKPoint r1, SKPoint r2, SKPoint s1, SKPoint s2, out SKPoint hit)
        {
            hit = default;
            float rdx = r2.X - r1.X, rdy = r2.Y - r1.Y;
            float sdx = s2.X - s1.X, sdy = s2.Y - s1.Y;
            float d = rdx * sdy - rdy * sdx;
            if (Math.Abs(d) < 1e-6f) return false;
            float ua = ((s1.X - r1.X) * sdy - (s1.Y - r1.Y) * sdx) / d;
            float ub = ((s1.X - r1.X) * rdy - (s1.Y - r1.Y) * rdx) / d;
            if (ua < 0 || ub < 0 || ub > 1) return false;
            hit = new SKPoint(r1.X + ua * rdx, r1.Y + ua * rdy);
            return true;
        }

        private static float ParamOnSegment(SKPoint a, SKPoint b, SKPoint p)
        {
            float dx = b.X - a.X, dy = b.Y - a.Y;
            float lenSq = dx * dx + dy * dy;
            if (lenSq < 1e-6f) return 0;
            return Math.Clamp(((p.X - a.X) * dx + (p.Y - a.Y) * dy) / lenSq, 0, 1);
        }

        public static ArcEntity? TryFilletLines(LineEntity l1, LineEntity l2, float radius)
        {
            if (!TryLineIntersectionInfinite(l1, l2, out var corner)) return null;
            float d1 = SKPoint.Distance(corner, l1.Start) > SKPoint.Distance(corner, l1.End)
                ? SKPoint.Distance(corner, l1.Start) : SKPoint.Distance(corner, l1.End);
            float d2 = SKPoint.Distance(corner, l2.Start) > SKPoint.Distance(corner, l2.End)
                ? SKPoint.Distance(corner, l2.Start) : SKPoint.Distance(corner, l2.End);
            if (radius > d1 * 0.9f || radius > d2 * 0.9f || radius < 1f) return null;

            var dir1 = NormalizeAwayFrom(corner, l1);
            var dir2 = NormalizeAwayFrom(corner, l2);
            float angle = (float)Math.Acos(Math.Clamp(dir1.X * dir2.X + dir1.Y * dir2.Y, -1, 1));
            if (angle < 0.05f || angle > (float)Math.PI - 0.05f) return null;

            float tanHalf = (float)Math.Tan(angle * 0.5);
            float dist = radius / tanHalf;
            var t1 = new SKPoint(corner.X + dir1.X * dist, corner.Y + dir1.Y * dist);
            var t2 = new SKPoint(corner.X + dir2.X * dist, corner.Y + dir2.Y * dist);
            var center = new SKPoint((t1.X + t2.X) * 0.5f, (t1.Y + t2.Y) * 0.5f);
            float r = SKPoint.Distance(center, t1);
            float start = (float)(Math.Atan2(t1.Y - center.Y, t1.X - center.X) * 180 / Math.PI);
            float end = (float)(Math.Atan2(t2.Y - center.Y, t2.X - center.X) * 180 / Math.PI);
            float sweep = end - start;
            if (sweep > 180) sweep -= 360;
            if (sweep < -180) sweep += 360;
            return new ArcEntity(center, r, start, sweep, l1.Color, l1.Layer);
        }

        private static SKPoint NormalizeAwayFrom(SKPoint corner, LineEntity line)
        {
            var far = SKPoint.Distance(corner, line.Start) > SKPoint.Distance(corner, line.End) ? line.Start : line.End;
            float dx = far.X - corner.X, dy = far.Y - corner.Y;
            float len = (float)Math.Sqrt(dx * dx + dy * dy);
            return len < 1e-6f ? new SKPoint(1, 0) : new SKPoint(dx / len, dy / len);
        }

        public static bool TryLineIntersectionInfinite(LineEntity l1, LineEntity l2, out SKPoint hit)
        {
            hit = default;
            float d = (l1.End.X - l1.Start.X) * (l2.End.Y - l2.Start.Y) - (l1.End.Y - l1.Start.Y) * (l2.End.X - l2.Start.X);
            if (Math.Abs(d) < 1e-6f) return false;
            float ua = ((l2.End.X - l2.Start.X) * (l1.Start.Y - l2.Start.Y) - (l2.End.Y - l2.Start.Y) * (l1.Start.X - l2.Start.X)) / d;
            hit = new SKPoint(l1.Start.X + ua * (l1.End.X - l1.Start.X), l1.Start.Y + ua * (l1.End.Y - l1.Start.Y));
            return true;
        }

        public static List<CadEntity> InstantiateBlock(CadBlockDefinition block, SKPoint insertPoint)
        {
            var delta = new SKPoint(insertPoint.X - block.BasePoint.X, insertPoint.Y - block.BasePoint.Y);
            return block.Entities.Select(e => CloneEntity(e, delta)!).ToList();
        }
    }
}
