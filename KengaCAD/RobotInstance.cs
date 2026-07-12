using System;
using System.Linq;
using System.Windows.Media;
using System.Windows.Media.Media3D;

namespace KengaCAD
{
    /// <summary>Экземпляр робота в ячейке (multi-robot workcell).</summary>
    public class RobotInstance
    {
        public string Id { get; init; } = Guid.NewGuid().ToString("N")[..8];
        public string Name { get; set; } = "Робот 1";
        public double[] JointAngles { get; set; } = new double[RobotKinematics.NumJoints];
        public DhParams[] Dh { get; set; } = RobotKinematics.DefaultDh;
        public RobotDefinition? Definition { get; set; }
        public (double X, double Y, double Z) BaseCad { get; set; }
        public double[] JointMin { get; set; } = Enumerable.Repeat(-180.0, RobotKinematics.NumJoints).ToArray();
        public double[] JointMax { get; set; } = Enumerable.Repeat(180.0, RobotKinematics.NumJoints).ToArray();
        public ModelVisual3D? SceneVisual { get; set; }

        public Color BrandColor
        {
            get
            {
                var m = Definition?.Manufacturer ?? "";
                return m switch
                {
                    "KUKA" => Color.FromRgb(255, 140, 0),
                    "ABB" => Color.FromRgb(255, 0, 0),
                    "Fanuc" => Color.FromRgb(255, 255, 0),
                    "UR" => Color.FromRgb(0, 160, 220),
                    _ => Color.FromRgb(70, 130, 180)
                };
            }
        }

        public void ApplyDefinition(RobotDefinition def)
        {
            Definition = def;
            Dh = def.DhParams.Length >= 6
                ? def.DhParams
                : RobotKinematics.GetDhForRobot(def.DisplayName);
            JointMin = def.JointMin.ToArray();
            JointMax = def.JointMax.ToArray();
        }

        public RobotInstance CloneAtOffset(string newName, (double X, double Y, double Z) offset)
        {
            return new RobotInstance
            {
                Name = newName,
                JointAngles = (double[])JointAngles.Clone(),
                Dh = Dh,
                Definition = Definition,
                BaseCad = (BaseCad.X + offset.X, BaseCad.Y + offset.Y, BaseCad.Z + offset.Z),
                JointMin = (double[])JointMin.Clone(),
                JointMax = (double[])JointMax.Clone()
            };
        }
    }
}
