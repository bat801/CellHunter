using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using CellHunter.Desktop.Models;

namespace CellHunter.Desktop.Services
{
    public class PythonBridge : IPythonBridge, IDisposable
    {
        private Process? _currentProcess;
        private CancellationTokenSource? _cts;
        private bool _isRunning;

        private bool _collectingJson = false;
        private string _jsonBuffer = "";

        public event EventHandler<string>? ProgressMessage;
        public event EventHandler<AnalysisSummary>? AnalysisCompleted;
        public bool IsRunning => _isRunning;

        public async Task RunAnalysisAsync(string folderPath, string model = "cellpose", string device = "gpu")
        {
            if (_isRunning)
            {
                ProgressMessage?.Invoke(this, "⚠️ Анализ уже выполняется. Дождитесь завершения.");
                return;
            }

            _isRunning = true;
            _cts = new CancellationTokenSource();

            try
            {
                // Определяем путь к проекту CellHunter.Analyzer
                // Относительно текущей сборки (bin/Debug/...)
                string currentDir = AppDomain.CurrentDomain.BaseDirectory;

                // Поднимаемся на 4 уровня: bin/Debug/net8.0-windows/ -> CellHunter.Desktop/
                string desktopProjectDir = Path.GetFullPath(Path.Combine(currentDir, @"..\..\..\.."));

                // Поднимаемся еще на уровень до src/
                string srcDir = Path.GetFullPath(Path.Combine(desktopProjectDir, @".."));

                string analyzerDir = Path.Combine(srcDir, "CellHunter.Analyzer");
                string pythonPath = Path.Combine(analyzerDir, "venv", "Scripts", "python.exe");

                // Если путь не найден — пробуем абсолютный
                if (!File.Exists(pythonPath))
                {
                    pythonPath = @"C:\_Projects\WPF\CellHunter\src\CellHunter.Analyzer\venv\Scripts\python.exe";
                    analyzerDir = @"C:\_Projects\WPF\CellHunter\src\CellHunter.Analyzer";
                }

                if (!File.Exists(pythonPath))
                {
                    ProgressMessage?.Invoke(this, $"❌ Python не найден! Проверьте путь: {pythonPath}");
                    _isRunning = false;
                    return;
                }

                var startInfo = new ProcessStartInfo
                {
                    FileName = pythonPath,
                    Arguments = $"-m analyzer.main \"{folderPath}\" --model {model} --{device}",
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    StandardOutputEncoding = Encoding.UTF8,  // УЖЕ ЕСТЬ
                    StandardErrorEncoding = Encoding.UTF8,   // УЖЕ ЕСТЬ
                    WorkingDirectory = analyzerDir,
                    EnvironmentVariables =
                    {
                        ["PYTHONPATH"] = analyzerDir,
                        ["PYTHONIOENCODING"] = "utf-8"       // ← ДОБАВИТЬ ЭТУ СТРОКУ
                    }
                };

                _currentProcess = new Process { StartInfo = startInfo };
                _currentProcess.OutputDataReceived += OnOutputDataReceived;
                _currentProcess.ErrorDataReceived += OnErrorDataReceived;

                ProgressMessage?.Invoke(this, $"🚀 Запуск анализа: {folderPath}");
                ProgressMessage?.Invoke(this, $"📊 Модель: {model.ToUpper()}, Режим: {device.ToUpper()}");

                _currentProcess.Start();
                _currentProcess.BeginOutputReadLine();
                _currentProcess.BeginErrorReadLine();

                await _currentProcess.WaitForExitAsync(_cts.Token);

                ProgressMessage?.Invoke(this, "✅ Анализ завершен");
                _isRunning = false;
            }
            catch (OperationCanceledException)
            {
                ProgressMessage?.Invoke(this, "⏹️ Анализ отменен пользователем");
                try
                {
                    if (_currentProcess != null && !_currentProcess.HasExited)
                    {
                        _currentProcess.Kill();
                    }
                }
                catch { }
                _isRunning = false;
            }
            catch (Exception ex)
            {
                ProgressMessage?.Invoke(this, $"❌ Ошибка: {ex.Message}");
                _isRunning = false;
            }
        }

        public void CancelAnalysis()
        {
            _cts?.Cancel();
        }

        private void OnOutputDataReceived(object sender, DataReceivedEventArgs e)
        {
            if (string.IsNullOrEmpty(e.Data)) return;

            // Проверяем маркеры начала и конца JSON
            if (e.Data.Contains("===CELLHUNTER_JSON_START==="))
            {
                _collectingJson = true;
                _jsonBuffer = "";
                return;
            }

            if (e.Data.Contains("===CELLHUNTER_JSON_END==="))
            {
                _collectingJson = false;

                // Парсим накопленный JSON
                try
                {
                    var summary = JsonConvert.DeserializeObject<AnalysisSummary>(_jsonBuffer);
                    if (summary != null)
                    {
                        AnalysisCompleted?.Invoke(this, summary);
                        ProgressMessage?.Invoke(this, $"✅ Получены метаданные: {summary.ProcessedFiles} файлов, {summary.TotalTimeSeconds} сек.");
                    }
                }
                catch (Exception ex)
                {
                    ProgressMessage?.Invoke(this, $"⚠️ Ошибка парсинга JSON: {ex.Message}");
                }
                return;
            }

            if (_collectingJson)
            {
                _jsonBuffer += e.Data;
                return;
            }

            // Обычные сообщения (логи)
            ProgressMessage?.Invoke(this, e.Data);
        }

        private void OnErrorDataReceived(object sender, DataReceivedEventArgs e)
        {
            if (!string.IsNullOrEmpty(e.Data))
            {
                ProgressMessage?.Invoke(this, $"⚠️ {e.Data}");
            }
        }

        public void Dispose()
        {
            _currentProcess?.Dispose();
            _cts?.Dispose();
        }
    }
}