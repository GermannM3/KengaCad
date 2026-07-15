using System.Collections.ObjectModel;
using KengaCAD;

namespace KengaCAD.Mobile;

public partial class ConnectionPage : ContentPage
{
    public static string StorePath => Path.Combine(FileSystem.AppDataDirectory, "robot_links.json");

    private UrDashboardClient? _ur;
    private readonly ObservableCollection<ProfileRow> _rows = new();

    public ConnectionPage()
    {
        InitializeComponent();
        ProtocolPicker.ItemsSource = Enum.GetNames(typeof(RobotLinkProtocol)).ToList();
        ProtocolPicker.SelectedIndex = 0;
        BrandPicker.ItemsSource = RobotLinkPresets.All.Select(p => p.Brand).ToList();
        BrandPicker.SelectedIndex = 0;
        ProfilesList.ItemsSource = _rows;
        Loaded += (_, _) => ReloadProfiles();
    }

    private void OnBrandChanged(object? sender, EventArgs e)
    {
        if (BrandPicker.SelectedIndex < 0) return;
        var preset = RobotLinkPresets.All[BrandPicker.SelectedIndex];
        HintLabel.Text = preset.Hint;
        PortEntry.Text = preset.Port.ToString();
        ProtocolPicker.SelectedItem = preset.Protocol.ToString();
    }

    private RobotLinkProfile BuildProfile()
    {
        _ = int.TryParse(PortEntry.Text, out var port);
        var protoName = ProtocolPicker.SelectedItem?.ToString() ?? nameof(RobotLinkProtocol.FtpUpload);
        Enum.TryParse<RobotLinkProtocol>(protoName, out var proto);
        return new RobotLinkProfile
        {
            Name = BrandPicker.SelectedItem?.ToString() ?? "Robot",
            Brand = BrandPicker.SelectedItem?.ToString() ?? "Generic",
            Host = HostEntry.Text?.Trim() ?? "",
            Port = port > 0 ? port : 21,
            Protocol = proto,
            Username = UserEntry.Text ?? "anonymous",
            Password = PassEntry.Text ?? "",
            RemoteDirectory = string.IsNullOrWhiteSpace(RemoteDirEntry.Text) ? "/" : RemoteDirEntry.Text!.Trim()
        };
    }

    private async void OnProbe(object? sender, EventArgs e)
    {
        var p = BuildProfile();
        StatusLabel.Text = $"Проверка {p.Host}:{p.Port}…";
        var (ok, msg) = await RobotLinkProbe.ProbeAsync(p.Host, p.Port);
        StatusLabel.Text = msg;
        await DisplayAlert(ok ? "Связь есть" : "Нет связи", msg, "OK");
    }

    private async void OnSave(object? sender, EventArgs e)
    {
        var p = BuildProfile();
        if (string.IsNullOrWhiteSpace(p.Host))
        {
            await DisplayAlert("Профиль", "Укажите IP контроллера.", "OK");
            return;
        }
        var list = RobotLinkStore.Load(StorePath);
        list.RemoveAll(x => x.Host == p.Host && x.Port == p.Port);
        list.Insert(0, p);
        RobotLinkStore.Save(list, StorePath);
        ReloadProfiles();
        StatusLabel.Text = $"Сохранено: {p.Brand} {p.Host}:{p.Port}";
    }

    private void ReloadProfiles()
    {
        _rows.Clear();
        foreach (var p in RobotLinkStore.Load(StorePath))
            _rows.Add(new ProfileRow { Summary = $"{p.Brand}  {p.Host}:{p.Port}  [{p.Protocol}]" });
    }

    private async void OnUrConnect(object? sender, EventArgs e)
    {
        var p = BuildProfile();
        _ur ??= new UrDashboardClient();
        StatusLabel.Text = "UR Dashboard…";
        var ok = await _ur.ConnectAsync(p.Host, p.Port > 0 ? p.Port : 29999);
        StatusLabel.Text = ok ? "UR подключен" : $"UR ошибка: {_ur.LastError}";
        if (!ok) await DisplayAlert("UR", StatusLabel.Text, "OK");
    }

    private async void OnUrMode(object? sender, EventArgs e) => await UrCmd(c => c.RobotModeAsync());
    private async void OnUrPlay(object? sender, EventArgs e)
    {
        var confirm = await DisplayAlert("Безопасность", "Запустить программу на роботе? Убедитесь, что зона безопасна.", "Play", "Отмена");
        if (!confirm) return;
        await UrCmd(c => c.PlayAsync());
    }
    private async void OnUrStop(object? sender, EventArgs e) => await UrCmd(c => c.StopAsync());

    private async Task UrCmd(Func<UrDashboardClient, Task<string>> fn)
    {
        if (_ur is not { IsConnected: true })
        {
            await DisplayAlert("UR", "Сначала Connect UR.", "OK");
            return;
        }
        try
        {
            var r = await fn(_ur);
            StatusLabel.Text = r;
        }
        catch (Exception ex)
        {
            StatusLabel.Text = ex.Message;
        }
    }

    private sealed class ProfileRow
    {
        public string Summary { get; set; } = "";
    }
}
