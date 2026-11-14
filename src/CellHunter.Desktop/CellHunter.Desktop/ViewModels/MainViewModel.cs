using System;
using System.Collections.ObjectModel;
using System.Windows.Input;
using CellHunter.Desktop.Models;
using CellHunter.Desktop.Services;
using CellHunter.Desktop.Utils;
using Ookii.Dialogs.Wpf;

namespace CellHunter.Desktop.ViewModels
{
    public class MainViewModel : ObservableObject
    {
        private readonly IPythonBridge _pythonBridge;
        private string _selectedFolder = string.Empty;
        private string _logMessages = string.Empty;
        private double _progressValue;
        private bool _isAnalyzing;
        private ObservableCollection<ImageAnalysisResult> _results = new();
        private string _selectedModel = "cellpose";
        private readonly List<string> _availableModels = new() { "cellpose", "yolo" };

        public List<string> AvailableModels => _availableModels;

        public string SelectedFolder
        {
            get => _selectedFolder;
            set => SetProperty(ref _selectedFolder, value);
        }

        public string SelectedModel
        {
            get => _selectedModel;
            set => SetProperty(ref _selectedModel, value);
        }

        public string LogMessages
        {
            get => _logMessages;
            set => SetProperty(ref _logMessages, value);
        }

        public double ProgressValue
        {
            get => _progressValue;
            set => SetProperty(ref _progressValue, value);
        }

        public bool IsAnalyzing
        {
            get => _isAnalyzing;
            set => SetProperty(ref _isAnalyzing, value);
        }

        public ObservableCollection<ImageAnalysisResult> Results
        {
            get => _results;
            set => SetProperty(ref _results, value);
        }

        public ICommand SelectFolderCommand { get; }
        public ICommand StartAnalysisCommand { get; }
        public ICommand CancelAnalysisCommand { get; }
        public ICommand ExportReportCommand { get; }

        public MainViewModel(IPythonBridge pythonBridge)
        {
            _pythonBridge = pythonBridge;

            SelectFolderCommand = new RelayCommand(ExecuteSelectFolder);
            StartAnalysisCommand = new RelayCommand(ExecuteStartAnalysis, CanExecuteStartAnalysis);
            CancelAnalysisCommand = new RelayCommand(ExecuteCancelAnalysis, CanExecuteCancelAnalysis);
            ExportReportCommand = new RelayCommand(ExecuteExportReport, CanExecuteExportReport);

            // Подписка на события PythonBridge
            _pythonBridge.ProgressMessage += OnProgressMessage;
            _pythonBridge.AnalysisCompleted += OnAnalysisCompleted;
        }

        private void OnProgressMessage(object? sender, string message)
        {
            App.Current.Dispatcher.Invoke(() =>
            {
                LogMessages += $"{DateTime.Now:HH:mm:ss} {message}\n";
                ParseProgress(message);
            });
        }

        private void OnAnalysisCompleted(object? sender, AnalysisSummary summary)
        {
            App.Current.Dispatcher.Invoke(() =>
            {
                IsAnalyzing = false;
                ProgressValue = 100;

                if (summary.Status == "success" && summary.Results != null)
                {
                    Results.Clear();
                    foreach (var result in summary.Results)
                    {
                        Results.Add(result);
                    }

                    // Теперь метаданные должны правильно парситься
                    LogMessages += $"\n📁 Отчет: {summary.ExcelPath}\n";
                    LogMessages += $"📊 Обработано: {summary.ProcessedFiles}/{summary.TotalFiles} файлов\n";
                    LogMessages += $"⏱️ Время: {summary.TotalTimeSeconds:F1} сек.\n";
                }
                else if (summary.Status != "success")
                {
                    LogMessages += $"\n❌ Ошибка анализа: {summary.Status}\n";
                }
            });
        }

        private void ParseProgress(string message)
        {
            // Ожидаемый формат: PROGRESS:<текущий>/<всего>:<имя файла>
            const string prefix = "PROGRESS:";
            int prefixIndex = message.IndexOf(prefix, StringComparison.Ordinal);
            if (prefixIndex < 0) return;

            string payload = message.Substring(prefixIndex + prefix.Length);
            string[] parts = payload.Split(':', 2);
            string[] numbers = parts[0].Split('/');

            if (numbers.Length != 2) return;
            if (!int.TryParse(numbers[0], out int current)) return;
            if (!int.TryParse(numbers[1], out int total) || total <= 0) return;

            ProgressValue = Math.Clamp((double)current / total * 100.0, 0.0, 100.0);
        }

        private void ExecuteSelectFolder()
        {
            var dialog = new VistaFolderBrowserDialog();
            dialog.Description = "Выберите папку с изображениями для анализа";
            dialog.ShowNewFolderButton = false;

            if (dialog.ShowDialog() == true)
            {
                SelectedFolder = dialog.SelectedPath;
            }
        }

        private bool CanExecuteStartAnalysis() => !IsAnalyzing && !string.IsNullOrEmpty(SelectedFolder);

        private async void ExecuteStartAnalysis()
        {
            if (string.IsNullOrEmpty(SelectedFolder)) return;

            LogMessages = string.Empty;
            Results.Clear();
            ProgressValue = 0;
            IsAnalyzing = true;

            try
            {
                // Передаем выбранную модель
                await _pythonBridge.RunAnalysisAsync(SelectedFolder, SelectedModel);
            }
            finally
            {
                // Сбрасываем состояние и при ошибке/отмене, иначе кнопка «Запуск» останется заблокированной
                IsAnalyzing = false;
            }
        }

        private bool CanExecuteCancelAnalysis() => IsAnalyzing;

        private void ExecuteCancelAnalysis()
        {
            _pythonBridge.CancelAnalysis();
            IsAnalyzing = false;
            LogMessages += "\n⏹️ Анализ отменен\n";
        }

        private bool CanExecuteExportReport() => Results.Count > 0;

        private void ExecuteExportReport()
        {
            LogMessages += "\n📊 Экспорт отчета... (функция в разработке)\n";
        }
    }
}