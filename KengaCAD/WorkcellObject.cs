using System;
using System.Windows.Media;
using System.Windows.Media.Media3D;

namespace KengaCAD
{
    public enum WorkcellType { Table, Fixture, Fence, Conveyor, ImportedMesh }

    /// <summary>Параметрический объект рабочей ячейки с AABB для коллизий.</summary>
    public class WorkcellObject
    {
        public string Id { get; set; } = Guid.NewGuid().ToString("N")[..8];
        public string Name { get; set; } = "Object";
        public WorkcellType Type { get; set; }
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public double SizeX { get; set; } = 800;
        public double SizeY { get; set; } = 600;
        public double SizeZ { get; set; } = 40;
        public bool Visible { get; set; } = true;
        public Color Color { get; set; } = Color.FromRgb(90, 95, 105);

        public MeshGeometry3D? CollisionMesh { get; set; }

        public (double MinX, double MinY, double MinZ, double MaxX, double MaxY, double MaxZ) GetAabb()
        {
            if (CollisionMesh != null && CollisionMesh.Positions.Count > 0)
            {
                var b = MeshGeometryHelper.ComputeBounds(CollisionMesh);
                double tx = X - (b.MinX + b.MaxX) * 0.5;
                double ty = Y + (b.MinY + b.MaxY) * 0.5;
                return (b.MinX + tx, b.MinY + ty, b.MinZ + Z, b.MaxX + tx, b.MaxY + ty, b.MaxZ + Z);
            }
            double hx = SizeX * 0.5, hy = SizeY * 0.5;
            return (X - hx, Y - hy, Z, X + hx, Y + hy, Z + SizeZ);
        }

        public static WorkcellObject CreateTable(double x, double y, double w = 800, double d = 600, double h = 40)
            => new()
            {
                Name = "Стол",
                Type = WorkcellType.Table,
                X = x, Y = y, Z = 0,
                SizeX = w, SizeY = d, SizeZ = h,
                Color = Color.FromRgb(70, 75, 85)
            };

        public static WorkcellObject CreateFixture(double x, double y, double w = 200, double d = 150, double h = 120)
            => new()
            {
                Name = "Оснастка",
                Type = WorkcellType.Fixture,
                X = x, Y = y, Z = 40,
                SizeX = w, SizeY = d, SizeZ = h,
                Color = Color.FromRgb(180, 140, 60)
            };

        public static WorkcellObject CreateFence(double x, double y, double w = 1200, double d = 20, double h = 1800)
            => new()
            {
                Name = "Ограждение",
                Type = WorkcellType.Fence,
                X = x, Y = y, Z = 0,
                SizeX = w, SizeY = d, SizeZ = h,
                Color = Color.FromRgb(255, 180, 0)
            };

        public static WorkcellObject CreateConveyor(double x, double y, double len = 2000, double w = 400, double h = 80)
            => new()
            {
                Name = "Конвейер",
                Type = WorkcellType.Conveyor,
                X = x, Y = y, Z = 0,
                SizeX = len, SizeY = w, SizeZ = h,
                Color = Color.FromRgb(50, 50, 55)
            };
    }

    public class IoSignal
    {
        public string Name { get; set; } = "DO1";
        public string Type { get; set; } = "DO";
        public bool Value { get; set; }
        public string Description { get; set; } = "";
        /// <summary>OPC UA NodeId, например ns=2;s=PLC.DO1</summary>
        public string OpcNodeId { get; set; } = "";
    }
}
