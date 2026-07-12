using System.Collections.ObjectModel;
using KengaCAD;

namespace KengaCAD.Mobile;

public partial class MainPage : ContentPage
{
    private readonly double[] _joints = new double[RobotKinematics.NumJoints];
    private DhParams[] _dh = RobotKinematics.DefaultDh;
    private double[] _jMin = Enumerable.Repeat(-180.0, 6).ToArray();
    private double[] _jMax = Enumerable.Repeat(180.0, 6).ToArray();
    private readonly ObservableCollection<WaypointRow> _waypoints = new();
    private readonly Slider[] _sliders;
    private bool _updating;

    public MainPage()
    {
        InitializeComponent();
        _sliders = new[] { J1, J2, J3, J4, J5, J6 };
        WaypointsList.ItemsSource = _waypoints;
        Loaded += async (_, _) => await InitAsync();
    }

    private async Task InitAsync()
    {
        await MobileConfig.EnsureAsync();
        RobotPicker.ItemsSource = RobotLibrary.Robots.Select(r => r.DisplayName).ToList();
        if (RobotPicker.ItemsSource is IList<string> list && list.Count > 0)
            RobotPicker.SelectedIndex = 0;
        StatusLabel.Text = "Готово";
    }

    private void OnRobotChanged(object? sender, EventArgs e)
    {
        if (RobotPicker.SelectedIndex < 0) return;
        var name = RobotPicker.ItemsSource is IList<string> items ? items[RobotPicker.SelectedIndex] : "";
        var def = RobotLibrary.FindByDisplayName(name);
        if (def == null) return;
        _dh = def.DhParams.Length >= 6 ? def.DhParams : RobotKinematics.DefaultDh;
        _jMin = def.JointMin.ToArray();
        _jMax = def.JointMax.ToArray();
        _updating = true;
        for (int i = 0; i < 6; i++)
        {
            _sliders[i].Minimum = _jMin[i];
            _sliders[i].Maximum = _jMax[i];
            _sliders[i].Value = 0;
            _joints[i] = 0;
        }
        _updating = false;
        UpdateTcp();
    }

    private void OnJointChanged(object? sender, ValueChangedEventArgs e)
    {
        if (_updating) return;
        for (int i = 0; i < 6; i++)
            _joints[i] = _sliders[i].Value;
        UpdateTcp();
    }

    private void UpdateTcp()
    {
        var fk = RobotKinematics.FkFull(_joints, _dh);
        TcpLabel.Text = $"TCP  X={fk.TcpPos.X:F1}  Y={fk.TcpPos.Y:F1}  Z={fk.TcpPos.Z:F1}  |  Rx={fk.TcpRpyDeg.Rx:F1} Ry={fk.TcpRpyDeg.Ry:F1} Rz={fk.TcpRpyDeg.Rz:F1}";
    }

    private void OnZeroJoints(object? sender, EventArgs e)
    {
        _updating = true;
        for (int i = 0; i < 6; i++)
        {
            _joints[i] = 0;
            _sliders[i].Value = 0;
        }
        _updating = false;
        UpdateTcp();
    }

    private void OnAddWaypoint(object? sender, EventArgs e)
    {
        var fk = RobotKinematics.FkFull(_joints, _dh);
        int idx = _waypoints.Count + 1;
        _waypoints.Add(new WaypointRow
        {
            Index = idx,
            X = fk.TcpPos.X,
            Y = fk.TcpPos.Y,
            Z = fk.TcpPos.Z,
            Rx = fk.TcpRpyDeg.Rx,
            Ry = fk.TcpRpyDeg.Ry,
            Rz = fk.TcpRpyDeg.Rz
        });
        StatusLabel.Text = $"Добавлена P{idx:000}";
    }

    private async void OnExportKrl(object? sender, EventArgs e) =>
        await ExportAsync("krl", (pts, path) => Postprocessors.ExportKukaKrl(pts, path));
    private async void OnExportRapid(object? sender, EventArgs e) =>
        await ExportAsync("mod", (pts, path) => Postprocessors.ExportAbbRapid(pts, path));
    private async void OnExportGcode(object? sender, EventArgs e) =>
        await ExportAsync("gcode", (pts, path) => Postprocessors.ExportGCode(pts, path));

    private async Task ExportAsync(string ext, Func<IReadOnlyList<TrajectoryPoint>, string, bool> exporter)
    {
        if (_waypoints.Count == 0)
        {
            await DisplayAlert("Экспорт", "Сначала добавьте хотя бы одну точку.", "OK");
            return;
        }
        var pts = _waypoints.Select(w => TrajectoryPoint.FromXyz(w.X, w.Y, w.Z, w.Rx, w.Ry, w.Rz)).ToList();
        var path = Path.Combine(FileSystem.CacheDirectory, $"kengacad_export.{ext}");
        if (!exporter(pts, path))
        {
            StatusLabel.Text = "Ошибка экспорта";
            return;
        }
        await Share.Default.RequestAsync(new ShareFileRequest
        {
            Title = "KengaCAD экспорт",
            File = new ShareFile(path)
        });
        StatusLabel.Text = $"Экспорт: {path}";
    }

    private sealed class WaypointRow
    {
        public int Index { get; set; }
        public double X, Y, Z, Rx, Ry, Rz;
        public string Display => $"P{Index:000}  X={X:F1} Y={Y:F1} Z={Z:F1}";
    }
}
