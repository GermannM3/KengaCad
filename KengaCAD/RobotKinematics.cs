using System;
using System.Collections.Generic;
using System.Linq;

namespace KengaCAD
{
    /// <summary>
    /// Параметры Денавита — Хартенберга для одного звена: a (мм), d (мм), alpha (рад), theta_offset (рад).
    /// </summary>
    public readonly struct DhParams
    {
        public double A { get; }
        public double D { get; }
        public double Alpha { get; }
        public double ThetaOffset { get; }

        public DhParams(double a, double d, double alpha, double thetaOffset)
        {
            A = a;
            D = d;
            Alpha = alpha;
            ThetaOffset = thetaOffset;
        }
    }

    /// <summary>
    /// Результат прямой кинематики: позиция TCP, RPY, матрица 4x4, позиции звеньев.
    /// </summary>
    public class FkResult
    {
        public (double X, double Y, double Z) TcpPos { get; set; }
        public (double Rx, double Ry, double Rz) TcpRpyDeg { get; set; }
        public double[,] T { get; set; } = new double[4, 4];
        public List<(double X, double Y, double Z)> LinkPositions { get; set; } = new();
    }

    /// <summary>
    /// Кинематика 6DOF-манипулятора: FK по Денавиту — Хартенбергу.
    /// </summary>
    public static class RobotKinematics
    {
        public const int NumJoints = 6;

        /// <summary>Стандартные DH-параметры демо-робота (a, d, alpha, theta_offset).</summary>
        public static readonly DhParams[] DefaultDh = new[]
        {
            new DhParams(75, 330, Math.PI / 2, 0),
            new DhParams(300, 0, 0, 0),
            new DhParams(75, 0, Math.PI / 2, 0),
            new DhParams(0, 320, -Math.PI / 2, 0),
            new DhParams(0, 0, Math.PI / 2, 0),
            new DhParams(0, 80, 0, 0),
        };

        public static readonly DhParams[] KukaKR6 = new[]
        {
            new DhParams(25, 400, Math.PI / 2, 0),
            new DhParams(315, 0, 0, 0),
            new DhParams(35, 0, Math.PI / 2, 0),
            new DhParams(0, 365, -Math.PI / 2, 0),
            new DhParams(0, 0, Math.PI / 2, 0),
            new DhParams(0, 80, 0, 0),
        };

        public static readonly DhParams[] AbbIRB120 = new[]
        {
            new DhParams(0, 290, Math.PI / 2, 0),
            new DhParams(270, 0, 0, 0),
            new DhParams(70, 0, Math.PI / 2, 0),
            new DhParams(0, 302, -Math.PI / 2, 0),
            new DhParams(0, 0, Math.PI / 2, 0),
            new DhParams(0, 72, 0, 0),
        };

        public static readonly DhParams[] FanucLRMate = new[]
        {
            new DhParams(50, 330, Math.PI / 2, 0),
            new DhParams(330, 0, 0, 0),
            new DhParams(35, 0, Math.PI / 2, 0),
            new DhParams(0, 335, -Math.PI / 2, 0),
            new DhParams(0, 0, Math.PI / 2, 0),
            new DhParams(0, 80, 0, 0),
        };

        public static readonly DhParams[] UR5 = new[]
        {
            new DhParams(0, 89.2, Math.PI / 2, 0),
            new DhParams(-425, 0, 0, 0),
            new DhParams(-392.2, 0, 0, 0),
            new DhParams(0, 109.3, Math.PI / 2, 0),
            new DhParams(0, 94.75, -Math.PI / 2, 0),
            new DhParams(0, 82.5, 0, 0),
        };

        public static DhParams[] GetDhForRobot(string name)
        {
            if (name.Contains("KUKA") || name.Contains("KR6")) return KukaKR6;
            if (name.Contains("ABB") || name.Contains("IRB")) return AbbIRB120;
            if (name.Contains("Fanuc") || name.Contains("LR Mate")) return FanucLRMate;
            if (name.Contains("UR") || name.Contains("Universal")) return UR5;
            return DefaultDh;
        }

        private static void RotZ(double theta, double[,] out4x4)
        {
            double c = Math.Cos(theta), s = Math.Sin(theta);
            out4x4[0, 0] = c; out4x4[0, 1] = -s; out4x4[0, 2] = 0; out4x4[0, 3] = 0;
            out4x4[1, 0] = s; out4x4[1, 1] = c;  out4x4[1, 2] = 0; out4x4[1, 3] = 0;
            out4x4[2, 0] = 0; out4x4[2, 1] = 0;  out4x4[2, 2] = 1; out4x4[2, 3] = 0;
            out4x4[3, 0] = 0; out4x4[3, 1] = 0;  out4x4[3, 2] = 0; out4x4[3, 3] = 1;
        }

        private static void Trans(double x, double y, double z, double[,] out4x4)
        {
            out4x4[0, 0] = 1; out4x4[0, 1] = 0; out4x4[0, 2] = 0; out4x4[0, 3] = x;
            out4x4[1, 0] = 0; out4x4[1, 1] = 1; out4x4[1, 2] = 0; out4x4[1, 3] = y;
            out4x4[2, 0] = 0; out4x4[2, 1] = 0; out4x4[2, 2] = 1; out4x4[2, 3] = z;
            out4x4[3, 0] = 0; out4x4[3, 1] = 0; out4x4[3, 2] = 0; out4x4[3, 3] = 1;
        }

        private static void RotX(double alpha, double[,] out4x4)
        {
            double c = Math.Cos(alpha), s = Math.Sin(alpha);
            out4x4[0, 0] = 1; out4x4[0, 1] = 0;  out4x4[0, 2] = 0;  out4x4[0, 3] = 0;
            out4x4[1, 0] = 0; out4x4[1, 1] = c;  out4x4[1, 2] = -s; out4x4[1, 3] = 0;
            out4x4[2, 0] = 0; out4x4[2, 1] = s;  out4x4[2, 2] = c;  out4x4[2, 3] = 0;
            out4x4[3, 0] = 0; out4x4[3, 1] = 0;  out4x4[3, 2] = 0;  out4x4[3, 3] = 1;
        }

        private static void Mul4x4(double[,] a, double[,] b, double[,] result)
        {
            for (int i = 0; i < 4; i++)
                for (int j = 0; j < 4; j++)
                {
                    result[i, j] = 0;
                    for (int k = 0; k < 4; k++)
                        result[i, j] += a[i, k] * b[k, j];
                }
        }

        private static void DhLink(double theta, double d, double a, double alpha, double[,] outT)
        {
            var rz = new double[4, 4];
            var tz = new double[4, 4];
            var tx = new double[4, 4];
            var rx = new double[4, 4];
            var tmp = new double[4, 4];

            RotZ(theta, rz);
            Trans(0, 0, d, tz);
            Trans(a, 0, 0, tx);
            RotX(alpha, rx);

            Mul4x4(rz, tz, tmp);
            Mul4x4(tmp, tx, rz);
            Mul4x4(rz, rx, outT);
        }

        private static (double Rx, double Ry, double Rz) Rot3ToRpy(double[,] R)
        {
            double sy = Math.Sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0]);
            const double eps = 1e-6;
            if (sy >= eps)
            {
                double rx = Math.Atan2(R[2, 1], R[2, 2]);
                double ry = Math.Atan2(-R[2, 0], sy);
                double rz = Math.Atan2(R[1, 0], R[0, 0]);
                return (Math.Round(rx * 180.0 / Math.PI, 6), Math.Round(ry * 180.0 / Math.PI, 6), Math.Round(rz * 180.0 / Math.PI, 6));
            }
            double rx2 = Math.Atan2(-R[1, 2], R[1, 1]);
            double ry2 = Math.Atan2(-R[2, 0], sy);
            return (Math.Round(rx2 * 180.0 / Math.PI, 6), Math.Round(ry2 * 180.0 / Math.PI, 6), 0);
        }

        /// <summary>
        /// Прямая кинематика: углы суставов (градусы) и DH-параметры → позиция TCP, RPY, позиции звеньев.
        /// </summary>
        public static FkResult FkFull(IReadOnlyList<double> jointsDeg, IReadOnlyList<DhParams>? dhParams = null)
        {
            var dh = dhParams ?? DefaultDh;
            var T = new double[4, 4];
            T[0, 0] = T[1, 1] = T[2, 2] = T[3, 3] = 1;

            var linkPositions = new List<(double X, double Y, double Z)>();
            linkPositions.Add((T[0, 3], T[1, 3], T[2, 3]));

            for (int i = 0; i < NumJoints; i++)
            {
                var p = i < dh.Count ? dh[i] : DefaultDh[i];
                double theta = (Math.PI / 180.0) * jointsDeg[i] + p.ThetaOffset;
                var Ti = new double[4, 4];
                DhLink(theta, p.D, p.A, p.Alpha, Ti);
                var Tnew = new double[4, 4];
                Mul4x4(T, Ti, Tnew);
                T = Tnew;
                linkPositions.Add((T[0, 3], T[1, 3], T[2, 3]));
            }

            var R = new double[3, 3];
            for (int i = 0; i < 3; i++)
                for (int j = 0; j < 3; j++)
                    R[i, j] = T[i, j];

            var rpy = Rot3ToRpy(R);
            return new FkResult
            {
                TcpPos = (T[0, 3], T[1, 3], T[2, 3]),
                TcpRpyDeg = rpy,
                T = T,
                LinkPositions = linkPositions
            };
        }

        /// <summary>Только позиция TCP (x, y, z) в мм.</summary>
        public static (double X, double Y, double Z) FkTcp(IReadOnlyList<double> jointsDeg, IReadOnlyList<DhParams>? dhParams = null)
        {
            var r = FkFull(jointsDeg, dhParams);
            return r.TcpPos;
        }

        /// <summary>Обратная кинематика: позиция TCP (мм). Итерационный метод Якобиана.</summary>
        public static bool SolveIkPosition(
            (double X, double Y, double Z) target,
            double[] seed,
            IReadOnlyList<DhParams>? dhParams,
            double[] jointMin,
            double[] jointMax,
            out double[] solved,
            int maxIterations = 120,
            double posEpsMm = 0.7)
        {
            var q = seed.ToArray();
            var dh = dhParams ?? DefaultDh;
            const double jacobianDeltaDeg = 0.5;
            const double gain = 0.45;

            for (int iter = 0; iter < maxIterations; iter++)
            {
                var fk = FkFull(q, dh).TcpPos;
                double ex = target.X - fk.X;
                double ey = target.Y - fk.Y;
                double ez = target.Z - fk.Z;
                if (Math.Sqrt(ex * ex + ey * ey + ez * ez) < posEpsMm)
                {
                    solved = q;
                    return true;
                }

                for (int j = 0; j < NumJoints; j++)
                {
                    var qd = q.ToArray();
                    qd[j] += jacobianDeltaDeg;
                    var pd = FkFull(qd, dh).TcpPos;
                    double jx = (pd.X - fk.X) / jacobianDeltaDeg;
                    double jy = (pd.Y - fk.Y) / jacobianDeltaDeg;
                    double jz = (pd.Z - fk.Z) / jacobianDeltaDeg;
                    double denom = jx * jx + jy * jy + jz * jz + 1e-9;
                    double dq = gain * (jx * ex + jy * ey + jz * ez) / denom;
                    q[j] = Math.Clamp(q[j] + dq, jointMin[j], jointMax[j]);
                }
            }

            solved = seed.ToArray();
            return false;
        }

        /// <summary>Обратная кинематика: позиция + ориентация RPY (градусы).</summary>
        public static bool SolveIkFull(
            (double X, double Y, double Z) targetPos,
            (double Rx, double Ry, double Rz) targetRpyDeg,
            double[] seed,
            IReadOnlyList<DhParams>? dhParams,
            double[] jointMin,
            double[] jointMax,
            out double[] solved,
            int maxIterations = 150,
            double posEpsMm = 1.5,
            double rotEpsDeg = 1.0)
        {
            var q = seed.ToArray();
            var dh = dhParams ?? DefaultDh;
            const double jacobianDeltaDeg = 0.4;
            const double gain = 0.35;
            var targetR = RpyDegToRot3(targetRpyDeg);

            for (int iter = 0; iter < maxIterations; iter++)
            {
                var fk = FkFull(q, dh);
                double ex = targetPos.X - fk.TcpPos.X;
                double ey = targetPos.Y - fk.TcpPos.Y;
                double ez = targetPos.Z - fk.TcpPos.Z;
                var (erx, ery, erz) = RotErrorDeg(fk.T, targetR);
                double posErr = Math.Sqrt(ex * ex + ey * ey + ez * ez);
                double rotErr = Math.Sqrt(erx * erx + ery * ery + erz * erz);
                if (posErr < posEpsMm && rotErr < rotEpsDeg)
                {
                    solved = q;
                    return true;
                }

                var err = new[] { ex, ey, ez, erx, ery, erz };
                for (int j = 0; j < NumJoints; j++)
                {
                    var qd = q.ToArray();
                    qd[j] += jacobianDeltaDeg;
                    var fd = FkFull(qd, dh);
                    double j0 = (fd.TcpPos.X - fk.TcpPos.X) / jacobianDeltaDeg;
                    double j1 = (fd.TcpPos.Y - fk.TcpPos.Y) / jacobianDeltaDeg;
                    double j2 = (fd.TcpPos.Z - fk.TcpPos.Z) / jacobianDeltaDeg;
                    var (drx, dry, drz) = RotErrorDeg(fd.T, fk.T);
                    double j3 = drx / jacobianDeltaDeg;
                    double j4 = dry / jacobianDeltaDeg;
                    double j5 = drz / jacobianDeltaDeg;
                    var jacCol = new[] { j0, j1, j2, j3, j4, j5 };
                    double denom = jacCol.Sum(v => v * v) + 1e-9;
                    double dq = gain * jacCol.Zip(err, (a, b) => a * b).Sum() / denom;
                    q[j] = Math.Clamp(q[j] + dq, jointMin[j], jointMax[j]);
                }
            }

            solved = seed.ToArray();
            return false;
        }

        private static double[,] RpyDegToRot3((double Rx, double Ry, double Rz) rpy)
        {
            double rx = rpy.Rx * Math.PI / 180, ry = rpy.Ry * Math.PI / 180, rz = rpy.Rz * Math.PI / 180;
            var cx = Math.Cos(rx); var sx = Math.Sin(rx);
            var cy = Math.Cos(ry); var sy = Math.Sin(ry);
            var cz = Math.Cos(rz); var sz = Math.Sin(rz);
            var R = new double[3, 3];
            R[0, 0] = cz * cy; R[0, 1] = cz * sy * sx - sz * cx; R[0, 2] = cz * sy * cx + sz * sx;
            R[1, 0] = sz * cy; R[1, 1] = sz * sy * sx + cz * cx; R[1, 2] = sz * sy * cx - cz * sx;
            R[2, 0] = -sy; R[2, 1] = cy * sx; R[2, 2] = cy * cx;
            return R;
        }

        private static (double Rx, double Ry, double Rz) RotErrorDeg(double[,] currentT, double[,] targetR)
        {
            var Rc = new double[3, 3];
            for (int i = 0; i < 3; i++)
                for (int j = 0; j < 3; j++)
                    Rc[i, j] = currentT[i, j];
            var Re = new double[3, 3];
            for (int i = 0; i < 3; i++)
                for (int j = 0; j < 3; j++)
                {
                    Re[i, j] = 0;
                    for (int k = 0; k < 3; k++)
                        Re[i, j] += targetR[i, k] * Rc[k, j];
                }
            var rpy = Rot3ToRpy(Re);
            return rpy;
        }
    }
}
