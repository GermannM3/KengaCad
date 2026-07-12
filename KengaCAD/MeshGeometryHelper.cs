using System;
using System.Collections.Generic;
using System.Linq;
using System.Windows.Media.Media3D;

namespace KengaCAD
{
    public static class MeshGeometryHelper
    {
        public static (double MinX, double MinY, double MinZ, double MaxX, double MaxY, double MaxZ) ComputeBounds(MeshGeometry3D mesh)
        {
            if (mesh.Positions.Count == 0)
                return (0, 0, 0, 0, 0, 0);
            double minX = double.MaxValue, minY = double.MaxValue, minZ = double.MaxValue;
            double maxX = double.MinValue, maxY = double.MinValue, maxZ = double.MinValue;
            foreach (var p in mesh.Positions)
            {
                minX = Math.Min(minX, p.X); maxX = Math.Max(maxX, p.X);
                minY = Math.Min(minY, p.Y); maxY = Math.Max(maxY, p.Y);
                minZ = Math.Min(minZ, p.Z); maxZ = Math.Max(maxZ, p.Z);
            }
            return (minX, minY, minZ, maxX, maxY, maxZ);
        }

        public static void ApplyBoundsToWorkcell(WorkcellObject obj, MeshGeometry3D mesh, double offsetX = 0, double offsetY = 0, double offsetZ = 0)
        {
            var b = ComputeBounds(mesh);
            obj.SizeX = Math.Max(1, b.MaxX - b.MinX);
            obj.SizeY = Math.Max(1, b.MaxY - b.MinY);
            obj.SizeZ = Math.Max(1, b.MaxZ - b.MinZ);
            obj.X = offsetX + (b.MinX + b.MaxX) * 0.5;
            obj.Y = offsetY - (b.MinY + b.MaxY) * 0.5;
            obj.Z = offsetZ + b.MinZ;
            obj.CollisionMesh = mesh;
        }

        public static bool PointNearMesh((double X, double Y, double Z) point, MeshGeometry3D mesh,
            double tx, double ty, double tz, double margin)
        {
            var b = ComputeBounds(mesh);
            var aabb = (
                MinX: b.MinX + tx - margin, MinY: b.MinY + ty - margin, MinZ: b.MinZ + tz - margin,
                MaxX: b.MaxX + tx + margin, MaxY: b.MaxY + ty + margin, MaxZ: b.MaxZ + tz + margin);
            return point.X >= aabb.MinX && point.X <= aabb.MaxX
                && point.Y >= aabb.MinY && point.Y <= aabb.MaxY
                && point.Z >= aabb.MinZ && point.Z <= aabb.MaxZ;
        }

        public static bool SegmentIntersectsMesh((double X, double Y, double Z) a, (double X, double Y, double Z) b,
            MeshGeometry3D mesh, double tx, double ty, double tz, double radius)
        {
            int steps = Math.Max(2, (int)(Distance(a, b) / Math.Max(radius, 5.0)));
            for (int i = 0; i <= steps; i++)
            {
                double t = (double)i / steps;
                var p = (
                    X: a.X + (b.X - a.X) * t,
                    Y: a.Y + (b.Y - a.Y) * t,
                    Z: a.Z + (b.Z - a.Z) * t);
                if (PointNearMesh(p, mesh, tx, ty, tz, radius))
                    return true;
            }
            return false;
        }

        private static double Distance((double X, double Y, double Z) a, (double X, double Y, double Z) b)
        {
            double dx = a.X - b.X, dy = a.Y - b.Y, dz = a.Z - b.Z;
            return Math.Sqrt(dx * dx + dy * dy + dz * dz);
        }

        public static MeshGeometry3D MergeMeshes(IEnumerable<MeshGeometry3D> meshes)
        {
            var merged = new MeshGeometry3D();
            foreach (var m in meshes)
            {
                int offset = merged.Positions.Count;
                foreach (var p in m.Positions) merged.Positions.Add(p);
                foreach (var i in m.TriangleIndices) merged.TriangleIndices.Add(i + offset);
            }
            merged.Freeze();
            return merged;
        }
    }
}
