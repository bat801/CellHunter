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
            DataContext = new MainViewModel(bridge);
        }
    }
}