using System;
using System.IO;
using System.Windows;
using System.Windows.Threading;

namespace KengaCAD
{
    public partial class App : Application
    {
        private static void WriteCrashLog(Exception ex)
        {
            try
            {
                var dir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "KengaCAD");
                Directory.CreateDirectory(dir);
                var path = Path.Combine(dir, "crash_log.txt");
                File.WriteAllText(path, $"{DateTime.UtcNow:o}\r\n{ex}\r\n");
            }
            catch { /* ignore */ }
        }

        private void Application_Startup(object sender, StartupEventArgs e)
        {
            AppDomain.CurrentDomain.UnhandledException += (s, args) =>
            {
                if (args.ExceptionObject is Exception ex)
                    WriteCrashLog(ex);
            };
            DispatcherUnhandledException += (s, args) =>
            {
                WriteCrashLog(args.Exception);
                MessageBox.Show(
                    "Произошла ошибка:\n" + args.Exception.Message + "\n\nПриложение будет закрыто.",
                    "KengaCAD - Ошибка",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
                args.Handled = true;
                Shutdown(1);
            };
            try
            {
                var main = new MainWindow();
                main.Show();
            }
            catch (Exception ex)
            {
                WriteCrashLog(ex);
                MessageBox.Show(
                    "Ошибка загрузки окна:\n" + ex.Message + "\n\nПодробности: " + Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData) + "\\KengaCAD\\crash_log.txt",
                    "KengaCAD - Ошибка",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
                Shutdown(1);
            }
        }
    }
}
