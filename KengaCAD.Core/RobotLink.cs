using System.Net.Sockets;
using System.Text;
using System.Text.Json;

namespace KengaCAD;

/// <summary>Профиль подключения к контроллеру робота в цехе (LAN / Wi‑Fi).</summary>
public sealed class RobotLinkProfile
{
    public string Name { get; set; } = "Robot";
    public string Brand { get; set; } = "Generic";
    public string Host { get; set; } = "192.168.1.10";
    public int Port { get; set; } = 21;
    public RobotLinkProtocol Protocol { get; set; } = RobotLinkProtocol.FtpUpload;
    public string Username { get; set; } = "anonymous";
    public string Password { get; set; } = "";
    public string RemoteDirectory { get; set; } = "/";
}

public enum RobotLinkProtocol
{
    /// <summary>Загрузка программы на контроллер по FTP (KUKA/ABB/Fanuc часто).</summary>
    FtpUpload = 0,
    /// <summary>Проверка TCP-порта / сырая отправка байт.</summary>
    TcpRaw = 1,
    /// <summary>Universal Robots Dashboard Server (порт 29999).</summary>
    UrDashboard = 2
}

public static class RobotLinkPresets
{
    public static IReadOnlyList<(string Brand, RobotLinkProtocol Protocol, int Port, string Hint)> All { get; } =
    [
        ("KUKA", RobotLinkProtocol.FtpUpload, 21, "FTP: каталог KRC:/R1/Program или /"),
        ("ABB", RobotLinkProtocol.FtpUpload, 21, "FTP: HOME или RAPID — .mod/.sys"),
        ("Fanuc", RobotLinkProtocol.FtpUpload, 21, "FTP: MD: или UD1: для .TP"),
        ("Yaskawa", RobotLinkProtocol.FtpUpload, 21, "FTP / MotoFTP — файл INFORM"),
        ("UR", RobotLinkProtocol.UrDashboard, 29999, "Dashboard: load / play / stop на UR"),
        ("Generic TCP", RobotLinkProtocol.TcpRaw, 30001, "Сырой TCP (шлюз, PLC, свой протокол)"),
        ("OPC UA (desktop)", RobotLinkProtocol.TcpRaw, 4840, "OPC UA — полноценно в Windows-версии")
    ];
}

/// <summary>Краткая проверка доступности хоста:порт в цеховой сети.</summary>
public static class RobotLinkProbe
{
    public static async Task<(bool Ok, string Message)> ProbeAsync(string host, int port, int timeoutMs = 3000, CancellationToken ct = default)
    {
        if (string.IsNullOrWhiteSpace(host))
            return (false, "Не указан IP / hostname");
        try
        {
            using var client = new TcpClient();
            using var reg = ct.Register(() => { try { client.Close(); } catch { /* ignore */ } });
            var connectTask = client.ConnectAsync(host.Trim(), port);
            var done = await Task.WhenAny(connectTask, Task.Delay(timeoutMs, ct)).ConfigureAwait(false);
            if (done != connectTask)
                return (false, $"Таймаут {timeoutMs} мс — {host}:{port}");
            await connectTask.ConfigureAwait(false);
            return (true, $"Открыт {host}:{port}");
        }
        catch (Exception ex)
        {
            return (false, $"{host}:{port} — {ex.Message}");
        }
    }
}

/// <summary>FTP-загрузка программы на контроллер (самый частый способ в цехе).</summary>
public static class FtpProgramUploader
{
    public static async Task<(bool Ok, string Message)> UploadAsync(
        RobotLinkProfile profile,
        string localFilePath,
        CancellationToken ct = default)
    {
        if (!File.Exists(localFilePath))
            return (false, "Локальный файл не найден");
        if (string.IsNullOrWhiteSpace(profile.Host))
            return (false, "Не указан Host");

        var fileName = Path.GetFileName(localFilePath);
        var remoteDir = (profile.RemoteDirectory ?? "/").TrimEnd('/');
        if (string.IsNullOrEmpty(remoteDir)) remoteDir = "/";
        var remotePath = remoteDir == "/" ? $"/{fileName}" : $"{remoteDir}/{fileName}";

        try
        {
            var user = string.IsNullOrEmpty(profile.Username) ? "anonymous" : profile.Username;
            var pass = profile.Password ?? "";
            var uri = new Uri($"ftp://{profile.Host}:{profile.Port}{remotePath}");

            var request = (System.Net.FtpWebRequest)System.Net.WebRequest.Create(uri);
            request.Method = System.Net.WebRequestMethods.Ftp.UploadFile;
            request.Credentials = new System.Net.NetworkCredential(user, pass);
            request.UseBinary = true;
            request.UsePassive = true;
            request.KeepAlive = false;
            request.Timeout = 15000;
            request.ReadWriteTimeout = 15000;

            await using (var fileStream = File.OpenRead(localFilePath))
            await using (var requestStream = await request.GetRequestStreamAsync().ConfigureAwait(false))
            {
                await fileStream.CopyToAsync(requestStream, ct).ConfigureAwait(false);
            }

            using var response = (System.Net.FtpWebResponse)await request.GetResponseAsync().ConfigureAwait(false);
            return (true, $"FTP OK: {remotePath} ({response.StatusDescription?.Trim()})");
        }
        catch (Exception ex)
        {
            return (false, $"FTP ошибка: {ex.Message}");
        }
    }
}

/// <summary>Universal Robots Dashboard Server (TCP 29999) — load/play без полного Primary Interface.</summary>
public sealed class UrDashboardClient : IAsyncDisposable
{
    private TcpClient? _client;
    private StreamReader? _reader;
    private StreamWriter? _writer;

    public bool IsConnected => _client?.Connected == true;
    public string? LastError { get; private set; }

    public async Task<bool> ConnectAsync(string host, int port = 29999, CancellationToken ct = default)
    {
        LastError = null;
        try
        {
            await DisposeAsync().ConfigureAwait(false);
            _client = new TcpClient();
            using var reg = ct.Register(() => { try { _client?.Close(); } catch { /* ignore */ } });
            await _client.ConnectAsync(host.Trim(), port).ConfigureAwait(false);
            var stream = _client.GetStream();
            _reader = new StreamReader(stream, Encoding.UTF8, false, 1024, leaveOpen: true);
            _writer = new StreamWriter(stream, Encoding.UTF8, 1024, leaveOpen: true) { AutoFlush = true, NewLine = "\n" };
            // Welcome line
            _ = await ReadLineAsync(ct).ConfigureAwait(false);
            return true;
        }
        catch (Exception ex)
        {
            LastError = ex.Message;
            return false;
        }
    }

    public async Task<string> SendAsync(string command, CancellationToken ct = default)
    {
        if (_writer == null || _reader == null)
            throw new InvalidOperationException("Не подключено к UR Dashboard");
        await _writer.WriteLineAsync(command).ConfigureAwait(false);
        var line = await ReadLineAsync(ct).ConfigureAwait(false);
        return line ?? "";
    }

    public Task<string> RobotModeAsync(CancellationToken ct = default) => SendAsync("robotmode", ct);
    public Task<string> LoadAsync(string programName, CancellationToken ct = default) => SendAsync($"load {programName}", ct);
    public Task<string> PlayAsync(CancellationToken ct = default) => SendAsync("play", ct);
    public Task<string> StopAsync(CancellationToken ct = default) => SendAsync("stop", ct);
    public Task<string> GetLoadedProgramAsync(CancellationToken ct = default) => SendAsync("get loaded program", ct);

    private async Task<string?> ReadLineAsync(CancellationToken ct)
    {
        if (_reader == null) return null;
        return await _reader.ReadLineAsync(ct).ConfigureAwait(false);
    }

    public async ValueTask DisposeAsync()
    {
        try { _writer?.Dispose(); } catch { /* ignore */ }
        try { _reader?.Dispose(); } catch { /* ignore */ }
        if (_client != null)
        {
            try { _client.Close(); } catch { /* ignore */ }
            _client.Dispose();
        }
        _writer = null;
        _reader = null;
        _client = null;
        await Task.CompletedTask;
    }
}

/// <summary>Простой TCP-клиент: проверка и отправка текста (шлюзы, PLC-скрипты).</summary>
public static class TcpRawClient
{
    public static async Task<(bool Ok, string Response)> SendAsync(
        string host, int port, string payload, int timeoutMs = 5000, CancellationToken ct = default)
    {
        try
        {
            using var client = new TcpClient();
            using var reg = ct.Register(() => { try { client.Close(); } catch { /* ignore */ } });
            await client.ConnectAsync(host.Trim(), port).ConfigureAwait(false);
            await using var stream = client.GetStream();
            stream.ReadTimeout = timeoutMs;
            stream.WriteTimeout = timeoutMs;
            var bytes = Encoding.UTF8.GetBytes(payload);
            await stream.WriteAsync(bytes, ct).ConfigureAwait(false);
            var buffer = new byte[4096];
            using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
            cts.CancelAfter(timeoutMs);
            int read;
            try
            {
                read = await stream.ReadAsync(buffer.AsMemory(0, buffer.Length), cts.Token).ConfigureAwait(false);
            }
            catch (OperationCanceledException)
            {
                return (true, "(отправлено, ответ не получен)");
            }
            return (true, Encoding.UTF8.GetString(buffer, 0, read));
        }
        catch (Exception ex)
        {
            return (false, ex.Message);
        }
    }
}

/// <summary>Локальное хранение профилей подключения на устройстве.</summary>
public static class RobotLinkStore
{
    public static string DefaultPath =>
        Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "KengaCAD", "robot_links.json");

    public static List<RobotLinkProfile> Load(string? path = null)
    {
        path ??= DefaultPath;
        try
        {
            if (!File.Exists(path)) return new List<RobotLinkProfile>();
            var json = File.ReadAllText(path);
            return JsonSerializer.Deserialize<List<RobotLinkProfile>>(json) ?? new List<RobotLinkProfile>();
        }
        catch
        {
            return new List<RobotLinkProfile>();
        }
    }

    public static void Save(IEnumerable<RobotLinkProfile> profiles, string? path = null)
    {
        path ??= DefaultPath;
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var json = JsonSerializer.Serialize(profiles.ToList(), new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(path, json);
    }
}
