using Microsoft.Maui.Storage;

namespace KengaCAD.Mobile;

public static class MobileConfig
{
    public static async Task EnsureAsync()
    {
        var target = Path.Combine(FileSystem.AppDataDirectory, "config");
        var robotsFile = Path.Combine(target, "robots.json");
        if (!File.Exists(robotsFile))
        {
            Directory.CreateDirectory(target);
            Directory.CreateDirectory(Path.Combine(target, "templates"));
            await CopyAssetAsync("config/robots.json", robotsFile);
            await CopyAssetAsync("config/postprocessors.json", Path.Combine(target, "postprocessors.json"));
            await CopyAssetAsync("config/settings.json", Path.Combine(target, "settings.json"));
            foreach (var tpl in new[] { "kuka_krl.sbn", "abb_rapid.sbn", "fanuc_tp.sbn", "ur_script.sbn", "yaskawa_inform.sbn" })
                await CopyAssetAsync($"config/templates/{tpl}", Path.Combine(target, "templates", tpl));
        }

        AppPaths.ConfigRootOverride = target;
        RobotLibrary.Reload();
    }

    private static async Task CopyAssetAsync(string assetName, string destPath)
    {
        try
        {
            using var stream = await FileSystem.OpenAppPackageFileAsync(assetName);
            using var outStream = File.Create(destPath);
            await stream.CopyToAsync(outStream);
        }
        catch
        {
            // asset optional
        }
    }
}
