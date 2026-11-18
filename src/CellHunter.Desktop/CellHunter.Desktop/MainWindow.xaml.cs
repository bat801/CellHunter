using System;
using System.IO;
using System.Windows;
using CellHunter.Desktop.Services;
using CellHunter.Desktop.ViewModels;

namespace CellHunter.Desktop
{
    public partial class MainWindow : Window
    {
        public MainWindow()
        {
            InitializeComponent();

            var bridge = new PythonBridge();
            var viewModel = new MainViewModel(bridge);
            ApplyCommandLine(viewModel);
            DataContext = viewModel;
        }

        /// <summary>
        /// Supports <c>--folder &lt;path&gt;</c> to preselect the analysis folder,
        /// which is handy for shortcuts and automated screenshots.
        /// </summary>
        private static void ApplyCommandLine(MainViewModel viewModel)
        {
            var args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++)
            {
                if (string.Equals(args[i], "--folder", StringComparison.OrdinalIgnoreCase)
                    && Directory.Exists(args[i + 1]))
                {
                    viewModel.SelectedFolder = Path.GetFullPath(args[i + 1]);
                    return;
                }
            }
        }
    }
}
