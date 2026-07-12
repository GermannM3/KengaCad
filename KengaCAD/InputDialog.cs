using System.Windows;
using System.Windows.Controls;

namespace KengaCAD
{
    public static class InputDialog
    {
        public static string? Prompt(string title, string prompt, string defaultValue = "")
        {
            var w = new Window
            {
                Title = title,
                Width = 420,
                Height = 160,
                WindowStartupLocation = WindowStartupLocation.CenterOwner,
                ResizeMode = ResizeMode.NoResize,
                Background = System.Windows.Media.Brushes.White
            };
            var grid = new Grid { Margin = new Thickness(16) };
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            grid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            var label = new TextBlock { Text = prompt, Margin = new Thickness(0, 0, 0, 8) };
            var box = new TextBox { Text = defaultValue, Margin = new Thickness(0, 0, 0, 12) };
            var panel = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = HorizontalAlignment.Right };
            var ok = new Button { Content = "OK", Width = 80, Margin = new Thickness(0, 0, 8, 0), IsDefault = true };
            var cancel = new Button { Content = "Отмена", Width = 80, IsCancel = true };
            ok.Click += (_, __) => { w.DialogResult = true; w.Close(); };
            panel.Children.Add(ok);
            panel.Children.Add(cancel);
            Grid.SetRow(label, 0);
            Grid.SetRow(box, 1);
            Grid.SetRow(panel, 2);
            grid.Children.Add(label);
            grid.Children.Add(box);
            grid.Children.Add(panel);
            w.Content = grid;
            if (Application.Current.MainWindow != null && Application.Current.MainWindow != w)
                w.Owner = Application.Current.MainWindow;
            return w.ShowDialog() == true ? box.Text : null;
        }
    }
}
