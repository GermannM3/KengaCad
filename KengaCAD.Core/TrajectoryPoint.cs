using System;
using System.Collections.Generic;

namespace KengaCAD
{
    /// <summary>Точка траектории с координатами и ориентацией (Euler RPY).</summary>
    public class TrajectoryPoint
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public double Rx { get; set; }
        public double Ry { get; set; }
        public double Rz { get; set; }

        /// <summary>Кватернион w,x,y,z для ABB RAPID.</summary>
        public (double Q1, double Q2, double Q3, double Q4) Quaternion
        {
            get
            {
                double rx = Rx * Math.PI / 180.0, ry = Ry * Math.PI / 180.0, rz = Rz * Math.PI / 180.0;
                double cx = Math.Cos(rx / 2), sx = Math.Sin(rx / 2);
                double cy = Math.Cos(ry / 2), sy = Math.Sin(ry / 2);
                double cz = Math.Cos(rz / 2), sz = Math.Sin(rz / 2);
                double q1 = cx * cy * cz + sx * sy * sz;
                double q2 = sx * cy * cz - cx * sy * sz;
                double q3 = cx * sy * cz + sx * cy * sz;
                double q4 = cx * cy * sz - sx * sy * cz;
                return (q1, q2, q3, q4);
            }
        }

        public static TrajectoryPoint FromXyz(double x, double y, double z, double rx = 0, double ry = 0, double rz = 0)
        {
            return new TrajectoryPoint { X = x, Y = y, Z = z, Rx = rx, Ry = ry, Rz = rz };
        }

        public static List<TrajectoryPoint> FromPoints(IEnumerable<(double X, double Y, double Z)> points)
        {
            var list = new List<TrajectoryPoint>();
            foreach (var p in points)
                list.Add(FromXyz(p.X, p.Y, p.Z));
            return list;
        }
    }
}
