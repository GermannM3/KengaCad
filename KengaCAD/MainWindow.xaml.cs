using System;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Media3D;
using System.Windows.Threading;
using SkiaSharp;
using SkiaSharp.Views.Desktop;
using SkiaSharp.Views.WPF;
using Microsoft.Win32;
using System.Collections.Generic;
using System.Linq;
using System.Collections.ObjectModel;
using System.Text.Json;

namespace KengaCAD
{
    public partial class MainWindow : Window
    {
        private SKBitmap? _bitmap;
        private SKCanvas? _canvas;
        private SKElement? _drawingCanvas;
        private SKElement DrawingCanvas => _drawingCanvas!;
        
        // Текущая команда
        private string _currentCommand = "";
        private bool _isDrawing = false;
        private SKPoint _startPoint;
        private SKPoint _currentPoint;
        
        // Список объектов
        private readonly System.Collections.Generic.List<CadEntity> _entities = new();
        
        // Настройки
        private bool _orthoMode = false;
        private bool _snapEnabled = true;
        private bool _gridVisible = true;
        private string _currentLayer = "0";
        private Color _currentColor = Colors.White;
        
        // Стек для Undo/Redo
        private readonly System.Collections.Generic.Stack<System.Collections.Generic.List<CadEntity>> _undoStack = new();
        private readonly System.Collections.Generic.Stack<System.Collections.Generic.List<CadEntity>> _redoStack = new();

        // Полилиния: накопление точек
        private readonly List<SKPoint> _polylinePoints = new();

        // Дуга: 3-точечная (начало, промежуточная, конец)
        private readonly List<SKPoint> _arcPoints = new();

        // Симуляция траектории в 3D
        private DispatcherTimer? _simTimer;
        private List<TrajectoryPoint> _simTrajectory = new();
        private int _simIndex;
        private readonly List<ModelVisual3D> _trajectoryVisuals = new();

        // Зум и панорама 2D
        private double _zoomScale = 1.0;
        private double _panX, _panY;
        private bool _panning;
        private System.Windows.Point _panStart;

        // MOVE/COPY: базовая точка
        private bool _editBaseSet;
        private SKPoint _editBasePoint;
        private CadEntity? _editRefEntity;
        private CadEntity? _editRefEntity2;
        private readonly List<SKPoint> _dimPoints = new();
        private readonly List<CadBlockDefinition> _blocks = new();
        private CadBlockDefinition? _pendingBlockInsert;
        private string? _currentDrawingPath;

        // 3D-навигация (орбита камеры)
        private bool _orbiting;
        private System.Windows.Point _orbitStart;
        private double _camYaw = -45, _camPitch = 30, _camDist = 900;
        private Point3D _camTarget = new(0, 0, 200);
        private bool _updatingJogUi;
        private bool _syncingRobotSelectors;
        private readonly Dictionary<string, (double X, double Y, double Z)> _toolFrames = new()
        {
            ["TOOL0"] = (0, 0, 0),
            ["GRIPPER_120"] = (0, 0, 120),
            ["WELD_TORCH_220"] = (30, 0, 220)
        };
        private readonly Dictionary<string, (double X, double Y, double Z)> _baseFrames = new()
        {
            ["BASE0"] = (0, 0, 0),
            ["STATION_A"] = (800, 0, 0),
            ["STATION_B"] = (1600, 300, 0)
        };
        private readonly ObservableCollection<ProgramWaypoint> _programWaypoints = new();
        private readonly ObservableCollection<ProgramOperation> _programOperations = new();
        private readonly Dictionary<string, (double[] Min, double[] Max)> _robotJointLimits = new();
        private double[] _jointMinLimits = Enumerable.Repeat(-180.0, RobotKinematics.NumJoints).ToArray();
        private double[] _jointMaxLimits = Enumerable.Repeat(180.0, RobotKinematics.NumJoints).ToArray();
        private int _selectedWaypointIndex = -1;
        private int _selectedOperationIndex = -1;
        private readonly List<ExecutionFrame> _execFrames = new();
        private int _execIndex;
        private bool _draggingRobotBase;
        private (double X, double Y, double Z) _robotBaseCad = (0, 0, 0);
        private RobotDefinition? _currentRobotDef;
        private readonly List<WorkcellObject> _workcellObjects = new();
        private readonly ObservableCollection<IoSignal> _ioSignals = new();
        private bool _ikConverged = true;
        private readonly List<RobotInstance> _robotInstances = new();
        private int _activeRobotIndex;
        private const int MaxRobotsInCell = 4;
        private readonly OpcUaClient _opcUaClient = new();
        private DispatcherTimer? _opcPollTimer;

        /// <summary>2D: Y вниз (Skia). 3D: Z вверх, для робота инвертируем Y оси CAD.</summary>
        private static Point3D CadToScene3D(double cadX, double cadY, double z = 0)
            => new(cadX, -cadY, z);

        private static Point3D MapRobotFk(double x, double y, double z)
            => new(x, -y, z);
        public MainWindow()
        {
            InitializeComponent();
            _drawingCanvas = new SKElement();
            _drawingCanvas.HorizontalAlignment = HorizontalAlignment.Stretch;
            _drawingCanvas.VerticalAlignment = VerticalAlignment.Stretch;
            _drawingCanvas.PaintSurface += DrawingCanvas_PaintSurface;
            _drawingCanvas.MouseDown += DrawingCanvas_MouseDown;
            _drawingCanvas.MouseMove += DrawingCanvas_MouseMove;
            _drawingCanvas.MouseUp += DrawingCanvas_MouseUp;
            _drawingCanvas.MouseWheel += DrawingCanvas_MouseWheel;
            DrawingCanvasHost.Children.Insert(0, _drawingCanvas);
            InitializeDrawing();
            InitializeComboBoxes();
            InitializeRobotPresets();
            BindCheckboxes();
            BuildGridFloor();
            UpdateCamera();
            InitializeJogPanel();
            AppendOutput("KengaCAD запущен. Интерфейс готов.");
        }

        private void InitializeJogPanel()
        {
            InitializeRobotJointLimits();
            ToolFrameComboBox.Items.Clear();
            foreach (var key in _toolFrames.Keys)
                ToolFrameComboBox.Items.Add(key);
            ToolFrameComboBox.SelectedIndex = 0;

            BaseFrameComboBox.Items.Clear();
            foreach (var key in _baseFrames.Keys)
                BaseFrameComboBox.Items.Add(key);
            BaseFrameComboBox.SelectedIndex = 0;

            WaypointsGrid.ItemsSource = _programWaypoints;
            OperationsGrid.ItemsSource = _programOperations;
            ApplyJointLimitsForCurrentRobot();
            SyncJointSlidersFromModel();
            UpdateJogTelemetry();
            if (OutputListBox.Items.Count == 0)
                AppendOutput("Готов к программированию робота.");
            ProgramRunModeComboBox.SelectedIndex = 0;
            InitializeIoSignals();
            InitializeRobotInstances();
            InitializeOpcPolling();
            RefreshProjectTree();
        }

        private void InitializeRobotInstances()
        {
            _robotInstances.Clear();
            var first = new RobotInstance { Name = "Робот 1", BaseCad = (0, 0, 0) };
            _robotInstances.Add(first);
            _activeRobotIndex = 0;
            RefreshRobotInstanceCombo();
        }

        private void RefreshRobotInstanceCombo()
        {
            _syncingRobotSelectors = true;
            JogRobotComboBox.Items.Clear();
            foreach (var r in _robotInstances)
                JogRobotComboBox.Items.Add(r.Name);
            JogRobotComboBox.SelectedIndex = Math.Clamp(_activeRobotIndex, 0, Math.Max(0, _robotInstances.Count - 1));
            _syncingRobotSelectors = false;
        }

        private RobotInstance ActiveRobotInstance => _robotInstances[Math.Clamp(_activeRobotIndex, 0, _robotInstances.Count - 1)];

        private void PushActiveRobotToInstance()
        {
            if (_robotInstances.Count == 0) return;
            var inst = ActiveRobotInstance;
            inst.JointAngles = _jointAngles.ToArray();
            inst.Dh = _currentDh;
            inst.Definition = _currentRobotDef;
            inst.BaseCad = _robotBaseCad;
            inst.JointMin = _jointMinLimits.ToArray();
            inst.JointMax = _jointMaxLimits.ToArray();
        }

        private void PullActiveRobotFromInstance()
        {
            if (_robotInstances.Count == 0) return;
            var inst = ActiveRobotInstance;
            _jointAngles = inst.JointAngles.ToArray();
            _currentDh = inst.Dh;
            _currentRobotDef = inst.Definition;
            _robotBaseCad = inst.BaseCad;
            _jointMinLimits = inst.JointMin.ToArray();
            _jointMaxLimits = inst.JointMax.ToArray();
            _currentRobotName = inst.Definition?.DisplayName ?? _currentRobotName;
        }

        private void SwitchActiveRobot(int index)
        {
            if (index < 0 || index >= _robotInstances.Count || index == _activeRobotIndex) return;
            PushActiveRobotToInstance();
            _activeRobotIndex = index;
            PullActiveRobotFromInstance();
            ApplyJointLimitsForCurrentRobot();
            SyncJointSlidersFromModel();
            UpdateJogTelemetry();
            BuildRobot3D();
            SyncScene3D();
        }

        private void AddRobotInstance()
        {
            if (_robotInstances.Count >= MaxRobotsInCell)
            {
                AppendOutput($"Ячейка: максимум {MaxRobotsInCell} робота.");
                return;
            }
            PushActiveRobotToInstance();
            var n = _robotInstances.Count + 1;
            var offset = (900.0 * (n - 1), 250.0 * ((n - 1) % 2), 0.0);
            var clone = ActiveRobotInstance.CloneAtOffset($"Робот {n}", offset);
            clone.JointAngles = new double[RobotKinematics.NumJoints];
            _robotInstances.Add(clone);
            _activeRobotIndex = _robotInstances.Count - 1;
            RefreshRobotInstanceCombo();
            PullActiveRobotFromInstance();
            ApplyJointLimitsForCurrentRobot();
            SyncJointSlidersFromModel();
            BuildRobot3D();
            SyncScene3D();
            AppendOutput($"Workcell: добавлен {clone.Name} @ X={clone.BaseCad.X:F0} Y={clone.BaseCad.Y:F0}");
        }

        private void InitializeOpcPolling()
        {
            _opcPollTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(500) };
            _opcPollTimer.Tick += (_, _) => PollOpcSignals();
            _opcPollTimer.Start();
            OpcStatusText.Text = "OPC: offline";
        }

        private async void OpcConnect_Click(object sender, RoutedEventArgs e)
        {
            var endpoint = OpcEndpointTextBox.Text.Trim();
            OpcStatusText.Text = "OPC: подключение...";
            bool ok = await _opcUaClient.ConnectAsync(endpoint);
            OpcStatusText.Text = ok ? $"OPC: {endpoint}" : $"OPC: ошибка — {_opcUaClient.LastError}";
            AppendOutput(OpcStatusText.Text);
        }

        private async void OpcDisconnect_Click(object sender, RoutedEventArgs e)
        {
            await _opcUaClient.DisconnectAsync();
            OpcStatusText.Text = "OPC: offline";
            AppendOutput("OPC UA отключён.");
        }

        private void IoSignalsGrid_CellEditEnding(object sender, DataGridCellEditEndingEventArgs e)
        {
            if (e.Row.Item is not IoSignal sig || !_opcUaClient.IsConnected) return;
            if (string.IsNullOrWhiteSpace(sig.OpcNodeId)) return;
            Dispatcher.BeginInvoke(() =>
            {
                if (sig.Type is "DO" or "AO")
                    _opcUaClient.WriteBool(sig.OpcNodeId, sig.Value);
            }, DispatcherPriority.Background);
        }

        private void PollOpcSignals()
        {
            if (!_opcUaClient.IsConnected) return;
            bool changed = false;
            foreach (var sig in _ioSignals)
            {
                if (string.IsNullOrWhiteSpace(sig.OpcNodeId)) continue;
                var val = _opcUaClient.ReadBool(sig.OpcNodeId);
                if (val.HasValue && val.Value != sig.Value)
                {
                    sig.Value = val.Value;
                    changed = true;
                }
            }
            if (changed)
                IoSignalsGrid.Items.Refresh();
        }

        private void InitializeIoSignals()
        {
            _ioSignals.Clear();
            _ioSignals.Add(new IoSignal { Name = "DO1", Type = "DO", Description = "Захват: открыть", OpcNodeId = "ns=2;s=DO1" });
            _ioSignals.Add(new IoSignal { Name = "DO2", Type = "DO", Description = "Захват: закрыть", OpcNodeId = "ns=2;s=DO2" });
            _ioSignals.Add(new IoSignal { Name = "DO3", Type = "DO", Description = "Старт сварки", OpcNodeId = "ns=2;s=DO3" });
            _ioSignals.Add(new IoSignal { Name = "DI1", Type = "DI", Description = "Деталь на месте", OpcNodeId = "ns=2;s=DI1" });
            _ioSignals.Add(new IoSignal { Name = "DI2", Type = "DI", Description = "Безопасность OK", OpcNodeId = "ns=2;s=DI2" });
            IoSignalsGrid.ItemsSource = _ioSignals;
        }

        private void InitializeRobotJointLimits()
        {
            _robotJointLimits.Clear();
            _robotJointLimits["default"] = (
                new[] { -180.0, -120.0, -170.0, -190.0, -120.0, -350.0 },
                new[] { 180.0, 120.0, 170.0, 190.0, 120.0, 350.0 });
            _robotJointLimits["KUKA"] = (
                new[] { -170.0, -190.0, -120.0, -185.0, -120.0, -350.0 },
                new[] { 170.0, 45.0, 156.0, 185.0, 120.0, 350.0 });
            _robotJointLimits["ABB"] = (
                new[] { -165.0, -110.0, -110.0, -160.0, -120.0, -400.0 },
                new[] { 165.0, 110.0, 70.0, 160.0, 120.0, 400.0 });
            _robotJointLimits["Fanuc"] = (
                new[] { -170.0, -100.0, -190.0, -190.0, -120.0, -360.0 },
                new[] { 170.0, 145.0, 190.0, 190.0, 120.0, 360.0 });
            _robotJointLimits["UR"] = (
                new[] { -360.0, -360.0, -360.0, -360.0, -360.0, -360.0 },
                new[] { 360.0, 360.0, 360.0, 360.0, 360.0, 360.0 });
        }

        private void ApplyJointLimitsForCurrentRobot()
        {
            if (_currentRobotDef != null)
            {
                _jointMinLimits = _currentRobotDef.JointMin.ToArray();
                _jointMaxLimits = _currentRobotDef.JointMax.ToArray();
            }
            else
            {
                (double[] Min, double[] Max) limits = _robotJointLimits["default"];
                foreach (var pair in _robotJointLimits)
                {
                    if (pair.Key == "default") continue;
                    if (_currentRobotName.Contains(pair.Key, StringComparison.OrdinalIgnoreCase))
                    {
                        limits = pair.Value;
                        break;
                    }
                }
                _jointMinLimits = limits.Min.ToArray();
                _jointMaxLimits = limits.Max.ToArray();
            }

            for (int i = 0; i < RobotKinematics.NumJoints; i++)
            {
                var slider = GetJointSlider(i);
                if (slider == null) continue;
                slider.Minimum = _jointMinLimits[i];
                slider.Maximum = _jointMaxLimits[i];
                _jointAngles[i] = Math.Clamp(_jointAngles[i], slider.Minimum, slider.Maximum);
            }
        }

        private void RefreshWaypointsGrid()
        {
            for (int i = 0; i < _programWaypoints.Count; i++)
                _programWaypoints[i].Index = i + 1;
            WaypointsGrid.Items.Refresh();
            RefreshProjectTree();
        }

        private void RefreshOperationsGrid()
        {
            for (int i = 0; i < _programOperations.Count; i++)
                _programOperations[i].Index = i + 1;
            OperationsGrid.Items.Refresh();
            RefreshProjectTree();
        }

        private void RefreshProjectTree()
        {
            ProjectTreeList.Items.Clear();
            ProjectTreeList.Items.Add("AR1730");
            ProjectTreeList.Items.Add("  Home");
            ProjectTreeList.Items.Add($"  Robot: {_currentRobotName}");
            ProjectTreeList.Items.Add($"  Program");
            ProjectTreeList.Items.Add($"    Waypoints: {_programWaypoints.Count}");
            for (int i = 0; i < Math.Min(5, _programWaypoints.Count); i++)
                ProjectTreeList.Items.Add($"      P{_programWaypoints[i].Index:000}");
            if (_programWaypoints.Count > 5)
                ProjectTreeList.Items.Add("      ...");
            ProjectTreeList.Items.Add($"    Operations: {_programOperations.Count}");
            for (int i = 0; i < Math.Min(5, _programOperations.Count); i++)
                ProjectTreeList.Items.Add($"      O{_programOperations[i].Index:000} {_programOperations[i].Type}");
            if (_programOperations.Count > 5)
                ProjectTreeList.Items.Add("      ...");
            ProjectTreeList.Items.Add($"  Simulation");
            ProjectTreeList.Items.Add($"  Workcell ({_workcellObjects.Count})");
            foreach (var obj in _workcellObjects.Take(6))
                ProjectTreeList.Items.Add($"    {obj.Name} [{obj.Type}]");
            if (_workcellObjects.Count > 6)
                ProjectTreeList.Items.Add("    ...");
            UpdateCycleTimeDisplay();
        }

        private void UpdateCycleTimeDisplay()
        {
            if (_programWaypoints.Count == 0 || _programOperations.Count == 0)
            {
                CycleTimeText.Text = "—";
                return;
            }
            var fk = RobotKinematics.FkFull(_jointAngles, _currentDh);
            var start = ToWorldTcp(fk.TcpPos);
            double sec = CollisionDetector.EstimateCycleTimeSeconds(
                _programOperations, _programWaypoints, start);
            CycleTimeText.Text = $"{sec:F1} с";
        }

        private void AppendOutput(string text)
        {
            string line = $"[{DateTime.Now:HH:mm:ss}] {text}";
            OutputListBox.Items.Add(line);
            if (OutputListBox.Items.Count > 300)
                OutputListBox.Items.RemoveAt(0);
            OutputListBox.ScrollIntoView(line);
        }

        private double JogStepDeg
        {
            get
            {
                if (JogStepComboBox.SelectedItem is ComboBoxItem item &&
                    double.TryParse(item.Content?.ToString(), out double step))
                    return step;
                return 5.0;
            }
        }

        private double TcpStepMm
        {
            get
            {
                if (TcpStepComboBox.SelectedItem is ComboBoxItem item &&
                    double.TryParse(item.Content?.ToString(), out double step))
                    return step;
                return 5.0;
            }
        }

        private (double X, double Y, double Z) SelectedToolOffset
        {
            get
            {
                string key = ToolFrameComboBox.SelectedItem?.ToString() ?? "TOOL0";
                return _toolFrames.TryGetValue(key, out var pose) ? pose : (0, 0, 0);
            }
        }

        private (double X, double Y, double Z) SelectedBaseOffset
        {
            get
            {
                string key = BaseFrameComboBox.SelectedItem?.ToString() ?? "BASE0";
                return _baseFrames.TryGetValue(key, out var pose) ? pose : (0, 0, 0);
            }
        }

        private Slider? GetJointSlider(int index) => index switch
        {
            0 => Joint1Slider,
            1 => Joint2Slider,
            2 => Joint3Slider,
            3 => Joint4Slider,
            4 => Joint5Slider,
            5 => Joint6Slider,
            _ => null
        };

        private void SyncJointSlidersFromModel()
        {
            _updatingJogUi = true;
            for (int i = 0; i < RobotKinematics.NumJoints; i++)
            {
                var slider = GetJointSlider(i);
                if (slider == null) continue;
                slider.Value = _jointAngles[i];
            }
            _updatingJogUi = false;
        }

        private void UpdateJogTelemetry()
        {
            var fk = RobotKinematics.FkFull(_jointAngles, _currentDh);
            var world = ToWorldTcp(fk.TcpPos);
            double x = world.X;
            double y = world.Y;
            double z = world.Z;
            TcpXText.Text = $"X: {x:F2}";
            TcpYText.Text = $"Y: {y:F2}";
            TcpZText.Text = $"Z: {z:F2}";
            TcpRxText.Text = $"Rx: {fk.TcpRpyDeg.Rx:F2}";
            TcpRyText.Text = $"Ry: {fk.TcpRpyDeg.Ry:F2}";
            TcpRzText.Text = $"Rz: {fk.TcpRpyDeg.Rz:F2}";
            IkStatusText.Text = _ikConverged ? "OK" : "FAIL";
            IkStatusText.Foreground = _ikConverged
                ? new SolidColorBrush(Color.FromRgb(80, 200, 80))
                : new SolidColorBrush(Color.FromRgb(220, 80, 80));
        }

        private void JointSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
        {
            if (_updatingJogUi) return;
            _jointAngles[0] = Joint1Slider.Value;
            _jointAngles[1] = Joint2Slider.Value;
            _jointAngles[2] = Joint3Slider.Value;
            _jointAngles[3] = Joint4Slider.Value;
            _jointAngles[4] = Joint5Slider.Value;
            _jointAngles[5] = Joint6Slider.Value;
            BuildRobot3D();
            SyncScene3D();
            UpdateJogTelemetry();
        }

        private void JogNudgeButton_Click(object sender, RoutedEventArgs e)
        {
            if (sender is not Button button || button.Tag is not string tag || tag.Length < 3)
                return;
            int jointIndex = int.Parse(tag[1].ToString()) - 1;
            bool increment = tag.EndsWith("+", StringComparison.Ordinal);
            if (jointIndex < 0 || jointIndex >= RobotKinematics.NumJoints) return;

            var slider = GetJointSlider(jointIndex);
            if (slider == null) return;

            double delta = increment ? JogStepDeg : -JogStepDeg;
            slider.Value = Math.Clamp(slider.Value + delta, slider.Minimum, slider.Maximum);
            AppendOutput($"J{jointIndex + 1}: {slider.Value:F1} deg");
        }

        private void ZeroJointsButton_Click(object sender, RoutedEventArgs e)
        {
            ZeroJoints();
            AppendOutput("Jog: все оси установлены в 0.");
        }

        private void JogRobotComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (_syncingRobotSelectors || JogRobotComboBox.SelectedIndex < 0) return;
            SwitchActiveRobot(JogRobotComboBox.SelectedIndex);
        }

        private void FramesComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            UpdateJogTelemetry();
        }

        private void TcpJogButton_Click(object sender, RoutedEventArgs e)
        {
            if (sender is not Button button || button.Tag is not string tag)
                return;
            double step = TcpStepMm;
            double dx = 0, dy = 0, dz = 0;
            if (tag == "X+") dx = step;
            else if (tag == "X-") dx = -step;
            else if (tag == "Y+") dy = step;
            else if (tag == "Y-") dy = -step;
            else if (tag == "Z+") dz = step;
            else if (tag == "Z-") dz = -step;
            else return;
            JogTcpBy(dx, dy, dz);
        }

        private void JogTcpBy(double dx, double dy, double dz)
        {
            var fk = RobotKinematics.FkFull(_jointAngles, _currentDh);
            var baseOffset = SelectedBaseOffset;
            var toolOffset = SelectedToolOffset;
            var worldTarget = (
                fk.TcpPos.X + baseOffset.X + toolOffset.X + dx,
                fk.TcpPos.Y + baseOffset.Y + toolOffset.Y + dy,
                fk.TcpPos.Z + baseOffset.Z + toolOffset.Z + dz);
            var robotTarget = (
                worldTarget.Item1 - baseOffset.X - toolOffset.X,
                worldTarget.Item2 - baseOffset.Y - toolOffset.Y,
                worldTarget.Item3 - baseOffset.Z - toolOffset.Z);

            if (!SolveIkPosition(robotTarget, out var solved))
            {
                StatusText.Text = "TCP-Jog: нет сходимости";
                AppendOutput(StatusText.Text);
                return;
            }

            _jointAngles = solved;
            BuildRobot3D();
            SyncScene3D();
            UpdateJogTelemetry();
            AppendOutput($"TCP-Jog -> X:{worldTarget.Item1:F1} Y:{worldTarget.Item2:F1} Z:{worldTarget.Item3:F1}");
        }

        private bool SolveIkPosition((double X, double Y, double Z) target, out double[] solvedAngles, double[]? seed = null)
        {
            bool ok = RobotKinematics.SolveIkPosition(
                target, seed ?? _jointAngles, _currentDh, _jointMinLimits, _jointMaxLimits, out solvedAngles);
            _ikConverged = ok;
            return ok;
        }

        private bool SolveIkFull((double X, double Y, double Z) pos, (double Rx, double Ry, double Rz) rpy,
            out double[] solvedAngles, double[]? seed = null)
        {
            bool ok = RobotKinematics.SolveIkFull(
                pos, rpy, seed ?? _jointAngles, _currentDh, _jointMinLimits, _jointMaxLimits, out solvedAngles);
            _ikConverged = ok;
            return ok;
        }

        private void AddWaypointButton_Click(object sender, RoutedEventArgs e)
        {
            var fk = RobotKinematics.FkFull(_jointAngles, _currentDh);
            var world = ToWorldTcp(fk.TcpPos);
            AddWaypointFromPose(
                world.X,
                world.Y,
                world.Z,
                fk.TcpRpyDeg.Rx,
                fk.TcpRpyDeg.Ry,
                fk.TcpRpyDeg.Rz);
        }

        private void AddWaypointFromPose(double x, double y, double z, double rx, double ry, double rz)
        {
            var pt = TrajectoryPoint.FromXyz(x, y, z, rx, ry, rz);
            double speed = ParseOrDefault(DefaultWaypointSpeedTextBox.Text, 120);
            double accel = ParseOrDefault(DefaultWaypointAccelTextBox.Text, 300);
            _programWaypoints.Add(new ProgramWaypoint
            {
                Index = _programWaypoints.Count + 1,
                X = pt.X,
                Y = pt.Y,
                Z = pt.Z,
                Rx = pt.Rx,
                Ry = pt.Ry,
                Rz = pt.Rz,
                Speed = speed,
                Accel = accel
            });
            RefreshWaypointsGrid();
            _selectedWaypointIndex = _programWaypoints.Count - 1;
            WaypointsGrid.SelectedIndex = _selectedWaypointIndex;
            if (_programOperations.Count == 0)
                AddOperation("MoveL");
            NormalizeOperationWaypointRefs();
            UpdateCycleTimeDisplay();
            AppendOutput($"Добавлена программная точка P{_programWaypoints.Count:000}.");
        }

        private void ClearWaypointsButton_Click(object sender, RoutedEventArgs e)
        {
            _programWaypoints.Clear();
            _selectedWaypointIndex = -1;
            RefreshWaypointsGrid();
            _programOperations.Clear();
            RefreshOperationsGrid();
            AppendOutput("Программные точки очищены.");
        }

        private void RunWaypointProgramButton_Click(object sender, RoutedEventArgs e)
        {
            if (_programWaypoints.Count == 0)
            {
                StatusText.Text = "Нет программных точек для выполнения.";
                AppendOutput(StatusText.Text);
                return;
            }
            StartSimulation();
        }

        private void StepWaypointProgramButton_Click(object sender, RoutedEventArgs e)
        {
            if (_programWaypoints.Count == 0)
            {
                StatusText.Text = "Нет программных точек.";
                AppendOutput(StatusText.Text);
                return;
            }

            int next = _selectedWaypointIndex + 1;
            if (next >= _programWaypoints.Count) next = 0;
            _selectedWaypointIndex = next;
            WaypointsGrid.SelectedIndex = next;
            var wp = _programWaypoints[next];
            MoveRobotToWaypoint(wp);
            StatusText.Text = $"Шаг программы: P{wp.Index:000}";
            AppendOutput(StatusText.Text);
        }

        private void MoveWaypointUpButton_Click(object sender, RoutedEventArgs e)
        {
            if (_selectedWaypointIndex <= 0 || _selectedWaypointIndex >= _programWaypoints.Count) return;
            int idx = _selectedWaypointIndex;
            (_programWaypoints[idx - 1], _programWaypoints[idx]) = (_programWaypoints[idx], _programWaypoints[idx - 1]);
            _selectedWaypointIndex--;
            RefreshWaypointsGrid();
            WaypointsGrid.SelectedIndex = _selectedWaypointIndex;
            AppendOutput($"Точка P{_selectedWaypointIndex + 1:000} перемещена вверх.");
        }

        private void MoveWaypointDownButton_Click(object sender, RoutedEventArgs e)
        {
            if (_selectedWaypointIndex < 0 || _selectedWaypointIndex >= _programWaypoints.Count - 1) return;
            int idx = _selectedWaypointIndex;
            (_programWaypoints[idx + 1], _programWaypoints[idx]) = (_programWaypoints[idx], _programWaypoints[idx + 1]);
            _selectedWaypointIndex++;
            RefreshWaypointsGrid();
            WaypointsGrid.SelectedIndex = _selectedWaypointIndex;
            AppendOutput($"Точка P{_selectedWaypointIndex + 1:000} перемещена вниз.");
        }

        private void DeleteWaypointButton_Click(object sender, RoutedEventArgs e)
        {
            if (_selectedWaypointIndex < 0 || _selectedWaypointIndex >= _programWaypoints.Count) return;
            int removed = _selectedWaypointIndex + 1;
            _programWaypoints.RemoveAt(_selectedWaypointIndex);
            if (_selectedWaypointIndex >= _programWaypoints.Count) _selectedWaypointIndex = _programWaypoints.Count - 1;
            RefreshWaypointsGrid();
            WaypointsGrid.SelectedIndex = _selectedWaypointIndex;
            NormalizeOperationWaypointRefs();
            AppendOutput($"Удалена точка P{removed:000}.");
        }

        private void SaveProgramButton_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new SaveFileDialog
            {
                Filter = "Kenga Program (*.kprog)|*.kprog|JSON (*.json)|*.json|All (*.*)|*.*",
                FileName = "robot_program.kprog"
            };
            if (dlg.ShowDialog() != true) return;
            var dto = new ProgramFileDto
            {
                Robot = _currentRobotName,
                Tool = ToolFrameComboBox.SelectedItem?.ToString() ?? "TOOL0",
                Base = BaseFrameComboBox.SelectedItem?.ToString() ?? "BASE0",
                Waypoints = _programWaypoints.ToList(),
                Operations = _programOperations.ToList()
            };
            var options = new JsonSerializerOptions { WriteIndented = true };
            System.IO.File.WriteAllText(dlg.FileName, JsonSerializer.Serialize(dto, options));
            AppendOutput($"Программа сохранена: {dlg.FileName}");
        }

        private void LoadProgramButton_Click(object sender, RoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Filter = "Kenga Program (*.kprog;*.json)|*.kprog;*.json|All (*.*)|*.*"
            };
            if (dlg.ShowDialog() != true) return;
            try
            {
                var json = System.IO.File.ReadAllText(dlg.FileName);
                var dto = JsonSerializer.Deserialize<ProgramFileDto>(json);
                if (dto == null) throw new InvalidOperationException("Пустой файл программы.");

                _programWaypoints.Clear();
                foreach (var wp in dto.Waypoints ?? new List<ProgramWaypoint>())
                    _programWaypoints.Add(wp);
                RefreshWaypointsGrid();
                _programOperations.Clear();
                foreach (var op in dto.Operations ?? new List<ProgramOperation>())
                    _programOperations.Add(op);
                RefreshOperationsGrid();
                NormalizeOperationWaypointRefs();

                if (!string.IsNullOrWhiteSpace(dto.Robot))
                    LoadRobotPreset(dto.Robot);
                if (!string.IsNullOrWhiteSpace(dto.Tool) && _toolFrames.ContainsKey(dto.Tool))
                    ToolFrameComboBox.SelectedItem = dto.Tool;
                if (!string.IsNullOrWhiteSpace(dto.Base) && _baseFrames.ContainsKey(dto.Base))
                    BaseFrameComboBox.SelectedItem = dto.Base;

                _selectedWaypointIndex = _programWaypoints.Count > 0 ? 0 : -1;
                WaypointsGrid.SelectedIndex = _selectedWaypointIndex;
                _selectedOperationIndex = _programOperations.Count > 0 ? 0 : -1;
                OperationsGrid.SelectedIndex = _selectedOperationIndex;
                AppendOutput($"Программа загружена: {dlg.FileName} ({_programWaypoints.Count} точек).");
            }
            catch (Exception ex)
            {
                AppendOutput($"Ошибка загрузки программы: {ex.Message}");
            }
        }

        private void StopProgramButton_Click(object sender, RoutedEventArgs e)
        {
            StopSimulation();
            AppendOutput("Выполнение программы остановлено.");
        }

        private void WaypointsGrid_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _selectedWaypointIndex = WaypointsGrid.SelectedIndex;
        }

        private void WaypointsGrid_CellEditEnding(object sender, DataGridCellEditEndingEventArgs e)
        {
            Dispatcher.BeginInvoke(new Action(() =>
            {
                RefreshWaypointsGrid();
                if (_selectedWaypointIndex >= 0 && _selectedWaypointIndex < _programWaypoints.Count)
                    AppendOutput($"Изменена точка P{_selectedWaypointIndex + 1:000}.");
            }), DispatcherPriority.Background);
        }

        private void OperationsGrid_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            _selectedOperationIndex = OperationsGrid.SelectedIndex;
        }

        private void OperationsGrid_CellEditEnding(object sender, DataGridCellEditEndingEventArgs e)
        {
            Dispatcher.BeginInvoke(new Action(() =>
            {
                RefreshOperationsGrid();
                if (_selectedOperationIndex >= 0 && _selectedOperationIndex < _programOperations.Count)
                    AppendOutput($"Изменена операция O{_selectedOperationIndex + 1:000}.");
            }), DispatcherPriority.Background);
        }

        private void AddMoveLOperationButton_Click(object sender, RoutedEventArgs e)
            => AddOperation("MoveL");
        private void AddMoveJOperationButton_Click(object sender, RoutedEventArgs e)
            => AddOperation("MoveJ");
        private void AddWaitOperationButton_Click(object sender, RoutedEventArgs e)
            => AddOperation("Wait");
        private void AddIoOperationButton_Click(object sender, RoutedEventArgs e)
            => AddOperation("IO");

        private void AddOperation(string type)
        {
            int wpIndex = _selectedWaypointIndex >= 0 ? _selectedWaypointIndex + 1 : Math.Max(1, _programWaypoints.Count);
            _programOperations.Add(new ProgramOperation
            {
                Index = _programOperations.Count + 1,
                Type = type,
                WaypointIndex = wpIndex,
                Speed = ParseOrDefault(DefaultWaypointSpeedTextBox.Text, 120),
                Accel = ParseOrDefault(DefaultWaypointAccelTextBox.Text, 300),
                WaitMs = 500,
                IoChannel = "DO1",
                IoValue = true
            });
            RefreshOperationsGrid();
            _selectedOperationIndex = _programOperations.Count - 1;
            OperationsGrid.SelectedIndex = _selectedOperationIndex;
            UpdateCycleTimeDisplay();
            AppendOutput($"Добавлена операция {type}.");
        }

        private void MoveOperationUpButton_Click(object sender, RoutedEventArgs e)
        {
            if (_selectedOperationIndex <= 0 || _selectedOperationIndex >= _programOperations.Count) return;
            int idx = _selectedOperationIndex;
            (_programOperations[idx - 1], _programOperations[idx]) = (_programOperations[idx], _programOperations[idx - 1]);
            _selectedOperationIndex--;
            RefreshOperationsGrid();
            OperationsGrid.SelectedIndex = _selectedOperationIndex;
        }

        private void MoveOperationDownButton_Click(object sender, RoutedEventArgs e)
        {
            if (_selectedOperationIndex < 0 || _selectedOperationIndex >= _programOperations.Count - 1) return;
            int idx = _selectedOperationIndex;
            (_programOperations[idx + 1], _programOperations[idx]) = (_programOperations[idx], _programOperations[idx + 1]);
            _selectedOperationIndex++;
            RefreshOperationsGrid();
            OperationsGrid.SelectedIndex = _selectedOperationIndex;
        }

        private void DeleteOperationButton_Click(object sender, RoutedEventArgs e)
        {
            if (_selectedOperationIndex < 0 || _selectedOperationIndex >= _programOperations.Count) return;
            _programOperations.RemoveAt(_selectedOperationIndex);
            if (_selectedOperationIndex >= _programOperations.Count) _selectedOperationIndex = _programOperations.Count - 1;
            RefreshOperationsGrid();
            OperationsGrid.SelectedIndex = _selectedOperationIndex;
            AppendOutput("Команда отменена.");
        }

        private void NormalizeOperationWaypointRefs()
        {
            int maxWp = _programWaypoints.Count;
            foreach (var op in _programOperations)
            {
                if (maxWp <= 0) op.WaypointIndex = 0;
                else if (op.WaypointIndex < 1) op.WaypointIndex = 1;
                else if (op.WaypointIndex > maxWp) op.WaypointIndex = maxWp;
            }
            RefreshOperationsGrid();
        }

        private double ParseOrDefault(string? text, double fallback)
            => double.TryParse(text, out double v) ? v : fallback;

        private void BindCheckboxes()
        {
            GridCheckBox.Checked += (_, __) => { _gridVisible = true; DrawingCanvas?.InvalidateVisual(); };
            GridCheckBox.Unchecked += (_, __) => { _gridVisible = false; DrawingCanvas?.InvalidateVisual(); };
            OrthoCheckBox.Checked += (_, __) => {
                _orthoMode = true;
                OrthoStatus.Text = "ВКЛ";
                OrthoStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#4CAF50"));
            };
            OrthoCheckBox.Unchecked += (_, __) => {
                _orthoMode = false;
                OrthoStatus.Text = "ВЫКЛ";
                OrthoStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F44336"));
            };
            SnapCheckBox.Checked += (_, __) => {
                _snapEnabled = true;
                SnapStatus.Text = "ВКЛ";
                SnapStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#4CAF50"));
            };
            SnapCheckBox.Unchecked += (_, __) => {
                _snapEnabled = false;
                SnapStatus.Text = "ВЫКЛ";
                SnapStatus.Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F44336"));
            };
        }

        private void ExportGCode_Click(object sender, RoutedEventArgs e) => ExportGCode_Executed(sender, e);
        private void ExportKRL_Click(object sender, RoutedEventArgs e) => ExportKRL_Executed(sender, e);
        private void ExportRAPID_Click(object sender, RoutedEventArgs e) => ExportRAPID_Executed(sender, e);
        private void ExportTP_Click(object sender, RoutedEventArgs e) => ExportTP_Executed(sender, e);
        private void ExportYaskawa_Click(object sender, RoutedEventArgs e) => ExportYaskawa_Executed(sender, e);
        private void ExportUR_Click(object sender, RoutedEventArgs e) => ExportUR_Executed(sender, e);

        private void RibbonCommand_Click(object sender, RoutedEventArgs e)
        {
            if ((sender as System.Windows.Controls.Button)?.Tag is not string tag) return;
            var cmd = tag.ToUpperInvariant();
            if (cmd == "ZOOMEXTENTS") { ZoomExtents(); return; }
            if (cmd == "ZOOMIN") { ZoomIn(); return; }
            if (cmd == "ZOOMOUT") { ZoomOut(); return; }
            if (cmd == "SIMULATE") { StartSimulation(); return; }
            if (cmd == "SIMPAUSE") { PauseSimulation(); return; }
            if (cmd == "SIMSTOP") { StopSimulation(); return; }
            if (cmd == "SIMRESET") { ResetSimulation(); return; }
            if (cmd == "LOADROBOT") { LoadSelectedRobotPreset(); return; }
            if (cmd == "LOADDEMOROBOT") { LoadDemoRobotAndSimulate(); return; }
            if (cmd == "ZEROJOINTS") { ZeroJoints(); return; }
            if (cmd == "TRAJFROMPOLYLINE") { TrajFromPolyline(); return; }
            if (cmd == "TRAJSPLINE") { BuildTrajectoryFromDrawing("SPLINE"); return; }
            if (cmd == "TRAJSMOOTH") { BuildTrajectoryFromDrawing("SMOOTH"); return; }
            if (cmd == "TRAJSPIRAL") { BuildTrajectoryFromDrawing("SPIRAL"); return; }
            if (cmd == "LAYERNEW") { LayerNew(); return; }
            if (cmd == "VIEWTOP") { ViewTop_Click(sender, e); return; }
            if (cmd == "VIEWFRONT") { ViewFront_Click(sender, e); return; }
            if (cmd == "VIEWLEFT") { ViewLeft_Click(sender, e); return; }
            if (cmd == "VIEW3D") { ViewIso_Click(sender, e); return; }
            if (cmd == "IMPORTSTEP") { ImportFile("STEP", "STEP (*.stp;*.step)|*.stp;*.step"); return; }
            if (cmd == "IMPORTIGES") { ImportFile("IGES", "IGES (*.igs;*.iges)|*.igs;*.iges"); return; }
            if (cmd == "IMPORTSTL") { ImportFile("STL", "STL (*.stl)|*.stl"); return; }
            if (cmd == "IMPORTOBJ") { ImportFile("OBJ", "OBJ (*.obj)|*.obj"); return; }
            if (cmd == "IMPORTGLTF") { ImportFile("glTF", "glTF (*.gltf;*.glb)|*.gltf;*.glb"); return; }
            if (cmd == "CHECKCOLLISION") { RunCollisionCheck(); return; }
            if (cmd == "SELFCOLLISION") { RunSelfCollisionCheck(); return; }
            if (cmd == "CYCLETIME") { ShowCycleTime(); return; }
            if (cmd == "ADDTABLE") { AddWorkcellObject(WorkcellType.Table); return; }
            if (cmd == "ADDFIXTURE") { AddWorkcellObject(WorkcellType.Fixture); return; }
            if (cmd == "ADDFENCE") { AddWorkcellObject(WorkcellType.Fence); return; }
            if (cmd == "ADDCONVEYOR") { AddWorkcellObject(WorkcellType.Conveyor); return; }
            if (cmd == "ADDROBOT") { AddRobotInstance(); return; }
            if (cmd == "CLEARWORKCELL") { ClearWorkcell(); return; }
            if (cmd == "EXPORTPDF") { ExportPdfDrawing(); return; }
            if (cmd == "EXPORTCSV") { ExportTrajectoryCsv(); return; }
            if (cmd == "IMPORTCSV") { ImportTrajectoryCsv(); return; }
            if (cmd == "INSERTBLOCK") { BeginInsertBlock(); return; }
            if (cmd == "TEXT" || cmd == "DIMLINEAR" || cmd == "DIMRADIUS") { SetCurrentCommand(cmd); return; }
            if (cmd == "ROTATE" || cmd == "SCALE" || cmd == "MIRROR" || cmd == "TRIM" || cmd == "EXTEND" || cmd == "FILLET") { SetCurrentCommand(cmd); return; }
            SetCurrentCommand(cmd);
        }

        private void ImportFile(string format, string filter)
        {
            var dlg = new OpenFileDialog { Filter = filter };
            if (dlg.ShowDialog() != true) return;
            try
            {
                string path = dlg.FileName;
                string fname = System.IO.Path.GetFileName(path);
                MeshGeometry3D? mesh = null;
                ModelVisual3D? visual = null;

                if (format == "STL")
                {
                    var stl = StlLoader.Load(path);
                    mesh = stl.Mesh;
                    visual = StlLoader.CreateModelVisual(stl);
                }
                else if (format == "OBJ")
                {
                    var obj = ObjLoader.Load(path);
                    mesh = obj.Mesh;
                    visual = ObjLoader.CreateModelVisual(obj);
                }
                else if (format == "GLTF")
                {
                    var (gMesh, name) = GltfLoader.Load(path);
                    mesh = gMesh;
                    visual = GltfLoader.CreateModelVisual(gMesh);
                    fname = name + System.IO.Path.GetExtension(path);
                }
                else if (format == "STEP" || format == "IGES")
                {
                    var stlPath = ExternalCadConverter.TryConvertStepToStl(path);
                    if (stlPath != null && System.IO.File.Exists(stlPath))
                    {
                        var stl = StlLoader.Load(stlPath);
                        mesh = stl.Mesh;
                        visual = StlLoader.CreateModelVisual(stl);
                        StatusText.Text = $"Импорт {format}: конвертирован через FreeCAD → STL";
                    }
                    else
                    {
                        StatusText.Text = $"Импорт {format}: {CadImportHints.StepHint}";
                        AppendOutput(StatusText.Text);
                        return;
                    }
                }

                if (visual != null && mesh != null)
                {
                    var wc = new WorkcellObject
                    {
                        Name = fname,
                        Type = WorkcellType.ImportedMesh,
                        X = _robotBaseCad.X + 400,
                        Y = _robotBaseCad.Y,
                        Z = 0,
                        Color = Color.FromRgb(120, 130, 150)
                    };
                    MeshGeometryHelper.ApplyBoundsToWorkcell(wc, mesh, _robotBaseCad.X + 400, _robotBaseCad.Y, 0);
                    wc.CollisionMesh = mesh;
                    _workcellObjects.Add(wc);
                    WorkcellModel3D.Children.Add(visual);
                    var b = MeshGeometryHelper.ComputeBounds(mesh);
                    visual.Transform = new TranslateTransform3D(
                        wc.X - (b.MinX + b.MaxX) * 0.5,
                        -(wc.Y + (b.MinY + b.MaxY) * 0.5),
                        wc.Z - b.MinZ);
                    SyncScene3D();
                    RefreshProjectTree();
                    StatusText.Text = $"Импорт {format}: {fname} ({GetMeshTriCount(visual)} треуг., mesh-коллизия)";
                    AppendOutput(StatusText.Text);
                }
                else
                    StatusText.Text = $"Импорт {format}: {fname} — формат не поддерживается";
            }
            catch (Exception ex)
            {
                StatusText.Text = $"Ошибка импорта {format}: {ex.Message}";
                AppendOutput(StatusText.Text);
            }
        }

        private static int GetMeshTriCount(ModelVisual3D vis)
        {
            int count = 0;
            foreach (var child in vis.Children)
                if (child is ModelVisual3D mv && mv.Content is GeometryModel3D gm && gm.Geometry is MeshGeometry3D m)
                    count += m.TriangleIndices.Count / 3;
            if (vis.Content is GeometryModel3D g && g.Geometry is MeshGeometry3D mesh)
                count += mesh.TriangleIndices.Count / 3;
            return count;
        }

        private void ExportPdfDrawing()
        {
            var dlg = new SaveFileDialog { Filter = "PDF (*.pdf)|*.pdf", FileName = "drawing.pdf" };
            if (dlg.ShowDialog() != true) return;
            if (PdfExporter.ExportDrawing(_entities, dlg.FileName))
            {
                StatusText.Text = "PDF экспорт: " + dlg.FileName;
                AppendOutput(StatusText.Text);
            }
        }

        private void ExportTrajectoryCsv()
        {
            var pts = GetActiveTrajectory();
            if (pts.Count == 0) { StatusText.Text = "Нет траектории для экспорта CSV."; return; }
            var dlg = new SaveFileDialog { Filter = "CSV (*.csv)|*.csv", FileName = "trajectory.csv" };
            if (dlg.ShowDialog() != true) return;
            TrajectoryIO.ExportCsv(pts, dlg.FileName);
            StatusText.Text = "CSV экспорт: " + dlg.FileName;
            AppendOutput(StatusText.Text);
        }

        private void ImportTrajectoryCsv()
        {
            var dlg = new OpenFileDialog { Filter = "CSV (*.csv)|*.csv|All (*.*)|*.*" };
            if (dlg.ShowDialog() != true) return;
            var wps = TrajectoryIO.ImportCsv(dlg.FileName);
            if (wps.Count == 0) { StatusText.Text = "CSV: точки не найдены."; return; }
            _programWaypoints.Clear();
            foreach (var wp in wps) _programWaypoints.Add(wp);
            RefreshWaypointsGrid();
            _selectedWaypointIndex = 0;
            WaypointsGrid.SelectedIndex = 0;
            StatusText.Text = $"CSV импорт: {wps.Count} точек программы";
            AppendOutput(StatusText.Text);
        }

        private void CreateBlock()
        {
            var selected = _entities.Where(e => e.IsSelected).ToList();
            if (selected.Count == 0) { StatusText.Text = "Выделите объекты для блока (хотя бы один)."; return; }
            var name = InputDialog.Prompt("Создать блок", "Имя блока:", $"Block_{_blocks.Count + 1}");
            if (string.IsNullOrWhiteSpace(name)) return;
            float minX = float.MaxValue, minY = float.MaxValue;
            foreach (var e in selected) { e.GetBounds(out float x0, out float y0, out _, out _); minX = Math.Min(minX, x0); minY = Math.Min(minY, y0); }
            var block = new CadBlockDefinition
            {
                Name = name.Trim(),
                BasePoint = new SKPoint(minX, minY),
                Entities = selected.Select(e => e.Clone()).ToList()
            };
            _blocks.Add(block);
            StatusText.Text = $"Блок «{block.Name}» создан ({selected.Count} объектов).";
            AppendOutput(StatusText.Text);
        }

        private void BeginInsertBlock()
        {
            if (_blocks.Count == 0) { StatusText.Text = "Нет сохранённых блоков. Сначала создайте блок."; return; }
            _pendingBlockInsert = _blocks[^1];
            SetCurrentCommand("INSERTBLOCK");
            StatusText.Text = $"INSERTBLOCK: укажите точку вставки блока «{_pendingBlockInsert.Name}»";
        }

        private void BuildTrajectoryFromDrawing(string mode)
        {
            var control = TrajectoryBuilder.CollectPolylinePoints(_entities);
            if (control.Count < 2)
            {
                StatusText.Text = "Постройте полилинию или дугу для траектории.";
                AppendOutput(StatusText.Text);
                return;
            }
            SKPoint? center = mode == "SPIRAL"
                ? new SKPoint(control.Average(p => p.X), control.Average(p => p.Y))
                : null;
            var poly = TrajectoryBuilder.BuildTrajectoryPolyline(_entities, mode, center);
            if (poly == null)
            {
                StatusText.Text = "Не найдена замкнутая полилиния.";
                return;
            }
            _entities.Add(poly);
            SaveState();
            DrawingCanvas.InvalidateVisual();
            StatusText.Text = $"Траектория ({mode}): {poly.Points.Count} точек. Нажмите Старт для симуляции.";
            AppendOutput(StatusText.Text);
        }

        private void LayerNew()
        {
            int n = LayerComboBox.Items.Count + 1;
            string name = "Слой " + n;
            LayerComboBox.Items.Add(name);
            LayerComboBox.SelectedItem = name;
            _currentLayer = name;
            CurrentLayerText.Text = name;
            StatusText.Text = "Новый слой: " + name;
            AppendOutput(StatusText.Text);
        }

        private void ZeroJoints()
        {
            _jointAngles = new double[6];
            BuildRobot3D();
            StatusText.Text = "Сетка включена";
            AppendOutput(StatusText.Text);
        }

        private void TrajFromPolyline()
        {
            var pts = GetActiveTrajectory();
            if (pts.Count == 0)
                StatusText.Text = "Постройте полилинию или дугу, затем запустите симуляцию.";
            else
                StatusText.Text = $"Траектория из чертежа: {pts.Count} точек. Нажмите Старт для симуляции.";
            AppendOutput(StatusText.Text);
        }

        private void SetCurrentCommand(string cmd)
        {
            if (cmd != "POLYLINE")
                _polylinePoints.Clear();
            _editBaseSet = false;
            _editRefEntity = null;
            _editRefEntity2 = null;
            _dimPoints.Clear();
            _currentCommand = cmd;
            StatusText.Text = cmd switch
            {
                "LINE" => "LINE: укажите первую точку",
                "CIRCLE" => "CIRCLE: укажите центр окружности",
                "ARC" => "ARC: укажите начальную точку дуги",
                "POLYLINE" => "POLYLINE: укажите первую точку",
                "RECTANGLE" => "RECTANGLE: укажите первый угол",
                "MOVE" => "MOVE: выберите объекты",
                "COPY" => "COPY: выберите объекты",
                "ROTATE" => "ROTATE: выберите объекты",
                "SCALE" => "SCALE: выберите объекты",
                "MIRROR" => "MIRROR: выберите объекты",
                "TRIM" => "TRIM: выберите границу",
                "EXTEND" => "EXTEND: выберите границу",
                "FILLET" => "FILLET: выберите первую линию",
                "LAYERNEW" => "Создание нового слоя",
                "ZOOMIN" => "Увеличение масштаба",
                "ZOOMOUT" => "Уменьшение масштаба",
                "PAN" => "Панорама: перетаскивайте вид",
                "VIEWTOP" => "Вид сверху",
                "VIEWFRONT" => "Вид спереди",
                "VIEWLEFT" => "Вид слева",
                "VIEW3D" => "3D вид",
                "LOADROBOT" => "Загрузить модель робота",
                "LOADDEMOROBOT" => "Демо-робот",
                "ZEROJOINTS" => "Сбросить в ноль",
                "TRAJFROMPOLYLINE" => "Траектория из полилинии",
                "TRAJSPLINE" => "Сплайн траектории",
                "TRAJSMOOTH" => "Сглаженная траектория",
                "TRAJSPIRAL" => "Спиральная траектория",
                "SIMULATE" => "Старт симуляции",
                "SIMPAUSE" => "Пауза",
                "SIMSTOP" => "Стоп",
                "SIMRESET" => "Сброс",
                "IMPORTSTEP" => "Импорт STEP",
                "IMPORTIGES" => "Импорт IGES",
                "IMPORTSTL" => "Импорт STL",
                "IMPORTGLTF" => "Импорт glTF",
                "CREATEBLOCK" => "Создать блок из выделения",
                "INSERTBLOCK" => "Вставить блок",
                "TEXT" => "Разместить текст",
                "DIMLINEAR" => "Линейный размер",
                "DIMRADIUS" => "Радиальный размер",
                _ => $"{cmd}: готово"
            };
        }

        private List<TrajectoryPoint> GetTrajectoryFromEntities()
        {
            var points = new List<TrajectoryPoint>();
            foreach (var entity in _entities)
            {
                if (entity is LineEntity line)
                {
                    points.Add(TrajectoryPoint.FromXyz(line.Start.X, line.Start.Y, 0));
                    points.Add(TrajectoryPoint.FromXyz(line.End.X, line.End.Y, 0));
                }
                else if (entity is CircleEntity circle)
                    points.Add(TrajectoryPoint.FromXyz(circle.Center.X, circle.Center.Y, 0));
                else if (entity is RectangleEntity rect)
                {
                    points.Add(TrajectoryPoint.FromXyz(rect.X0, rect.Y0, 0));
                    points.Add(TrajectoryPoint.FromXyz(rect.X1, rect.Y0, 0));
                    points.Add(TrajectoryPoint.FromXyz(rect.X1, rect.Y1, 0));
                    points.Add(TrajectoryPoint.FromXyz(rect.X0, rect.Y1, 0));
                }
                else if (entity is PolylineEntity pl)
                    foreach (var p in pl.Points)
                        points.Add(TrajectoryPoint.FromXyz(p.X, p.Y, 0));
            }
            return points;
        }

        private List<TrajectoryPoint> GetActiveTrajectory()
        {
            if (_programWaypoints.Count > 0)
                return _programWaypoints.Select(p => TrajectoryPoint.FromXyz(p.X, p.Y, p.Z, p.Rx, p.Ry, p.Rz)).ToList();
            return GetTrajectoryFromEntities();
        }

        private void MoveRobotToWaypoint(ProgramWaypoint wp)
        {
            var robotTarget = ToRobotTcp((wp.X, wp.Y, wp.Z));
            var rpy = (wp.Rx, wp.Ry, wp.Rz);
            double[] solvedFull;
            bool ok;
            if (Math.Abs(wp.Rx) + Math.Abs(wp.Ry) + Math.Abs(wp.Rz) > 0.1)
                ok = SolveIkFull(robotTarget, rpy, out solvedFull);
            else
                ok = SolveIkPosition(robotTarget, out solvedFull);
            if (!ok) { AppendOutput($"IK FAIL для P{wp.Index:000}"); return; }
            _jointAngles = solvedFull;
            BuildRobot3D();
            SyncScene3D();
            UpdateJogTelemetry();
        }

        private void ExportGCode_Executed(object sender, RoutedEventArgs e)
        {
            var pts = GetActiveTrajectory();
            if (pts.Count == 0) { StatusText.Text = "Нет траектории. Добавьте точки или полилинию."; return; }
            var dlg = new SaveFileDialog { Filter = "G-code (*.gcode)|*.gcode|All (*.*)|*.*", FileName = "trajectory.gcode" };
            if (dlg.ShowDialog() != true) return;
            StatusText.Text = Postprocessors.ExportGCode(pts, dlg.FileName) ? "Экспорт G-code: " + dlg.FileName : "Ошибка экспорта.";
            AppendOutput(StatusText.Text);
        }

        private void ExportKRL_Executed(object sender, RoutedEventArgs e)
        {
            var pts = GetActiveTrajectory();
            if (pts.Count == 0) { StatusText.Text = "Нет траектории. Добавьте точки или полилинию."; return; }
            var dlg = new SaveFileDialog { Filter = "KUKA KRL (*.krl)|*.krl|All (*.*)|*.*", FileName = "trajectory.krl" };
            if (dlg.ShowDialog() != true) return;
            StatusText.Text = Postprocessors.ExportKukaKrl(pts, dlg.FileName) ? "Экспорт KUKA KRL: " + dlg.FileName : "Ошибка экспорта.";
            AppendOutput(StatusText.Text);
        }

        private void ExportRAPID_Executed(object sender, RoutedEventArgs e)
        {
            var pts = GetActiveTrajectory();
            if (pts.Count == 0) { StatusText.Text = "Нет траектории. Добавьте точки или полилинию."; return; }
            var dlg = new SaveFileDialog { Filter = "ABB RAPID (*.mod)|*.mod|All (*.*)|*.*", FileName = "trajectory.mod" };
            if (dlg.ShowDialog() != true) return;
            StatusText.Text = Postprocessors.ExportAbbRapid(pts, dlg.FileName) ? "Экспорт ABB RAPID: " + dlg.FileName : "Ошибка экспорта.";
            AppendOutput(StatusText.Text);
        }

        private void ExportTP_Executed(object sender, RoutedEventArgs e)
        {
            var pts = GetActiveTrajectory();
            if (pts.Count == 0) { StatusText.Text = "Нет траектории. Добавьте точки или полилинию."; return; }
            var dlg = new SaveFileDialog { Filter = "Fanuc TP (*.ls)|*.ls|All (*.*)|*.*", FileName = "trajectory.ls" };
            if (dlg.ShowDialog() != true) return;
            StatusText.Text = Postprocessors.ExportFanucTp(pts, dlg.FileName) ? "Экспорт Fanuc TP: " + dlg.FileName : "Ошибка экспорта.";
            AppendOutput(StatusText.Text);
        }

        private void ExportYaskawa_Executed(object sender, RoutedEventArgs e)
        {
            var pts = GetActiveTrajectory();
            if (pts.Count == 0) { StatusText.Text = "Нет траектории. Добавьте точки или полилинию."; return; }
            var dlg = new SaveFileDialog { Filter = "Yaskawa INFORM (*.jbi)|*.jbi|All (*.*)|*.*", FileName = "trajectory.jbi" };
            if (dlg.ShowDialog() != true) return;
            StatusText.Text = Postprocessors.ExportYaskawaInform(pts, dlg.FileName) ? "Экспорт Yaskawa INFORM: " + dlg.FileName : "Ошибка экспорта.";
            AppendOutput(StatusText.Text);
        }

        private void ExportUR_Executed(object sender, RoutedEventArgs e)
        {
            var pts = GetActiveTrajectory();
            if (pts.Count == 0) { StatusText.Text = "Нет траектории. Добавьте точки или полилинию."; return; }
            var dlg = new SaveFileDialog { Filter = "UR Script (*.urp)|*.urp|All (*.*)|*.*", FileName = "trajectory.urp" };
            if (dlg.ShowDialog() != true) return;
            StatusText.Text = Postprocessors.ExportUrScript(pts, dlg.FileName) ? "Экспорт UR Script: " + dlg.FileName : "Ошибка экспорта.";
            AppendOutput(StatusText.Text);
        }

        private void DeleteCommand_Executed(object sender, ExecutedRoutedEventArgs e)
        {
            for (int i = _entities.Count - 1; i >= 0; i--)
                if (_entities[i].IsSelected)
                    _entities.RemoveAt(i);
            DrawingCanvas?.InvalidateVisual();
            SyncScene3D();
            StatusText.Text = "Удалено";
        }

        private void InitializeDrawing()
        {
            _bitmap = new SKBitmap(2000, 2000);
            _canvas = new SKCanvas(_bitmap);
            _canvas.Clear(SKColor.Parse("#1E1E1E"));
        }

        private void InitializeComboBoxes()
        {
            // Слои
            LayerComboBox.Items.Add("0");
            LayerComboBox.Items.Add("Dimensions");
            LayerComboBox.Items.Add("Text");
            LayerComboBox.Items.Add("Hidden");
            LayerComboBox.SelectedIndex = 0;
            LayerComboBox.SelectionChanged += (s, e) => _currentLayer = LayerComboBox.SelectedItem?.ToString() ?? "0";

            // Цвета
            ColorComboBox.Items.Add("White");
            ColorComboBox.Items.Add("Black");
            ColorComboBox.Items.Add("Red");
            ColorComboBox.Items.Add("Yellow");
            ColorComboBox.Items.Add("Green");
            ColorComboBox.Items.Add("Cyan");
            ColorComboBox.Items.Add("Blue");
            ColorComboBox.Items.Add("Magenta");
            ColorComboBox.SelectedIndex = 0;
            ColorComboBox.SelectionChanged += (s, e) =>
            {
                var colorName = ColorComboBox.SelectedItem?.ToString() ?? "White";
                _currentColor = (Color)ColorConverter.ConvertFromString(colorName);
                CurrentColorIndicator.Fill = new SolidColorBrush(_currentColor);
            };

            // Тип линии
            LineTypeComboBox.Items.Add("Continuous");
            LineTypeComboBox.Items.Add("Dashed");
            LineTypeComboBox.Items.Add("Dotted");
            LineTypeComboBox.Items.Add("DashDot");
            LineTypeComboBox.SelectedIndex = 0;
        }

        private void InitializeRobotPresets()
        {
            RobotPresetComboBox.Items.Clear();
            RobotPresetComboBox.Items.Add("— выберите модель —");
            foreach (var robot in RobotLibrary.Robots)
                RobotPresetComboBox.Items.Add(robot.DisplayName);
            RobotPresetComboBox.SelectedIndex = 0;

            // JogRobotComboBox — экземпляры роботов в ячейке (InitializeRobotInstances)
        }

        private void RobotPresetComboBox_SelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (RobotPresetComboBox.SelectedIndex <= 0) return;
            var name = RobotPresetComboBox.SelectedItem?.ToString() ?? "";
            if (string.IsNullOrEmpty(name) || name.StartsWith("—")) return;
            LoadRobotPreset(name);
        }

        private void LoadSelectedRobotPreset()
        {
            if (RobotPresetComboBox.SelectedIndex > 0)
            {
                var name = RobotPresetComboBox.SelectedItem?.ToString() ?? "";
                LoadRobotPreset(name);
                return;
            }
            var dlg = new OpenFileDialog
            {
                Filter = "3D Models (*.stl;*.obj)|*.stl;*.obj|STL (*.stl)|*.stl|OBJ (*.obj)|*.obj",
                Title = "Загрузить 3D-модель робота"
            };
            if (dlg.ShowDialog() != true) return;
            try
            {
                ModelVisual3D? visual = null;
                string ext = System.IO.Path.GetExtension(dlg.FileName).ToLower();
                string fname = System.IO.Path.GetFileName(dlg.FileName);
                if (ext == ".stl")
                {
                    var stl = StlLoader.Load(dlg.FileName);
                    visual = StlLoader.CreateModelVisual(stl);
                }
                else if (ext == ".obj")
                {
                    var obj = ObjLoader.Load(dlg.FileName);
                    visual = ObjLoader.CreateModelVisual(obj);
                }
                if (visual != null)
                {
                    RobotModel.Children.Clear();
                    RobotModel.Children.Add(visual);
                    _currentRobotName = fname;
                    SyncScene3D();
                    StatusText.Text = $"Модель загружена из файла: {fname}";
                    UpdateJogTelemetry();
                    AppendOutput(StatusText.Text);
                }
                else
                    StatusText.Text = $"Формат {ext} не поддерживается";
            }
            catch (Exception ex)
            {
                StatusText.Text = $"Ошибка загрузки: {ex.Message}";
            }
        }

        private void LoadDemoRobotAndSimulate()
        {
            var demo = RobotLibrary.Robots.FirstOrDefault();
            if (demo != null)
            {
                int idx = RobotPresetComboBox.Items.IndexOf(demo.DisplayName);
                if (idx >= 0) RobotPresetComboBox.SelectedIndex = idx;
                else LoadRobotPreset(demo.DisplayName);
            }
            else
                LoadRobotPreset("Демо (6 осей)");
            if (_workcellObjects.Count == 0)
                AddWorkcellObject(WorkcellType.Table);
            StartSimulation();
        }

        private double[] _jointAngles = new double[6];
        private DhParams[] _currentDh = RobotKinematics.DefaultDh;
        private string _currentRobotName = "";

        private static readonly Dictionary<string, (byte R, byte G, byte B)> RobotColors = new()
        {
            { "KUKA", (255, 102, 0) },
            { "ABB", (255, 50, 50) },
            { "Fanuc", (255, 210, 0) },
            { "UR", (30, 90, 180) },
        };

        private void LoadRobotPreset(string name)
        {
            _currentRobotName = name;
            _currentRobotDef = RobotLibrary.FindByDisplayName(name);
            if (_currentRobotDef != null)
            {
                _currentDh = _currentRobotDef.DhParams.Length >= 6
                    ? _currentRobotDef.DhParams
                    : RobotKinematics.DefaultDh;
            }
            else
            {
                _currentDh = RobotKinematics.GetDhForRobot(name);
            }
            _jointAngles = new double[6];
            ApplyJointLimitsForCurrentRobot();
            PushActiveRobotToInstance();
            if (_currentRobotDef != null)
                ActiveRobotInstance.ApplyDefinition(_currentRobotDef);
            BuildRobot3D();
            SyncScene3D();
            StatusText.Text = _currentRobotDef != null
                ? $"Робот: {_currentRobotDef.DisplayName} (reach {_currentRobotDef.MaxReachMm:F0} mm, {_currentRobotDef.PayloadKg:F0} kg)"
                : $"Робот загружен: {name}";
            AppendOutput(StatusText.Text);
            RefreshProjectTree();
        }

        private (byte R, byte G, byte B) GetRobotBrandColor()
        {
            foreach (var kv in RobotColors)
                if (_currentRobotName.Contains(kv.Key, StringComparison.OrdinalIgnoreCase))
                    return kv.Value;
            return (70, 130, 210);
        }

        private void BuildRobot3D()
        {
            PushActiveRobotToInstance();
            RobotModel.Children.Clear();
            for (int ri = 0; ri < _robotInstances.Count; ri++)
            {
                var inst = _robotInstances[ri];
                var container = new ModelVisual3D();
                BuildRobotVisualInto(container, inst, ri == _activeRobotIndex);
                container.Transform = new TranslateTransform3D(inst.BaseCad.X, -inst.BaseCad.Y, inst.BaseCad.Z);
                RobotModel.Children.Add(container);
                inst.SceneVisual = container;
            }
            SyncJointSlidersFromModel();
            UpdateJogTelemetry();
        }

        private void BuildRobotVisualInto(ModelVisual3D parent, RobotInstance inst, bool isActive)
        {
            var fk = RobotKinematics.FkFull(inst.JointAngles, inst.Dh);
            var links = fk.LinkPositions;
            var brand = inst.BrandColor;
            if (!isActive)
            {
                brand = Color.FromRgb(
                    (byte)(brand.R * 0.55 + 80),
                    (byte)(brand.G * 0.55 + 80),
                    (byte)(brand.B * 0.55 + 80));
            }

            var matBase = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(60, 60, 70)));
            var matJoint = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(
                (byte)Math.Min(255, brand.R + 40),
                (byte)Math.Min(255, brand.G + 40),
                (byte)Math.Min(255, brand.B + 40))));
            var matArm = new DiffuseMaterial(new SolidColorBrush(brand));
            var matTool = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(200, 60, 60)));

            AddCylinder(parent, new Point3D(0, 0, 0), 70, 28, 32, matBase);

            for (int i = 0; i < links.Count; i++)
            {
                var p = links[i];
                var p3 = MapRobotFk(p.X, p.Y, p.Z);
                double jointR = i == 0 ? 36 : (i < links.Count - 1 ? 28 : 18);
                double tubeR = i < links.Count - 1 ? 16 : 11;
                var mat = i == links.Count - 1 ? matTool : matJoint;
                AddSphere(parent, p3, jointR, 24, mat);

                Point3D from = i > 0
                    ? MapRobotFk(links[i - 1].X, links[i - 1].Y, links[i - 1].Z)
                    : new Point3D(0, 0, 28);
                AddTube(parent, from, p3, tubeR, 16, matArm);
            }
        }

        private static void AddCylinder(ModelVisual3D parent, Point3D center, double radius, double height, int segments, Material mat)
        {
            var mesh = new MeshGeometry3D();
            for (int i = 0; i < segments; i++)
            {
                double a = 2 * Math.PI * i / segments;
                double ca = Math.Cos(a), sa = Math.Sin(a);
                mesh.Positions.Add(new Point3D(center.X + radius * ca, center.Y + radius * sa, center.Z));
                mesh.Positions.Add(new Point3D(center.X + radius * ca, center.Y + radius * sa, center.Z + height));
                var n = new Vector3D(ca, sa, 0);
                mesh.Normals.Add(n);
                mesh.Normals.Add(n);
            }
            for (int i = 0; i < segments; i++)
            {
                int b = i * 2, n = ((i + 1) % segments) * 2;
                mesh.TriangleIndices.Add(b); mesh.TriangleIndices.Add(n); mesh.TriangleIndices.Add(n + 1);
                mesh.TriangleIndices.Add(b); mesh.TriangleIndices.Add(n + 1); mesh.TriangleIndices.Add(b + 1);
            }
            int topCenter = mesh.Positions.Count;
            mesh.Positions.Add(new Point3D(center.X, center.Y, center.Z + height));
            mesh.Normals.Add(new Vector3D(0, 0, 1));
            for (int i = 0; i < segments; i++)
            {
                int cur = i * 2 + 1, nxt = ((i + 1) % segments) * 2 + 1;
                mesh.TriangleIndices.Add(topCenter); mesh.TriangleIndices.Add(cur); mesh.TriangleIndices.Add(nxt);
            }
            var model = new GeometryModel3D(mesh, mat) { BackMaterial = mat };
            parent.Children.Add(new ModelVisual3D { Content = model });
        }

        private static void AddSphere(ModelVisual3D parent, Point3D center, double radius, int div, Material mat)
        {
            var mesh = new MeshGeometry3D();
            for (int lat = 0; lat <= div; lat++)
            {
                double theta = Math.PI * lat / div;
                double sinT = Math.Sin(theta), cosT = Math.Cos(theta);
                for (int lon = 0; lon <= div; lon++)
                {
                    double phi = 2 * Math.PI * lon / div;
                    double x = sinT * Math.Cos(phi), y = sinT * Math.Sin(phi), z = cosT;
                    mesh.Positions.Add(new Point3D(center.X + radius * x, center.Y + radius * y, center.Z + radius * z));
                    mesh.Normals.Add(new Vector3D(x, y, z));
                }
            }
            int cols = div + 1;
            for (int lat = 0; lat < div; lat++)
                for (int lon = 0; lon < div; lon++)
                {
                    int a = lat * cols + lon, b = a + cols;
                    mesh.TriangleIndices.Add(a); mesh.TriangleIndices.Add(b); mesh.TriangleIndices.Add(b + 1);
                    mesh.TriangleIndices.Add(a); mesh.TriangleIndices.Add(b + 1); mesh.TriangleIndices.Add(a + 1);
                }
            var model = new GeometryModel3D(mesh, mat) { BackMaterial = mat };
            parent.Children.Add(new ModelVisual3D { Content = model });
        }

        private static void AddTube(ModelVisual3D parent, Point3D from, Point3D to, double radius, int segments, Material mat)
        {
            var dir = new Vector3D(to.X - from.X, to.Y - from.Y, to.Z - from.Z);
            double len = dir.Length;
            if (len < 1e-6) return;
            dir.Normalize();

            var up = Math.Abs(dir.Z) < 0.99 ? new Vector3D(0, 0, 1) : new Vector3D(1, 0, 0);
            var right = Vector3D.CrossProduct(dir, up); right.Normalize();
            var fwd = Vector3D.CrossProduct(right, dir); fwd.Normalize();

            var mesh = new MeshGeometry3D();
            for (int i = 0; i < segments; i++)
            {
                double a = 2 * Math.PI * i / segments;
                double ca = Math.Cos(a), sa = Math.Sin(a);
                var offset = right * (radius * ca) + fwd * (radius * sa);
                var n = right * ca + fwd * sa;
                mesh.Positions.Add(new Point3D(from.X + offset.X, from.Y + offset.Y, from.Z + offset.Z));
                mesh.Positions.Add(new Point3D(to.X + offset.X, to.Y + offset.Y, to.Z + offset.Z));
                mesh.Normals.Add(n); mesh.Normals.Add(n);
            }
            for (int i = 0; i < segments; i++)
            {
                int b = i * 2, nx = ((i + 1) % segments) * 2;
                mesh.TriangleIndices.Add(b); mesh.TriangleIndices.Add(nx); mesh.TriangleIndices.Add(nx + 1);
                mesh.TriangleIndices.Add(b); mesh.TriangleIndices.Add(nx + 1); mesh.TriangleIndices.Add(b + 1);
            }
            var model = new GeometryModel3D(mesh, mat) { BackMaterial = mat };
            parent.Children.Add(new ModelVisual3D { Content = model });
        }

        private double GetDpiScale()
        {
            var src = PresentationSource.FromVisual(this);
            return src?.CompositionTarget?.TransformToDevice.M11 ?? 1.0;
        }

        private SKPoint ScreenToWorld(System.Windows.Point screen)
        {
            double dpi = GetDpiScale();
            return new SKPoint(
                (float)((screen.X * dpi - _panX) / _zoomScale),
                (float)((screen.Y * dpi - _panY) / _zoomScale));
        }

        private void DrawingCanvas_PaintSurface(object? sender, SKPaintSurfaceEventArgs e)
        {
            var canvas = e.Surface.Canvas;
            canvas.Clear(SKColor.Parse("#1E1E1E"));
            canvas.Save();
            canvas.Translate((float)_panX, (float)_panY);
            canvas.Scale((float)_zoomScale, (float)_zoomScale);

            if (_gridVisible)
                DrawGrid(canvas);

            foreach (var entity in _entities)
                entity.Draw(canvas);

            var cmdPreview = _currentCommand.ToUpper();
            bool needPreview = _isDrawing && !string.IsNullOrEmpty(_currentCommand)
                || (cmdPreview == "POLYLINE" && _polylinePoints.Count > 0)
                || ((cmdPreview == "ARC" || cmdPreview == "A") && _arcPoints.Count > 0);
            if (needPreview)
                DrawCurrentObject(canvas);

            DrawCrosshair(canvas, _currentPoint);
            canvas.Restore();
        }

        private void DrawGrid(SKCanvas canvas)
        {
            using var paint = new SKPaint
            {
                Color = SKColor.Parse("#40404040"),
                StrokeWidth = 0.5f,
                IsAntialias = true
            };

            const int gridSize = 50;
            const int majorGridSize = 500;

            // Рисование линий
            for (int x = 0; x < 2000; x += gridSize)
            {
                canvas.DrawLine(x, 0, x, 2000, paint);
            }
            for (int y = 0; y < 2000; y += gridSize)
            {
                canvas.DrawLine(0, y, 2000, y, paint);
            }

            // Рисование линий
            using var majorPaint = new SKPaint
            {
                Color = SKColor.Parse("#64646464"),
                StrokeWidth = 1f,
                IsAntialias = true
            };

            for (int x = 0; x < 2000; x += majorGridSize)
            {
                canvas.DrawLine(x, 0, x, 2000, majorPaint);
            }
            for (int y = 0; y < 2000; y += majorGridSize)
            {
                canvas.DrawLine(0, y, 2000, y, majorPaint);
            }
        }

        private void DrawCrosshair(SKCanvas canvas, SKPoint point)
        {
            using var paint = new SKPaint
            {
                Color = SKColor.Parse("#00FF00"),
                StrokeWidth = 1f,
                IsAntialias = true
            };

            const int crosshairSize = 10;
            
            // Горизонтальные линии
            canvas.DrawLine(point.X - crosshairSize, point.Y, point.X + crosshairSize, point.Y, paint);
            // Вертикальные линии
            canvas.DrawLine(point.X, point.Y - crosshairSize, point.X, point.Y + crosshairSize, paint);
        }

        private void DrawCurrentObject(SKCanvas canvas)
        {
            using var paint = new SKPaint
            {
                Color = SKColor.Parse("#FFFFFFFF"),
                StrokeWidth = 2f,
                IsAntialias = true,
                IsStroke = true
            };

            switch (_currentCommand.ToUpper())
            {
                case "LINE":
                case "L":
                    canvas.DrawLine(_startPoint, _currentPoint, paint);
                    break;
                case "CIRCLE":
                case "C":
                    var radius = SKPoint.Distance(_startPoint, _currentPoint);
                    canvas.DrawCircle(_startPoint, radius, paint);
                    break;
                case "RECTANGLE":
                    DrawRect(canvas, _startPoint, _currentPoint, paint);
                    break;
                case "POLYLINE":
                    for (int i = 0; i < _polylinePoints.Count - 1; i++)
                        canvas.DrawLine(_polylinePoints[i], _polylinePoints[i + 1], paint);
                    if (_polylinePoints.Count > 0)
                        canvas.DrawLine(_polylinePoints[_polylinePoints.Count - 1], _currentPoint, paint);
                    break;
                case "ARC":
                case "A":
                    if (_arcPoints.Count == 1)
                        canvas.DrawLine(_arcPoints[0], _currentPoint, paint);
                    else if (_arcPoints.Count == 2)
                    {
                        var previewArc = ArcEntity.From3Points(_arcPoints[0], _arcPoints[1], _currentPoint, Colors.White, "0");
                        previewArc?.Draw(canvas);
                    }
                    break;
            }
        }

        private static void DrawRect(SKCanvas canvas, SKPoint a, SKPoint b, SKPaint paint)
        {
            float x0 = Math.Min(a.X, b.X), x1 = Math.Max(a.X, b.X);
            float y0 = Math.Min(a.Y, b.Y), y1 = Math.Max(a.Y, b.Y);
            canvas.DrawLine(x0, y0, x1, y0, paint);
            canvas.DrawLine(x1, y0, x1, y1, paint);
            canvas.DrawLine(x1, y1, x0, y1, paint);
            canvas.DrawLine(x0, y1, x0, y0, paint);
        }

        private void DrawingCanvas_MouseDown(object sender, MouseButtonEventArgs e)
        {
            if (e.MiddleButton == MouseButtonState.Pressed)
            {
                _panning = true;
                _panStart = e.GetPosition(DrawingCanvas);
                DrawingCanvas.CaptureMouse();
                return;
            }
            if (e.LeftButton != MouseButtonState.Pressed) return;
            var position = e.GetPosition(DrawingCanvas);
            var point = ScreenToWorld(position);
            if (_snapEnabled) point = SnapToPoint(point);

            var cmd = _currentCommand.ToUpper();
            if (cmd == "PAN")
            {
                _panning = true;
                _panStart = position;
                return;
            }
            if (cmd == "MOVE" || cmd == "COPY")
            {
                if (!_editBaseSet)
                {
                    _editBasePoint = point;
                    _editBaseSet = true;
                    StatusText.Text = cmd == "MOVE" ? "MOVE: укажите базовую точку" : "COPY: укажите базовую точку";
                    return;
                }
                var delta = new SKPoint(point.X - _editBasePoint.X, point.Y - _editBasePoint.Y);
                var selected = _entities.Where(x => x.IsSelected).ToList();
                if (selected.Count == 0) { StatusText.Text = "Выделите объекты (клик по объекту или рамкой)."; _editBaseSet = false; return; }
                if (cmd == "COPY")
                {
                    foreach (var ent in selected)
                    {
                        var copy = CadGeometry.CloneEntity(ent, delta);
                        if (copy != null) _entities.Add(copy);
                    }
                    SaveState();
                    StatusText.Text = "Перемещение завершено";
                }
                else
                {
                    foreach (var ent in selected)
                        CadGeometry.MoveEntity(ent, delta);
                    SaveState();
                    StatusText.Text = "Копирование завершено";
                }
                _editBaseSet = false;
                _currentCommand = "";
                DrawingCanvas.InvalidateVisual();
                return;
            }

            if (string.IsNullOrEmpty(_currentCommand))
            {
                SelectObject(point);
                return;
            }

            if (TryHandleEditCommand(cmd, point))
                return;

            if (cmd == "POLYLINE")
            {
                if (e.ClickCount == 2)
                {
                    if (_polylinePoints.Count >= 2) { FinishPolyline(); return; }
                    if (_polylinePoints.Count == 1) { _polylinePoints.Add(point); FinishPolyline(); return; }
                }
                _polylinePoints.Add(point);
                StatusText.Text = $"Полилиния: точек {_polylinePoints.Count}. Enter для замыкания или продолжайте.";
                DrawingCanvas.InvalidateVisual();
                return;
            }

            if (cmd == "ARC" || cmd == "A")
            {
                _arcPoints.Add(point);
                if (_arcPoints.Count == 1)
                    StatusText.Text = "ARC: укажите промежуточную точку дуги";
                else if (_arcPoints.Count == 2)
                    StatusText.Text = "ARC: укажите конечную точку дуги";
                else if (_arcPoints.Count >= 3)
                {
                    var arc = ArcEntity.From3Points(_arcPoints[0], _arcPoints[1], _arcPoints[2], _currentColor, _currentLayer);
                    if (arc != null)
                    {
                        _entities.Add(arc);
                        SaveState();
                        StatusText.Text = "Дуга создана";
                    }
                    else
                        StatusText.Text = "Не удалось построить дугу (точки на одной прямой)";
                    _arcPoints.Clear();
                    _currentCommand = "";
                }
                DrawingCanvas.InvalidateVisual();
                return;
            }

            _isDrawing = true;
            _startPoint = point;
        }

        private void DrawingCanvas_MouseMove(object sender, MouseEventArgs e)
        {
            var position = e.GetPosition(DrawingCanvas);
            if (_panning)
            {
                double dpi = GetDpiScale();
                _panX += (position.X - _panStart.X) * dpi;
                _panY += (position.Y - _panStart.Y) * dpi;
                _panStart = position;
                DrawingCanvas.InvalidateVisual();
                return;
            }
            var point = ScreenToWorld(position);
            if (_snapEnabled && _isDrawing)
                point = SnapToPoint(point);
            _currentPoint = point;
            CursorInfo.Text = $"X: {point.X:F2} Y: {point.Y:F2}";
            var cmdMv = _currentCommand.ToUpper();
            if (_isDrawing || (cmdMv == "POLYLINE" && _polylinePoints.Count > 0)
                || ((cmdMv == "ARC" || cmdMv == "A") && _arcPoints.Count > 0))
                DrawingCanvas.InvalidateVisual();
        }

        private void DrawingCanvas_MouseUp(object sender, MouseButtonEventArgs e)
        {
            if (_panning) { _panning = false; DrawingCanvas.ReleaseMouseCapture(); return; }
            if (_isDrawing)
            {
                var position = e.GetPosition(DrawingCanvas);
                var endPoint = ScreenToWorld(position);

                if (_snapEnabled)
                {
                    endPoint = SnapToPoint(endPoint);
                }

                var cmd = _currentCommand.ToUpper();
                CadEntity? entity = cmd switch
                {
                    "LINE" or "L" => new LineEntity(_startPoint, endPoint, _currentColor, _currentLayer),
                    "CIRCLE" or "C" => new CircleEntity(_startPoint,
                        SKPoint.Distance(_startPoint, endPoint), _currentColor, _currentLayer),
                    "RECTANGLE" => new RectangleEntity(_startPoint, endPoint, _currentColor, _currentLayer),
                    _ => null
                };

                if (entity != null)
                {
                    _entities.Add(entity);
                    SaveState();
                }

                _isDrawing = false;
                _currentCommand = "";
                DrawingCanvas.InvalidateVisual();
                StatusText.Text = "Прямоугольник";
            }
        }

        private SKPoint SnapToPoint(SKPoint point)
        {
            const int snapGridSize = 25;
            float x = (float)Math.Round(point.X / snapGridSize) * snapGridSize;
            float y = (float)Math.Round(point.Y / snapGridSize) * snapGridSize;
            return new SKPoint(x, y);
        }

        private static CadEntity? CloneEntity(CadEntity ent, SKPoint delta) => CadGeometry.CloneEntity(ent, delta);

        private bool TryHandleEditCommand(string cmd, SKPoint point)
        {
            switch (cmd)
            {
                case "ROTATE":
                {
                    var selected = _entities.Where(x => x.IsSelected).ToList();
                    if (selected.Count == 0) { SelectObject(point); return true; }
                    if (!_editBaseSet)
                    {
                        _editBasePoint = point;
                        _editBaseSet = true;
                        StatusText.Text = "ROTATE: укажите центр поворота";
                        return true;
                    }
                    double angle = Math.Atan2(point.Y - _editBasePoint.Y, point.X - _editBasePoint.X);
                    foreach (var ent in selected)
                        CadGeometry.RotateEntity(ent, _editBasePoint, angle);
                    SaveState();
                    _editBaseSet = false;
                    _currentCommand = "";
                    StatusText.Text = $"Поворот выполнен ({angle * 180 / Math.PI:F1}°)";
                    DrawingCanvas.InvalidateVisual();
                    return true;
                }
                case "SCALE":
                {
                    var selected = _entities.Where(x => x.IsSelected).ToList();
                    if (selected.Count == 0) { SelectObject(point); return true; }
                    if (!_editBaseSet)
                    {
                        _editBasePoint = point;
                        _editBaseSet = true;
                        StatusText.Text = "SCALE: укажите базу масштаба";
                        return true;
                    }
                    double factor = SKPoint.Distance(_editBasePoint, point) / 100.0;
                    if (factor < 0.01) factor = 0.01;
                    foreach (var ent in selected)
                        CadGeometry.ScaleEntity(ent, _editBasePoint, factor);
                    SaveState();
                    _editBaseSet = false;
                    _currentCommand = "";
                    StatusText.Text = $"Масштаб: x{factor:F2}";
                    DrawingCanvas.InvalidateVisual();
                    return true;
                }
                case "MIRROR":
                {
                    var selected = _entities.Where(x => x.IsSelected).ToList();
                    if (selected.Count == 0) { SelectObject(point); return true; }
                    if (!_editBaseSet)
                    {
                        _editBasePoint = point;
                        _editBaseSet = true;
                        StatusText.Text = "MIRROR: укажите первую точку оси";
                        return true;
                    }
                    foreach (var ent in selected)
                        CadGeometry.MirrorEntity(ent, _editBasePoint, point);
                    SaveState();
                    _editBaseSet = false;
                    _currentCommand = "";
                    StatusText.Text = "Зеркало выполнено";
                    DrawingCanvas.InvalidateVisual();
                    return true;
                }
                case "TRIM":
                    if (_editRefEntity == null)
                    {
                        _editRefEntity = HitEntity(point);
                        StatusText.Text = _editRefEntity != null ? "TRIM: выберите объект для обрезки" : "TRIM: граница не найдена";
                        return true;
                    }
                    {
                        var target = HitEntity(point) as LineEntity;
                        if (target != null && CadGeometry.TryTrimLine(target, _editRefEntity, point, out var trimmed) && trimmed != null)
                        {
                            int idx = _entities.IndexOf(target);
                            if (idx >= 0) _entities[idx] = trimmed;
                            SaveState();
                            StatusText.Text = "Обрезка выполнена";
                        }
                        else StatusText.Text = "Обрезка не выполнена";
                    }
                    _editRefEntity = null;
                    _currentCommand = "";
                    DrawingCanvas.InvalidateVisual();
                    return true;
                case "EXTEND":
                    if (_editRefEntity == null)
                    {
                        _editRefEntity = HitEntity(point);
                        StatusText.Text = _editRefEntity != null ? "EXTEND: выберите линию для удлинения" : "EXTEND: граница не найдена";
                        return true;
                    }
                    {
                        var line = HitEntity(point) as LineEntity;
                        if (line != null && CadGeometry.TryExtendLine(line, _editRefEntity, point, out var extended) && extended != null)
                        {
                            int idx = _entities.IndexOf(line);
                            if (idx >= 0) _entities[idx] = extended;
                            SaveState();
                            StatusText.Text = "Удлинение выполнено";
                        }
                        else StatusText.Text = "Удлинение не выполнено";
                    }
                    _editRefEntity = null;
                    _currentCommand = "";
                    DrawingCanvas.InvalidateVisual();
                    return true;
                case "FILLET":
                    if (_editRefEntity == null)
                    {
                        _editRefEntity = HitEntity(point) as LineEntity;
                        StatusText.Text = _editRefEntity != null ? "FILLET: выберите вторую линию" : "FILLET: первая линия";
                        return true;
                    }
                    if (_editRefEntity2 == null)
                    {
                        _editRefEntity2 = HitEntity(point) as LineEntity;
                        if (_editRefEntity2 == null) { StatusText.Text = "FILLET: выберите вторую линию"; return true; }
                        StatusText.Text = "FILLET: укажите радиус (число в командной строке)";
                        return true;
                    }
                    if (_editRefEntity is LineEntity filletLine1 && _editRefEntity2 is LineEntity filletLine2)
                    {
                        float radius = 10f;
                        if (CadGeometry.TryLineIntersectionInfinite(filletLine1, filletLine2, out var corner))
                            radius = Math.Max(1f, SKPoint.Distance(point, corner));
                        var arc = CadGeometry.TryFilletLines(filletLine1, filletLine2, radius);
                        if (arc != null)
                        {
                            _entities.Add(arc);
                            SaveState();
                            StatusText.Text = $"Скругление R={radius:F1}";
                        }
                        else StatusText.Text = "Скругление не выполнено";
                    }
                    _editRefEntity = null;
                    _editRefEntity2 = null;
                    _currentCommand = "";
                    DrawingCanvas.InvalidateVisual();
                    return true;
                case "TEXT":
                {
                    var text = InputDialog.Prompt("Текст", "Введите текст:", "KengaCAD");
                    if (!string.IsNullOrWhiteSpace(text))
                    {
                        _entities.Add(new TextEntity(point, text.Trim(), _currentColor, _currentLayer));
                        SaveState();
                        StatusText.Text = "Текст добавлен";
                    }
                    _currentCommand = "";
                    DrawingCanvas.InvalidateVisual();
                    return true;
                }
                case "DIMLINEAR":
                    _dimPoints.Add(point);
                    if (_dimPoints.Count == 1) StatusText.Text = "DIMLINEAR: вторая точка";
                    else if (_dimPoints.Count == 2) StatusText.Text = "DIMLINEAR: укажите положение размерной линии";
                    else if (_dimPoints.Count >= 3)
                    {
                        _entities.Add(new DimLinearEntity(_dimPoints[0], _dimPoints[1], _dimPoints[2], _currentColor, _currentLayer));
                        SaveState();
                        _dimPoints.Clear();
                        _currentCommand = "";
                        StatusText.Text = "Линейный размер добавлен";
                    }
                    DrawingCanvas.InvalidateVisual();
                    return true;
                case "DIMRADIUS":
                    if (_editRefEntity == null)
                    {
                        _editRefEntity = HitEntity(point);
                        if (_editRefEntity is CircleEntity) StatusText.Text = "DIMRADIUS: укажите положение";
                        else { _editRefEntity = null; StatusText.Text = "DIMRADIUS: выберите окружность"; }
                        return true;
                    }
                    if (_editRefEntity is CircleEntity circle)
                    {
                        _entities.Add(new DimRadiusEntity(circle.Center, circle.Radius, point, _currentColor, _currentLayer));
                        SaveState();
                        StatusText.Text = "Радиальный размер добавлен";
                    }
                    _editRefEntity = null;
                    _currentCommand = "";
                    DrawingCanvas.InvalidateVisual();
                    return true;
                case "INSERTBLOCK":
                    if (_pendingBlockInsert != null)
                    {
                        foreach (var ent in CadGeometry.InstantiateBlock(_pendingBlockInsert, point))
                            _entities.Add(ent);
                        SaveState();
                        StatusText.Text = $"Блок «{_pendingBlockInsert.Name}» вставлен";
                        _pendingBlockInsert = null;
                        _currentCommand = "";
                        DrawingCanvas.InvalidateVisual();
                    }
                    return true;
            }
            return false;
        }

        private CadEntity? HitEntity(SKPoint point)
        {
            for (int i = _entities.Count - 1; i >= 0; i--)
                if (_entities[i].IsHit(point))
                    return _entities[i];
            return null;
        }

        private void SelectObject(SKPoint point)
        {
            // Выделение объектов мышью
            foreach (var entity in _entities)
            {
                if (entity.IsHit(point))
                {
                    entity.IsSelected = !entity.IsSelected;
                    DrawingCanvas.InvalidateVisual();
                    StatusText.Text = entity.IsSelected ? "Объект выделен" : "Объект снят с выделения";
                    return;
                }
            }
        }

        private void SaveState()
        {
            _undoStack.Push(_entities.Select(e => e.Clone()).ToList());
            _redoStack.Clear();
            SyncScene3D();
        }

        private void Window_PreviewKeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Escape)
            {
                _currentCommand = "";
                _editBaseSet = false;
                _editRefEntity = null;
                _editRefEntity2 = null;
                _dimPoints.Clear();
                _pendingBlockInsert = null;
                _polylinePoints.Clear();
                _arcPoints.Clear();
                _isDrawing = false;
                StatusText.Text = "Готово";
                DrawingCanvas?.InvalidateVisual();
                e.Handled = true;
                return;
            }
            if (e.Key != Key.Enter) return;
            if (_currentCommand.ToUpper() == "POLYLINE" && _polylinePoints.Count >= 2)
            {
                FinishPolyline();
                e.Handled = true;
            }
        }

        private void FinishPolyline()
        {
            if (_polylinePoints.Count < 2) return;
            _entities.Add(new PolylineEntity(new List<SKPoint>(_polylinePoints), _currentColor, _currentLayer));
            SaveState();
            _polylinePoints.Clear();
            _currentCommand = "";
            StatusText.Text = "Отменено действие";
            DrawingCanvas.InvalidateVisual();
            CommandLine.Clear();
        }

        private void CommandLine_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter)
            {
                if (_currentCommand.ToUpper() == "POLYLINE" && _polylinePoints.Count >= 2)
                {
                    FinishPolyline();
                    return;
                }
                var command = CommandLine.Text.Trim().ToUpper();
                ProcessCommand(command);
                CommandLine.Clear();
            }
        }

        private void ProcessCommand(string command)
        {
            var parts = command.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            var cmd = parts[0].ToUpper();

            switch (cmd)
            {
                case "LINE":
                case "L":
                    _currentCommand = "LINE";
                    StatusText.Text = "LINE: укажите вторую точку";
                    break;
                case "CIRCLE":
                case "C":
                    _currentCommand = "CIRCLE";
                    StatusText.Text = "CIRCLE: укажите точку на окружности";
                    break;
                case "POLYLINE":
                case "PL":
                    _currentCommand = "POLYLINE";
                    StatusText.Text = "POLYLINE: укажите следующую точку";
                    break;
                case "RECTANGLE":
                case "REC":
                    _currentCommand = "RECTANGLE";
                    StatusText.Text = "RECTANGLE: укажите противоположный угол";
                    break;
                case "MOVE":
                case "M":
                    _currentCommand = "MOVE";
                    _editBaseSet = false;
                    StatusText.Text = "MOVE: укажите точку назначения";
                    break;
                case "COPY":
                case "CO":
                    _currentCommand = "COPY";
                    _editBaseSet = false;
                    StatusText.Text = "COPY: укажите точку назначения";
                    break;
                case "UNDO":
                case "U":
                    Undo();
                    break;
                case "REDO":
                case "R":
                    Redo();
                    break;
                case "ZOOM":
                case "Z":
                    if (parts.Length > 1 && parts[1] == "E")
                    {
                        ZoomExtents();
                    }
                    break;
                case "ORTHO":
                    _orthoMode = !_orthoMode;
                    OrthoStatus.Text = _orthoMode ? "ВКЛ" : "ВЫКЛ";
                    OrthoStatus.Foreground = _orthoMode 
                        ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#4CAF50"))
                        : new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F44336"));
                    StatusText.Text = $"ORTHO: {(_orthoMode ? "ВКЛ" : "ВЫКЛ")}";
                    break;
                case "SNAP":
                    _snapEnabled = !_snapEnabled;
                    SnapStatus.Text = _snapEnabled ? "ВКЛ" : "ВЫКЛ";
                    SnapStatus.Foreground = _snapEnabled
                        ? new SolidColorBrush((Color)ColorConverter.ConvertFromString("#4CAF50"))
                        : new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F44336"));
                    StatusText.Text = $"SNAP: {(_snapEnabled ? "ВКЛ" : "ВЫКЛ")}";
                    break;
                case "HELP":
                case "?":
                    ShowHelp();
                    break;
                default:
                    StatusText.Text = $"Неизвестная команда: {cmd}";
                    break;
            }
        }

        private void Undo()
        {
            if (_undoStack.Count > 0)
            {
                _redoStack.Push(_entities.Select(e => e.Clone()).ToList());
                _entities.Clear();
                _entities.AddRange(_undoStack.Pop());
                DrawingCanvas.InvalidateVisual();
                SyncScene3D();
                StatusText.Text = "Повторено";
            }
        }

        private void Redo()
        {
            if (_redoStack.Count > 0)
            {
                _undoStack.Push(_entities.Select(e => e.Clone()).ToList());
                _entities.Clear();
                _entities.AddRange(_redoStack.Pop());
                DrawingCanvas.InvalidateVisual();
                SyncScene3D();
                StatusText.Text = "Отменено";
            }
        }

        private void ZoomExtents()
        {
            double minX = 0, minY = 0, maxX = 2000, maxY = 2000;
            foreach (var e in _entities)
            {
                if (e is LineEntity l) { minX = Math.Min(minX, Math.Min(l.Start.X, l.End.X)); maxX = Math.Max(maxX, Math.Max(l.Start.X, l.End.X)); minY = Math.Min(minY, Math.Min(l.Start.Y, l.End.Y)); maxY = Math.Max(maxY, Math.Max(l.Start.Y, l.End.Y)); }
                else if (e is CircleEntity c) { minX = Math.Min(minX, c.Center.X - c.Radius); maxX = Math.Max(maxX, c.Center.X + c.Radius); minY = Math.Min(minY, c.Center.Y - c.Radius); maxY = Math.Max(maxY, c.Center.Y + c.Radius); }
                else if (e is RectangleEntity r) { minX = Math.Min(minX, r.X0); maxX = Math.Max(maxX, r.X1); minY = Math.Min(minY, r.Y0); maxY = Math.Max(maxY, r.Y1); }
                else if (e is PolylineEntity pl) foreach (var p in pl.Points) { minX = Math.Min(minX, p.X); maxX = Math.Max(maxX, p.X); minY = Math.Min(minY, p.Y); maxY = Math.Max(maxY, p.Y); }
            }
            double w = maxX - minX, h = maxY - minY;
            if (w < 50) w = 50;
            if (h < 50) h = 50;
            double cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
            var host = DrawingCanvas?.Parent as System.Windows.FrameworkElement;
            double dpi = GetDpiScale();
            double viewW = (host?.ActualWidth ?? 800) * dpi, viewH = (host?.ActualHeight ?? 600) * dpi;
            _zoomScale = Math.Min(viewW / w, viewH / h) * 0.9;
            _panX = viewW / 2 - cx * _zoomScale;
            _panY = viewH / 2 - cy * _zoomScale;
            DrawingCanvas?.InvalidateVisual();
            StatusText.Text = "ZOOM: показать всё";
        }

        private void ZoomIn()
        {
            _zoomScale *= 1.25;
            if (_zoomScale > 50) _zoomScale = 50;
            DrawingCanvas?.InvalidateVisual();
        }

        private void ZoomOut()
        {
            _zoomScale /= 1.25;
            if (_zoomScale < 0.05) _zoomScale = 0.05;
            DrawingCanvas?.InvalidateVisual();
        }

        private void DrawingCanvas_MouseWheel(object sender, MouseWheelEventArgs e)
        {
            var pos = e.GetPosition(DrawingCanvas);
            double dpi = GetDpiScale();
            double mx = pos.X * dpi, my = pos.Y * dpi;
            double oldZoom = _zoomScale;
            if (e.Delta > 0)
                _zoomScale *= 1.15;
            else
                _zoomScale /= 1.15;
            _zoomScale = Math.Clamp(_zoomScale, 0.05, 50);
            _panX = mx - (mx - _panX) * (_zoomScale / oldZoom);
            _panY = my - (my - _panY) * (_zoomScale / oldZoom);
            DrawingCanvas?.InvalidateVisual();
            e.Handled = true;
        }

        private void StartSimulation()
        {
            if (_currentCommand.ToUpper() == "POLYLINE" && _polylinePoints.Count >= 2)
                FinishPolyline();
            var pts = GetActiveTrajectory();
            if (pts.Count == 0)
            {
                StatusText.Text = "Нет траектории. Добавьте точки, полилинию или программу.";
                return;
            }
            StopSimulation();
            _simTrajectory = pts;
            BuildExecutionFrames();
            if (_execFrames.Count == 0)
            {
                StatusText.Text = "Не удалось построить траекторию симуляции.";
                AppendOutput(StatusText.Text);
                return;
            }
            BuildTrajectory3D();
            _simIndex = 0;
            _execIndex = 0;
            _simTimer = new DispatcherTimer(DispatcherPriority.Normal)
            {
                Interval = TimeSpan.FromMilliseconds(50)
            };
            _simTimer.Tick += SimTimer_Tick;
            _simTimer.Start();
            UpdateTrajectoryBlink();
            StatusText.Text = "Симуляция: воспроизведение в 3D";
            AppendOutput(StatusText.Text);
        }

        private void BuildExecutionFrames()
        {
            _execFrames.Clear();
            var ops = _programOperations.Count > 0 ? _programOperations.ToList() : BuildDefaultOperations();
            if (ops.Count == 0) return;

            var currentJoints = _jointAngles.ToArray();
            var currentFk = RobotKinematics.FkFull(currentJoints, _currentDh);
            var currentWorld = ToWorldTcp(currentFk.TcpPos);

            foreach (var op in ops)
            {
                string t = op.Type?.Trim().ToUpperInvariant() ?? "MOVEL";
                if (t == "WAIT")
                {
                    int frames = Math.Max(1, (int)(op.WaitMs / 50.0));
                    for (int i = 0; i < frames; i++)
                    {
                        _execFrames.Add(new ExecutionFrame
                        {
                            Joints = currentJoints.ToArray(),
                            WaypointIndex = null,
                            EventMessage = i == 0 ? $"WAIT {op.WaitMs:F0} ms" : null
                        });
                    }
                    continue;
                }
                if (t == "IO")
                {
                    _execFrames.Add(new ExecutionFrame
                    {
                        Joints = currentJoints.ToArray(),
                        WaypointIndex = null,
                        EventMessage = $"IO {op.IoChannel}={(op.IoValue ? 1 : 0)}"
                    });
                    continue;
                }
                if (!TryGetWaypoint(op.WaypointIndex, out var wp))
                    continue;

                if (t == "MOVEJ")
                {
                    var robotTargetJ = ToRobotTcp((wp.X, wp.Y, wp.Z));
                    if (!SolveIkPosition(robotTargetJ, out var targetJoints, currentJoints))
                        continue;
                    double maxDiff = 0;
                    for (int j = 0; j < RobotKinematics.NumJoints; j++)
                        maxDiff = Math.Max(maxDiff, Math.Abs(targetJoints[j] - currentJoints[j]));
                    int steps = Math.Max(2, (int)Math.Ceiling(maxDiff / Math.Max(0.5, op.Speed / 15.0)));
                    for (int i = 1; i <= steps; i++)
                    {
                        double tStep = (double)i / steps;
                        var q = new double[RobotKinematics.NumJoints];
                        for (int j = 0; j < RobotKinematics.NumJoints; j++)
                            q[j] = currentJoints[j] + (targetJoints[j] - currentJoints[j]) * tStep;
                        _execFrames.Add(new ExecutionFrame
                        {
                            Joints = q,
                            WaypointIndex = wp.Index - 1,
                            EventMessage = i == 1 ? $"MOVEJ P{wp.Index:000}" : null
                        });
                    }
                    currentJoints = targetJoints.ToArray();
                    currentWorld = (wp.X, wp.Y, wp.Z);
                    continue;
                }

                var targetWorld = (wp.X, wp.Y, wp.Z);
                double dist = Distance3(currentWorld, targetWorld);
                double segmentLen = Math.Max(1.0, op.Speed / 20.0);
                int moveSteps = Math.Max(2, (int)Math.Ceiling(dist / segmentLen));
                var seed = currentJoints.ToArray();
                for (int i = 1; i <= moveSteps; i++)
                {
                    double k = (double)i / moveSteps;
                    var p = (
                        currentWorld.X + (targetWorld.X - currentWorld.X) * k,
                        currentWorld.Y + (targetWorld.Y - currentWorld.Y) * k,
                        currentWorld.Z + (targetWorld.Z - currentWorld.Z) * k);
                    var robotTarget = ToRobotTcp(p);
                    if (!SolveIkPosition(robotTarget, out var solved, seed))
                        break;
                    seed = solved.ToArray();
                    _execFrames.Add(new ExecutionFrame
                    {
                        Joints = solved,
                        WaypointIndex = wp.Index - 1,
                        EventMessage = i == 1 ? $"MOVEL P{wp.Index:000}" : null
                    });
                }
                currentJoints = seed.ToArray();
                currentWorld = targetWorld;
            }
        }

        private List<ProgramOperation> BuildDefaultOperations()
        {
            var list = new List<ProgramOperation>();
            foreach (var wp in _programWaypoints)
            {
                list.Add(new ProgramOperation
                {
                    Index = list.Count + 1,
                    Type = "MoveL",
                    WaypointIndex = wp.Index,
                    Speed = wp.Speed,
                    Accel = wp.Accel,
                    WaitMs = 0,
                    IoChannel = "",
                    IoValue = false
                });
            }
            return list;
        }

        private bool TryGetWaypoint(int waypointIndex, out ProgramWaypoint wp)
        {
            wp = new ProgramWaypoint();
            if (waypointIndex < 1 || waypointIndex > _programWaypoints.Count) return false;
            wp = _programWaypoints[waypointIndex - 1];
            return true;
        }

        private (double X, double Y, double Z) ToWorldTcp((double X, double Y, double Z) robotTcp)
        {
            var b = SelectedBaseOffset;
            var t = SelectedToolOffset;
            return (
                robotTcp.X + b.X + t.X + _robotBaseCad.X,
                robotTcp.Y + b.Y + t.Y + _robotBaseCad.Y,
                robotTcp.Z + b.Z + t.Z + _robotBaseCad.Z);
        }

        private (double X, double Y, double Z) ToRobotTcp((double X, double Y, double Z) worldTcp)
        {
            var b = SelectedBaseOffset;
            var t = SelectedToolOffset;
            return (
                worldTcp.X - b.X - t.X - _robotBaseCad.X,
                worldTcp.Y - b.Y - t.Y - _robotBaseCad.Y,
                worldTcp.Z - b.Z - t.Z - _robotBaseCad.Z);
        }

        private static double Distance3((double X, double Y, double Z) a, (double X, double Y, double Z) b)
        {
            double dx = a.X - b.X;
            double dy = a.Y - b.Y;
            double dz = a.Z - b.Z;
            return Math.Sqrt(dx * dx + dy * dy + dz * dz);
        }

        private void PauseSimulation()
        {
            _simTimer?.Stop();
            StatusText.Text = "Симуляция на паузе";
            AppendOutput(StatusText.Text);
        }

        private void StopSimulation()
        {
            _simTimer?.Stop();
            _simTimer = null;
            _execFrames.Clear();
            _execIndex = 0;
            StatusText.Text = "Симуляция остановлена";
            AppendOutput(StatusText.Text);
        }

        private void ResetSimulation()
        {
            StopSimulation();
            TrajectoryContainer.Children.Clear();
            _trajectoryVisuals.Clear();
            _simTrajectory.Clear();
            StatusText.Text = "3D симуляция сброшена";
            AppendOutput(StatusText.Text);
        }

        private void SimTimer_Tick(object? sender, EventArgs e)
        {
            if (_execFrames.Count == 0) return;

            if (_execIndex >= _execFrames.Count)
            {
                bool cyclicMode = ProgramRunModeComboBox.SelectedIndex == 1;
                if (cyclicMode)
                    _execIndex = 0;
                else
                {
                    StopSimulation();
                    AppendOutput("Выполнение программы завершено.");
                    return;
                }
            }

            var frame = _execFrames[_execIndex];
            _jointAngles = frame.Joints.ToArray();
            BuildRobot3D();
            SyncScene3D();
            UpdateJogTelemetry();

            if (frame.WaypointIndex.HasValue)
            {
                _selectedWaypointIndex = frame.WaypointIndex.Value;
                WaypointsGrid.SelectedIndex = _selectedWaypointIndex;
                _simIndex = Math.Clamp(_selectedWaypointIndex, 0, Math.Max(0, _simTrajectory.Count - 1));
            }
            if (!string.IsNullOrWhiteSpace(frame.EventMessage))
            {
                AppendOutput(frame.EventMessage);
                if (frame.EventMessage.StartsWith("IO ", StringComparison.Ordinal))
                    ApplyIoEvent(frame.EventMessage);
            }

            _execIndex++;
            UpdateTrajectoryBlink();
        }

        private void BuildTrajectory3D()
        {
            TrajectoryContainer.Children.Clear();
            _trajectoryVisuals.Clear();
            double r = 8.0;
            foreach (var pt in _simTrajectory)
            {
                var mesh = CreateCubeMesh(r);
                var mat = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(80, 80, 80)));
                var model = new GeometryModel3D(mesh, mat);
                var p3 = CadToScene3D(pt.X, pt.Y, pt.Z);
                model.Transform = new TranslateTransform3D(p3.X, p3.Y, p3.Z);
                var vis = new ModelVisual3D { Content = model };
                TrajectoryContainer.Children.Add(vis);
                _trajectoryVisuals.Add(vis);
            }
        }

        private static MeshGeometry3D CreateCubeMesh(double halfSize)
        {
            var g = new MeshGeometry3D();
            double s = halfSize;
            g.Positions.Add(new Point3D(-s, -s, -s));
            g.Positions.Add(new Point3D(s, -s, -s));
            g.Positions.Add(new Point3D(s, s, -s));
            g.Positions.Add(new Point3D(-s, s, -s));
            g.Positions.Add(new Point3D(-s, -s, s));
            g.Positions.Add(new Point3D(s, -s, s));
            g.Positions.Add(new Point3D(s, s, s));
            g.Positions.Add(new Point3D(-s, s, s));
            void Tri(int a, int b, int c) { g.TriangleIndices.Add(a); g.TriangleIndices.Add(b); g.TriangleIndices.Add(c); }
            Tri(0, 1, 2); Tri(0, 2, 3); Tri(4, 6, 5); Tri(4, 7, 6);
            Tri(0, 4, 5); Tri(0, 5, 1); Tri(1, 5, 6); Tri(1, 6, 2);
            Tri(2, 6, 7); Tri(2, 7, 3); Tri(3, 7, 4); Tri(3, 4, 0);
            return g;
        }

        private void UpdateTrajectoryBlink()
        {
            for (int i = 0; i < _trajectoryVisuals.Count; i++)
            {
                if (_trajectoryVisuals[i].Content is not GeometryModel3D model) continue;
                bool highlight = (i == _simIndex);
                model.Material = new DiffuseMaterial(new SolidColorBrush(
                    highlight ? Color.FromRgb(0, 200, 100) : Color.FromRgb(70, 70, 70)));
            }
        }

        private void ShowHelp()
        {
            var helpText = @"KengaCAD v2.1.0 - Справка

Основные команды:
  LINE (L)     - линия
  CIRCLE (C)   - окружность
  ARC (A)      - дуга
  RECTANGLE    - прямоугольник
  POLYLINE     - полилиния

Редактирование:
  MOVE (M)     - перемещение
  COPY (CO)    - копирование
  ROTATE (RO)  - поворот
  SCALE (SC)   - масштаб
  TRIM (TR)    - обрезка
  UNDO (U)     - отменить
  REDO (R)     - повторить

Навигация:
  ZOOM (Z)     - масштаб
  ZOOM (E)     - показать всё
  ORTHO (F8)   - ортогональный режим
  SNAP         - привязки

Нажмите ESC для отмены команды";

            MessageBox.Show(helpText, "KengaCAD - Справка",
                MessageBoxButton.OK, MessageBoxImage.Information);
        }

        // Обработчики Ribbon
        private void NewCommand_Executed(object sender, ExecutedRoutedEventArgs e)
        {
            _entities.Clear();
            _blocks.Clear();
            _undoStack.Clear();
            _redoStack.Clear();
            _currentDrawingPath = null;
            DrawingCanvas.InvalidateVisual();
            SyncScene3D();
            StatusText.Text = "Новый чертёж создан";
        }

        private void OpenCommand_Executed(object sender, ExecutedRoutedEventArgs e)
        {
            var dlg = new OpenFileDialog
            {
                Filter = "KengaCAD (*.kengacad)|*.kengacad|DXF (*.dxf)|*.dxf|DWG (*.dwg)|*.dwg|All (*.*)|*.*"
            };
            if (dlg.ShowDialog() != true) return;
            try
            {
                var ext = System.IO.Path.GetExtension(dlg.FileName).ToLowerInvariant();
                List<CadEntity> loaded;
                List<CadBlockDefinition> blocks;
                if (ext == ".dwg")
                {
                    var converted = ExternalCadConverter.TryConvertToDxf(dlg.FileName);
                    if (converted == null)
                    {
                        MessageBox.Show(
                            "DWG: укажите путь к ODA File Converter в config/settings.json (cad.oda_converter_path) или экспортируйте чертёж в DXF.",
                            "KengaCAD", MessageBoxButton.OK, MessageBoxImage.Information);
                        return;
                    }
                    loaded = CadDocumentIO.ImportDxf(converted);
                    blocks = new List<CadBlockDefinition>();
                }
                else if (ext == ".dxf")
                {
                    loaded = CadDocumentIO.ImportDxf(dlg.FileName);
                    blocks = new List<CadBlockDefinition>();
                }
                else
                {
                    (loaded, blocks) = CadDocumentIO.LoadNative(dlg.FileName);
                }
                _entities.Clear();
                _entities.AddRange(loaded);
                _blocks.Clear();
                _blocks.AddRange(blocks);
                _undoStack.Clear();
                _redoStack.Clear();
                _currentDrawingPath = dlg.FileName;
                DrawingCanvas.InvalidateVisual();
                SyncScene3D();
                ZoomExtents();
                StatusText.Text = $"Открыто: {dlg.FileName} ({loaded.Count} объектов)";
                AppendOutput(StatusText.Text);
            }
            catch (Exception ex)
            {
                StatusText.Text = $"Ошибка открытия: {ex.Message}";
                AppendOutput(StatusText.Text);
            }
        }

        private void SaveCommand_Executed(object sender, ExecutedRoutedEventArgs e)
        {
            if (string.IsNullOrEmpty(_currentDrawingPath))
            {
                var dlg = new SaveFileDialog
                {
                    Filter = "KengaCAD (*.kengacad)|*.kengacad|DXF (*.dxf)|*.dxf|All (*.*)|*.*",
                    FileName = "drawing.kengacad"
                };
                if (dlg.ShowDialog() != true) return;
                _currentDrawingPath = dlg.FileName;
            }
            try
            {
                var ext = System.IO.Path.GetExtension(_currentDrawingPath).ToLowerInvariant();
                if (ext == ".dxf")
                    CadDocumentIO.ExportDxf(_currentDrawingPath, _entities);
                else
                    CadDocumentIO.SaveNative(_currentDrawingPath, _entities, _blocks);
                StatusText.Text = $"Сохранено: {_currentDrawingPath}";
                AppendOutput(StatusText.Text);
            }
            catch (Exception ex)
            {
                StatusText.Text = $"Ошибка сохранения: {ex.Message}";
                AppendOutput(StatusText.Text);
            }
        }

        private void UndoCommand_Executed(object sender, ExecutedRoutedEventArgs e) => Undo();
        private void RedoCommand_Executed(object sender, ExecutedRoutedEventArgs e) => Redo();

        // Навигация камеры 3D сцены
        // ===================== CAMERA & NAVIGATION =====================

        private void UpdateCamera()
        {
            double yawR = _camYaw * Math.PI / 180;
            double pitchR = _camPitch * Math.PI / 180;
            double x = _camDist * Math.Cos(pitchR) * Math.Cos(yawR);
            double y = _camDist * Math.Cos(pitchR) * Math.Sin(yawR);
            double z = _camDist * Math.Sin(pitchR);
            var pos = new Point3D(_camTarget.X + x, _camTarget.Y + y, _camTarget.Z + z);
            var look = new Vector3D(_camTarget.X - pos.X, _camTarget.Y - pos.Y, _camTarget.Z - pos.Z);
            MainCamera.Position = pos;
            MainCamera.LookDirection = look;
            MainCamera.UpDirection = new Vector3D(0, 0, 1);
        }

        private void ViewIso_Click(object sender, RoutedEventArgs e)
        {
            _camYaw = -45; _camPitch = 22; _camDist = 1650; _camTarget = new Point3D(450, -450, 280);
            UpdateCamera();
        }

        private void ViewTop_Click(object sender, RoutedEventArgs e)
        {
            _camYaw = 0; _camPitch = 89.5; _camDist = 2200; _camTarget = new Point3D(500, -500, 0);
            UpdateCamera();
        }

        private void ViewFront_Click(object sender, RoutedEventArgs e)
        {
            _camYaw = -90; _camPitch = 8; _camDist = 1650; _camTarget = new Point3D(450, -450, 280);
            UpdateCamera();
        }

        private void ViewLeft_Click(object sender, RoutedEventArgs e)
        {
            _camYaw = 180; _camPitch = 8; _camDist = 1650; _camTarget = new Point3D(450, -450, 280);
            UpdateCamera();
        }

        private void ResetView_Click(object sender, RoutedEventArgs e) => ViewIso_Click(sender, e);

        private void ThreeDOnlyCheckBox_Checked(object sender, RoutedEventArgs e) => Apply3DOnlyMode(true);
        private void ThreeDOnlyCheckBox_Unchecked(object sender, RoutedEventArgs e) => Apply3DOnlyMode(false);

        private void Apply3DOnlyMode(bool only3D)
        {
            DrawingCanvasHost.Visibility = only3D ? Visibility.Collapsed : Visibility.Visible;
            DrawingColumnDefinition.Width = only3D ? new GridLength(0) : new GridLength(1, GridUnitType.Star);
            SceneColumnDefinition.Width = only3D ? new GridLength(1, GridUnitType.Star) : new GridLength(460);
            StatusText.Text = only3D ? "Режим только 3D включён" : "Режим только 3D выключен";
            AppendOutput(StatusText.Text);
        }

        private void ResetRobotBase_Click(object sender, RoutedEventArgs e)
        {
            _robotBaseCad = (0, 0, 0);
            BuildRobot3D();
            SyncScene3D();
            UpdateJogTelemetry();
            StatusText.Text = "База робота сброшена в 0,0,0";
            AppendOutput(StatusText.Text);
        }

        // ===================== 3D MOUSE INTERACTION =====================

        private void Viewport3D_MouseWheel(object sender, MouseWheelEventArgs e)
        {
            _camDist *= e.Delta > 0 ? 0.9 : 1.1;
            _camDist = Math.Clamp(_camDist, 50, 5000);
            UpdateCamera();
        }

        private void Viewport3D_MouseRightButtonDown(object sender, MouseButtonEventArgs e)
        {
            _orbiting = true;
            _orbitStart = e.GetPosition(ViewportBorder);
            ViewportBorder.CaptureMouse();
        }

        private void Viewport3D_MouseRightButtonUp(object sender, MouseButtonEventArgs e)
        {
            _orbiting = false;
            if (!_draggingRobotBase)
                ViewportBorder.ReleaseMouseCapture();
        }

        private void Viewport3D_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            var pos = e.GetPosition(ViewportBorder);
            if (!TryGetGroundPointFromScreen(pos, out var groundScene))
                return;

            if (e.ClickCount >= 2)
            {
                AddWaypointFromScenePoint(groundScene);
                return;
            }

            _draggingRobotBase = true;
            ViewportBorder.CaptureMouse();
            MoveRobotBaseCad(groundScene.X, -groundScene.Y, log: true);
        }

        private void Viewport3D_MouseLeftButtonUp(object sender, MouseButtonEventArgs e)
        {
            _draggingRobotBase = false;
            if (!_orbiting)
                ViewportBorder.ReleaseMouseCapture();
        }

        private void Viewport3D_MouseMove(object sender, MouseEventArgs e)
        {
            var pos = e.GetPosition(ViewportBorder);
            if (_draggingRobotBase && e.LeftButton == MouseButtonState.Pressed)
            {
                if (TryGetGroundPointFromScreen(pos, out var groundScene))
                {
                    MoveRobotBaseCad(groundScene.X, -groundScene.Y, log: false);
                }
                return;
            }
            if (!_orbiting) return;
            double dx = pos.X - _orbitStart.X;
            double dy = pos.Y - _orbitStart.Y;
            if (e.MiddleButton == MouseButtonState.Pressed || Keyboard.IsKeyDown(Key.LeftShift))
            {
                double yawR = _camYaw * Math.PI / 180;
                _camTarget.X -= (dx * Math.Sin(yawR) + dy * Math.Cos(yawR)) * 0.5;
                _camTarget.Y += (dx * Math.Cos(yawR) - dy * Math.Sin(yawR)) * 0.5;
            }
            else
            {
                _camYaw -= dx * 0.3;
                _camPitch += dy * 0.3;
                _camPitch = Math.Clamp(_camPitch, -89, 89);
            }
            _orbitStart = pos;
            UpdateCamera();
        }

        private bool TryGetGroundPointFromScreen(System.Windows.Point screen, out Point3D groundPoint)
        {
            groundPoint = new Point3D();
            double width = ViewportBorder.ActualWidth;
            double height = ViewportBorder.ActualHeight;
            if (width < 1 || height < 1) return false;

            var cam = MainCamera;
            var origin = cam.Position;
            var forward = cam.LookDirection;
            if (forward.Length < 1e-9) return false;
            forward.Normalize();
            var up = cam.UpDirection;
            up.Normalize();
            var right = Vector3D.CrossProduct(forward, up);
            if (right.Length < 1e-9) return false;
            right.Normalize();
            up = Vector3D.CrossProduct(right, forward);
            up.Normalize();

            double nx = (2.0 * screen.X / width) - 1.0;
            double ny = 1.0 - (2.0 * screen.Y / height);
            double aspect = width / height;
            double tan = Math.Tan(cam.FieldOfView * Math.PI / 360.0);
            var dir = forward + right * (nx * tan * aspect) + up * (ny * tan);
            dir.Normalize();

            if (Math.Abs(dir.Z) < 1e-9) return false;
            double t = -origin.Z / dir.Z;
            if (t < 0) return false;
            groundPoint = new Point3D(
                origin.X + dir.X * t,
                origin.Y + dir.Y * t,
                0);
            return true;
        }

        private void AddWaypointFromScenePoint(Point3D groundScene)
        {
            var fk = RobotKinematics.FkFull(_jointAngles, _currentDh);
            AddWaypointFromPose(
                groundScene.X,
                -groundScene.Y,
                0,
                fk.TcpRpyDeg.Rx,
                fk.TcpRpyDeg.Ry,
                fk.TcpRpyDeg.Rz);
            AppendOutput("Точка добавлена на 3D сцене (double-click).");
        }

        private void MoveRobotBaseCad(double cadX, double cadY, bool log)
        {
            _robotBaseCad = (cadX, cadY, 0);
            BuildRobot3D();
            SyncScene3D();
            UpdateJogTelemetry();
            if (log)
            {
                StatusText.Text = $"База робота: X={cadX:F1} Y={cadY:F1}";
                AppendOutput(StatusText.Text);
            }
        }

        private void ApplyIoEvent(string message)
        {
            // "IO DO1=1"
            var parts = message.Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2) return;
            var kv = parts[1].Split('=');
            if (kv.Length < 2) return;
            string channel = kv[0];
            bool val = kv[1] == "1";
            var sig = _ioSignals.FirstOrDefault(s => s.Name == channel);
            if (sig != null)
            {
                sig.Value = val;
                IoSignalsGrid.Items.Refresh();
                if (_opcUaClient.IsConnected && !string.IsNullOrWhiteSpace(sig.OpcNodeId) && sig.Type is "DO" or "AO")
                    _opcUaClient.WriteBool(sig.OpcNodeId, val);
            }
        }

        private void AddWorkcellObject(WorkcellType type)
        {
            double bx = _robotBaseCad.X + 500;
            double by = _robotBaseCad.Y;
            WorkcellObject obj = type switch
            {
                WorkcellType.Table => WorkcellObject.CreateTable(bx, by),
                WorkcellType.Fixture => WorkcellObject.CreateFixture(bx + 100, by + 100),
                WorkcellType.Fence => WorkcellObject.CreateFence(bx - 600, by),
                WorkcellType.Conveyor => WorkcellObject.CreateConveyor(bx, by - 400),
                _ => WorkcellObject.CreateTable(bx, by)
            };
            obj.Name = $"{obj.Name} {_workcellObjects.Count + 1}";
            _workcellObjects.Add(obj);
            RebuildWorkcell3D();
            RefreshProjectTree();
            AppendOutput($"Workcell: добавлен {obj.Name}");
            StatusText.Text = $"Workcell: {obj.Name}";
        }

        private void ClearWorkcell()
        {
            _workcellObjects.Clear();
            WorkcellModel3D.Children.Clear();
            RefreshProjectTree();
            AppendOutput("Workcell очищен.");
        }

        private void RebuildWorkcell3D()
        {
            WorkcellModel3D.Children.Clear();
            foreach (var obj in _workcellObjects.Where(o => o.Visible && o.Type != WorkcellType.ImportedMesh))
            {
                var mesh = CreateBoxMesh(obj.SizeX, obj.SizeY, obj.SizeZ);
                var mat = new DiffuseMaterial(new SolidColorBrush(obj.Color));
                var model = new GeometryModel3D(mesh, mat) { BackMaterial = mat };
                var visual = new ModelVisual3D { Content = model };
                visual.Transform = new TranslateTransform3D(
                    obj.X - obj.SizeX * 0.5,
                    -(obj.Y + obj.SizeY * 0.5),
                    obj.Z);
                WorkcellModel3D.Children.Add(visual);
            }
        }

        private static MeshGeometry3D CreateBoxMesh(double sx, double sy, double sz)
        {
            double hx = sx * 0.5, hy = sy * 0.5;
            var mesh = new MeshGeometry3D();
            void Face(Point3D a, Point3D b, Point3D c, Point3D d)
            {
                int i = mesh.Positions.Count;
                mesh.Positions.Add(a); mesh.Positions.Add(b); mesh.Positions.Add(c); mesh.Positions.Add(d);
                mesh.TriangleIndices.Add(i); mesh.TriangleIndices.Add(i + 1); mesh.TriangleIndices.Add(i + 2);
                mesh.TriangleIndices.Add(i); mesh.TriangleIndices.Add(i + 2); mesh.TriangleIndices.Add(i + 3);
            }
            Face(new(hx, hy, sz), new(-hx, hy, sz), new(-hx, -hy, sz), new(hx, -hy, sz));
            Face(new(hx, hy, 0), new(hx, -hy, 0), new(-hx, -hy, 0), new(-hx, hy, 0));
            Face(new(hx, hy, 0), new(hx, hy, sz), new(hx, -hy, sz), new(hx, -hy, 0));
            Face(new(-hx, hy, 0), new(-hx, -hy, 0), new(-hx, -hy, sz), new(-hx, hy, sz));
            Face(new(hx, hy, 0), new(-hx, hy, 0), new(-hx, hy, sz), new(hx, hy, sz));
            Face(new(hx, -hy, 0), new(hx, -hy, sz), new(-hx, -hy, sz), new(-hx, -hy, 0));
            return mesh;
        }

        private void RunCollisionCheck()
        {
            var trajectory = GetTrajectoryPointsForCollision();
            var hits = CollisionDetector.CheckTrajectoryVsObstacles(trajectory, _workcellObjects);
            var fk = RobotKinematics.FkFull(_jointAngles, _currentDh);
            var links = fk.LinkPositions.Select(p => (p.X + _robotBaseCad.X, p.Y + _robotBaseCad.Y, p.Z)).ToList();
            hits.AddRange(CollisionDetector.CheckRobotVsObstacles(links, _workcellObjects));
            if (hits.Count == 0)
            {
                StatusText.Text = "Коллизии: не обнаружены";
                AppendOutput(StatusText.Text);
                return;
            }
            StatusText.Text = $"Коллизии: {hits.Count} точек";
            AppendOutput(StatusText.Text);
            foreach (var h in hits.Take(10))
                AppendOutput($"  шаг {h.Step}: {h.ObjectA} ↔ {h.ObjectB} ({h.Point.X:F0},{h.Point.Y:F0},{h.Point.Z:F0})");
            if (hits.Count > 10)
                AppendOutput($"  ... ещё {hits.Count - 10}");
        }

        private void RunSelfCollisionCheck()
        {
            var fk = RobotKinematics.FkFull(_jointAngles, _currentDh);
            var links = fk.LinkPositions;
            var hits = CollisionDetector.CheckRobotSelfCollision(links);
            if (hits.Count == 0)
            {
                StatusText.Text = "Самоколлизия: не обнаружена";
                AppendOutput(StatusText.Text);
                return;
            }
            StatusText.Text = $"Самоколлизия: {hits.Count} пар звеньев";
            AppendOutput(StatusText.Text);
            foreach (var h in hits)
                AppendOutput($"  {h.ObjectA} ↔ {h.ObjectB}");
        }

        private void ShowCycleTime()
        {
            UpdateCycleTimeDisplay();
            StatusText.Text = $"Время цикла: {CycleTimeText.Text}";
            AppendOutput(StatusText.Text);
        }

        private List<(double X, double Y, double Z)> GetTrajectoryPointsForCollision()
        {
            if (_programWaypoints.Count > 0)
                return _programWaypoints.Select(w => (w.X, w.Y, w.Z)).ToList();
            return GetActiveTrajectory().Select(p => (p.X, p.Y, p.Z)).ToList();
        }

        // ===================== GRID FLOOR =====================

        private void BuildGridFloor()
        {
            GridFloor3D.Children.Clear();
            double extent = 1400;
            double step = 50;
            var matMinor = new DiffuseMaterial(new SolidColorBrush(Color.FromArgb(60, 100, 100, 120)));
            var matMajor = new DiffuseMaterial(new SolidColorBrush(Color.FromArgb(100, 120, 120, 150)));
            var matAxisX = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(200, 50, 50)));
            var matAxisY = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(50, 200, 50)));

            for (double v = -extent; v <= extent; v += step)
            {
                bool major = Math.Abs(v % 200) < 1;
                var mat = Math.Abs(v) < 1 ? matAxisY : (major ? matMajor : matMinor);
                double thick = Math.Abs(v) < 1 ? 2 : (major ? 1 : 0.5);
                AddFlatLine(GridFloor3D, new Point3D(v, -extent, 0), new Point3D(v, extent, 0), thick, mat);

                mat = Math.Abs(v) < 1 ? matAxisX : (major ? matMajor : matMinor);
                AddFlatLine(GridFloor3D, new Point3D(-extent, v, 0), new Point3D(extent, v, 0), thick, mat);
            }
        }

        private static void AddFlatLine(ModelVisual3D parent, Point3D from, Point3D to, double width, Material mat)
        {
            var dir = new Vector3D(to.X - from.X, to.Y - from.Y, 0);
            dir.Normalize();
            var perp = new Vector3D(-dir.Y, dir.X, 0);
            double hw = width * 0.5;
            var mesh = new MeshGeometry3D();
            mesh.Positions.Add(new Point3D(from.X + perp.X * hw, from.Y + perp.Y * hw, 0));
            mesh.Positions.Add(new Point3D(from.X - perp.X * hw, from.Y - perp.Y * hw, 0));
            mesh.Positions.Add(new Point3D(to.X - perp.X * hw, to.Y - perp.Y * hw, 0));
            mesh.Positions.Add(new Point3D(to.X + perp.X * hw, to.Y + perp.Y * hw, 0));
            mesh.Normals.Add(new Vector3D(0, 0, 1));
            mesh.Normals.Add(new Vector3D(0, 0, 1));
            mesh.Normals.Add(new Vector3D(0, 0, 1));
            mesh.Normals.Add(new Vector3D(0, 0, 1));
            mesh.TriangleIndices.Add(0); mesh.TriangleIndices.Add(1); mesh.TriangleIndices.Add(2);
            mesh.TriangleIndices.Add(0); mesh.TriangleIndices.Add(2); mesh.TriangleIndices.Add(3);
            var model = new GeometryModel3D(mesh, mat) { BackMaterial = mat };
            parent.Children.Add(new ModelVisual3D { Content = model });
        }

        private void SyncScene3D()
        {
            DrawingOverlay3D.Children.Clear();
            var matLine = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(0, 255, 100)));
            var matCircle = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(100, 200, 255)));
            var matArc = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(255, 200, 50)));
            var matRect = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(255, 100, 100)));
            var matPoly = new DiffuseMaterial(new SolidColorBrush(Color.FromRgb(200, 100, 255)));
            double zw = 0.5;
            double lineW = 2;

            foreach (var ent in _entities)
            {
                if (ent is LineEntity line)
                {
                    AddTube(DrawingOverlay3D,
                        CadToScene3D(line.Start.X, line.Start.Y, zw),
                        CadToScene3D(line.End.X, line.End.Y, zw), lineW, 6, matLine);
                }
                else if (ent is CircleEntity circle)
                {
                    int segs = 48;
                    for (int i = 0; i < segs; i++)
                    {
                        double a1 = 2 * Math.PI * i / segs;
                        double a2 = 2 * Math.PI * (i + 1) / segs;
                        float x1 = circle.Center.X + circle.Radius * (float)Math.Cos(a1);
                        float y1 = circle.Center.Y + circle.Radius * (float)Math.Sin(a1);
                        float x2 = circle.Center.X + circle.Radius * (float)Math.Cos(a2);
                        float y2 = circle.Center.Y + circle.Radius * (float)Math.Sin(a2);
                        AddTube(DrawingOverlay3D, CadToScene3D(x1, y1, zw), CadToScene3D(x2, y2, zw), lineW, 4, matCircle);
                    }
                }
                else if (ent is ArcEntity arc)
                {
                    int segs = 32;
                    for (int i = 0; i < segs; i++)
                    {
                        double d1 = arc.StartAngle + arc.SweepAngle * i / segs;
                        double d2 = arc.StartAngle + arc.SweepAngle * (i + 1) / segs;
                        double r1 = d1 * Math.PI / 180;
                        double r2 = d2 * Math.PI / 180;
                        float x1 = arc.Center.X + arc.Radius * (float)Math.Cos(r1);
                        float y1 = arc.Center.Y + arc.Radius * (float)Math.Sin(r1);
                        float x2 = arc.Center.X + arc.Radius * (float)Math.Cos(r2);
                        float y2 = arc.Center.Y + arc.Radius * (float)Math.Sin(r2);
                        AddTube(DrawingOverlay3D, CadToScene3D(x1, y1, zw), CadToScene3D(x2, y2, zw), lineW, 4, matArc);
                    }
                }
                else if (ent is RectangleEntity rect)
                {
                    AddTube(DrawingOverlay3D, CadToScene3D(rect.X0, rect.Y0, zw), CadToScene3D(rect.X1, rect.Y0, zw), lineW, 4, matRect);
                    AddTube(DrawingOverlay3D, CadToScene3D(rect.X1, rect.Y0, zw), CadToScene3D(rect.X1, rect.Y1, zw), lineW, 4, matRect);
                    AddTube(DrawingOverlay3D, CadToScene3D(rect.X1, rect.Y1, zw), CadToScene3D(rect.X0, rect.Y1, zw), lineW, 4, matRect);
                    AddTube(DrawingOverlay3D, CadToScene3D(rect.X0, rect.Y1, zw), CadToScene3D(rect.X0, rect.Y0, zw), lineW, 4, matRect);
                }
                else if (ent is PolylineEntity pl && pl.Points.Count >= 2)
                {
                    for (int i = 0; i < pl.Points.Count - 1; i++)
                    {
                        AddTube(DrawingOverlay3D,
                            CadToScene3D(pl.Points[i].X, pl.Points[i].Y, zw),
                            CadToScene3D(pl.Points[i + 1].X, pl.Points[i + 1].Y, zw),
                            lineW, 4, matPoly);
                    }
                }
            }
        }
    }

    public class ExecutionFrame
    {
        public double[] Joints { get; set; } = new double[RobotKinematics.NumJoints];
        public int? WaypointIndex { get; set; }
        public string? EventMessage { get; set; }
    }
}
