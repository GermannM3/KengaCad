using System;
using System.Collections.Generic;
using System.Linq;

namespace KengaCAD
{
    public class CollisionHit
    {
        public int Step { get; set; }
        public string ObjectA { get; set; } = "";
        public string ObjectB { get; set; } = "";
        public (double X, double Y, double Z) Point { get; set; }
    }

    /// <summary>Проверка коллизий траектории и робота (AABB).</summary>
    public static class CollisionDetector
    {
        public static bool AabbOverlap(
            (double MinX, double MinY, double MinZ, double MaxX, double MaxY, double MaxZ) a,
            (double MinX, double MinY, double MinZ, double MaxX, double MaxY, double MaxZ) b,
            double margin = 0)
        {
            return a.MinX - margin <= b.MaxX && a.MaxX + margin >= b.MinX
                && a.MinY - margin <= b.MaxY && a.MaxY + margin >= b.MinY
                && a.MinZ - margin <= b.MaxZ && a.MaxZ + margin >= b.MinZ;
        }

        public static List<CollisionHit> CheckTrajectoryVsObstacles(
            IReadOnlyList<(double X, double Y, double Z)> trajectory,
            IReadOnlyList<WorkcellObject> obstacles,
            double margin = 5.0)
        {
            var hits = new List<CollisionHit>();
            if (trajectory.Count == 0 || obstacles.Count == 0) return hits;

            for (int step = 0; step < trajectory.Count; step++)
            {
                var pt = trajectory[step];
                if (step > 0)
                {
                    var prev = trajectory[step - 1];
                    foreach (var obs in obstacles.Where(o => o.Visible))
                    {
                        if (obs.CollisionMesh != null &&
                            MeshGeometryHelper.SegmentIntersectsMesh(prev, pt, obs.CollisionMesh,
                                obs.X - obs.SizeX * 0.5, -(obs.Y + obs.SizeY * 0.5), obs.Z, margin))
                        {
                            hits.Add(new CollisionHit { Step = step, ObjectA = "trajectory_sweep", ObjectB = obs.Name, Point = pt });
                            continue;
                        }
                    }
                }

                var sphere = (
                    MinX: pt.X - margin, MinY: pt.Y - margin, MinZ: pt.Z - margin,
                    MaxX: pt.X + margin, MaxY: pt.Y + margin, MaxZ: pt.Z + margin);

                foreach (var obs in obstacles.Where(o => o.Visible))
                {
                    if (AabbOverlap(sphere, obs.GetAabb(), margin))
                    {
                        hits.Add(new CollisionHit
                        {
                            Step = step,
                            ObjectA = "trajectory",
                            ObjectB = obs.Name,
                            Point = pt
                        });
                    }
                }
            }
            return hits;
        }

        public static List<CollisionHit> CheckRobotSelfCollision(
            IReadOnlyList<(double X, double Y, double Z)> linkPositions,
            double linkRadius = 35.0,
            double minGap = 15.0)
        {
            var hits = new List<CollisionHit>();
            if (linkPositions.Count < 4) return hits;

            for (int i = 0; i < linkPositions.Count; i++)
            {
                for (int j = i + 2; j < linkPositions.Count; j++)
                {
                    if (j == i + 1) continue;
                    var a = linkPositions[i];
                    var b = linkPositions[j];
                    double dx = a.X - b.X, dy = a.Y - b.Y, dz = a.Z - b.Z;
                    double dist = Math.Sqrt(dx * dx + dy * dy + dz * dz);
                    if (dist < linkRadius * 2 + minGap)
                    {
                        hits.Add(new CollisionHit
                        {
                            Step = 0,
                            ObjectA = $"link_{i}",
                            ObjectB = $"link_{j}",
                            Point = a
                        });
                    }
                }
            }
            return hits;
        }

        public static List<CollisionHit> CheckRobotVsObstacles(
            IReadOnlyList<(double X, double Y, double Z)> linkPositions,
            IReadOnlyList<WorkcellObject> obstacles,
            double linkRadius = 30.0)
        {
            var hits = new List<CollisionHit>();
            foreach (var link in linkPositions)
            {
                var aabb = (
                    MinX: link.X - linkRadius, MinY: link.Y - linkRadius, MinZ: link.Z - linkRadius,
                    MaxX: link.X + linkRadius, MaxY: link.Y + linkRadius, MaxZ: link.Z + linkRadius);

                foreach (var obs in obstacles.Where(o => o.Visible))
                {
                    if (AabbOverlap(aabb, obs.GetAabb()))
                    {
                        hits.Add(new CollisionHit
                        {
                            ObjectA = "robot",
                            ObjectB = obs.Name,
                            Point = link
                        });
                    }
                }
            }
            return hits;
        }

        /// <summary>Оценка времени цикла по операциям программы (с).</summary>
        public static double EstimateCycleTimeSeconds(
            IReadOnlyList<ProgramOperation> operations,
            IReadOnlyList<ProgramWaypoint> waypoints,
            (double X, double Y, double Z) startPos)
        {
            double total = 0;
            var current = startPos;

            foreach (var op in operations)
            {
                string t = op.Type?.Trim().ToUpperInvariant() ?? "MOVEL";
                if (t == "WAIT")
                {
                    total += op.WaitMs / 1000.0;
                    continue;
                }
                if (t == "IO") { total += 0.05; continue; }

                if (op.WaypointIndex < 1 || op.WaypointIndex > waypoints.Count) continue;
                var wp = waypoints[op.WaypointIndex - 1];
                double dist = Distance(current, (wp.X, wp.Y, wp.Z));
                double speed = Math.Max(1.0, op.Speed);
                total += dist / speed;
                if (t == "MOVEJ") total += 0.3;
                current = (wp.X, wp.Y, wp.Z);
            }
            return total;
        }

        private static double Distance((double X, double Y, double Z) a, (double X, double Y, double Z) b)
        {
            double dx = a.X - b.X, dy = a.Y - b.Y, dz = a.Z - b.Z;
            return Math.Sqrt(dx * dx + dy * dy + dz * dz);
        }
    }
}
