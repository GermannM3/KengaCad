using System.Collections.Generic;

namespace KengaCAD
{
    public class ProgramWaypoint
    {
        public int Index { get; set; }
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public double Rx { get; set; }
        public double Ry { get; set; }
        public double Rz { get; set; }
        public double Speed { get; set; } = 120;
        public double Accel { get; set; } = 300;
    }

    public class ProgramFileDto
    {
        public string Robot { get; set; } = "";
        public string Tool { get; set; } = "TOOL0";
        public string Base { get; set; } = "BASE0";
        public List<ProgramWaypoint> Waypoints { get; set; } = new();
        public List<ProgramOperation> Operations { get; set; } = new();
    }

    public class ProgramOperation
    {
        public int Index { get; set; }
        public string Type { get; set; } = "MoveL";
        public int WaypointIndex { get; set; } = 1;
        public double Speed { get; set; } = 120;
        public double Accel { get; set; } = 300;
        public double WaitMs { get; set; } = 500;
        public string IoChannel { get; set; } = "DO1";
        public bool IoValue { get; set; }
    }
}
