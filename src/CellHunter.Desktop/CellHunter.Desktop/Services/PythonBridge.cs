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
                if (!Directory.Exists(folderPath))
                {
                    ReportError($"Папка с изображениями не найдена: {folderPath}");
                    return;
                }

                // 1. Ищем каталог анализатора: переменная окружения → рядом с приложением → вверх по дереву репозитория
                string? analyzerDir = FindAnalyzerDirectory();
                if (analyzerDir == null)
                {
                    ReportError(
                        "Не найден Python-анализатор CellHunter (analyzer/main.py)." + Environment.NewLine +
                        "  Проверено:" + Environment.NewLine +
                        "    • переменная окружения CELLHUNTER_ANALYZER_DIR" + Environment.NewLine +
                        $"    • текущий каталог и все родительские: {AppDomain.CurrentDomain.BaseDirectory}" + Environment.NewLine +
                        "  Решение: запустите приложение из каталога репозитория (src/CellHunter.Analyzer) " +
                        "или задайте CELLHUNTER_ANALYZER_DIR.");
                    return;
                }

                // 2. Ищем, чем запускать: venv → встроенный exe → python из PATH
                if (!TryResolveRunner(analyzerDir, out var runner))
                {
                    ReportError(
                        "Не найден Python для запуска анализатора." + Environment.NewLine +
                        "  Проверено:" + Environment.NewLine +
                        $"    • виртуальные окружения в {analyzerDir}: venv, .venv, env" + Environment.NewLine +
                        $"    • встроенный анализатор: {Path.Combine(analyzerDir, "CellHunterAnalyzer.exe")}" + Environment.NewLine +
                        "    • python.exe в PATH" + Environment.NewLine +
                        "  Создайте окружение и установите зависимости:" + Environment.NewLine +
                        $"    cd \"{analyzerDir}\"" + Environment.NewLine +
                        "    python -m venv venv" + Environment.NewLine +
                        @"    venv\Scripts\pip install -r requirements.txt");
                    return;
                }

                var startInfo = CreateStartInfo(runner, analyzerDir, folderPath, model, device);

                _currentProcess = new Process { StartInfo = startInfo };
                _currentProcess.OutputDataReceived += OnOutputDataReceived;
                _currentProcess.ErrorDataReceived += OnErrorDataReceived;

                ProgressMessage?.Invoke(this, $"🚀 Запуск анализа: {folderPath}");
                ProgressMessage?.Invoke(this, $"📊 Модель: {model.ToUpper()}, Режим: {device.ToUpper()}");

                _currentProcess.Start();
                _currentProcess.BeginOutputReadLine();
                _currentProcess.BeginErrorReadLine();

                await _currentProcess.WaitForExitAsync(_cts.Token);

                if (_currentProcess.ExitCode == 0)
                {
                    ProgressMessage?.Invoke(this, "✅ Анализ завершен");
                }
                else
                {
                    ReportError(
                        $"Анализатор завершился с кодом {_currentProcess.ExitCode}. " +
                        "Подробности — в сообщениях выше.");
                }
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
            }
            catch (Exception ex)
            {
                ReportError($"Не удалось запустить анализ: {ex.Message}");
            }
            finally
            {
                _isRunning = false;
            }
        }

        public void CancelAnalysis()
        {
            try
            {
                _cts?.Cancel();
            }
            catch (ObjectDisposedException)
            {
                // Анализ уже завершился — отменять нечего.
            }
        }

        /// <summary>
        /// Поднимается от каталога сборки вверх и ищет анализатор:
        /// сначала рядом с приложением (published), затем в src/CellHunter.Analyzer (dev-запуск).
        /// </summary>
        private static string? FindAnalyzerDirectory()
        {
            var fromEnv = Environment.GetEnvironmentVariable("CELLHUNTER_ANALYZER_DIR");
            if (!string.IsNullOrWhiteSpace(fromEnv))
            {
                var full = Path.GetFullPath(fromEnv.Trim('"'));
                if (File.Exists(Path.Combine(full, "analyzer", "main.py")))
                {
                    return full;
                }
            }

            var dir = new DirectoryInfo(AppDomain.CurrentDomain.BaseDirectory);
            while (dir != null)
            {
                // Анализатор лежит рядом с приложением
                if (File.Exists(Path.Combine(dir.FullName, "analyzer", "main.py")))
                {
                    return dir.FullName;
                }

                // Исходники в репозитории
                var inRepo = Path.Combine(dir.FullName, "src", "CellHunter.Analyzer");
                if (File.Exists(Path.Combine(inRepo, "analyzer", "main.py")))
                {
                    return inRepo;
                }

                dir = dir.Parent;
            }

            return null;
        }

        private static bool TryResolveRunner(string analyzerDir, out Runner runner)
        {
            // Виртуальные окружения внутри проекта анализатора
            foreach (var venv in new[] { "venv", ".venv", "env", ".env" })
            {
                var candidate = Path.Combine(analyzerDir, venv, "Scripts", "python.exe");
                if (File.Exists(candidate))
                {
                    runner = new Runner(candidate, isPythonModule: true);
                    return true;
                }
            }

            // Явно заданный интерпретатор
            var explicitPython = Environment.GetEnvironmentVariable("CELLHUNTER_PYTHON");
            if (!string.IsNullOrWhiteSpace(explicitPython) && File.Exists(explicitPython))
            {
                runner = new Runner(explicitPython, isPythonModule: true);
                return true;
            }

            // Встроенный PyInstaller-анализатор (README обещает запуск без Python)
            foreach (var bundled in new[]
                     {
                         "CellHunterAnalyzer.exe",
                         Path.Combine("dist", "CellHunterAnalyzer.exe"),
                         Path.Combine("analyzer", "CellHunterAnalyzer.exe")
                     })
            {
                var candidate = Path.Combine(analyzerDir, bundled);
                if (File.Exists(candidate))
                {
                    runner = new Runner(candidate, isPythonModule: false);
                    return true;
                }
            }

            // Python из PATH
            var pythonOnPath = FindOnPath("python.exe") ?? FindOnPath("python");
            if (pythonOnPath != null)
            {
                runner = new Runner(pythonOnPath, isPythonModule: true);
                return true;
            }

            runner = null!;
            return false;
        }

        private static ProcessStartInfo CreateStartInfo(
            Runner runner, string analyzerDir, string folderPath, string model, string device)
        {
            var startInfo = new ProcessStartInfo
            {
                FileName = runner.FileName,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true,
                StandardOutputEncoding = Encoding.UTF8,
                StandardErrorEncoding = Encoding.UTF8,
                WorkingDirectory = analyzerDir
            };

            if (runner.IsPythonModule)
            {
                startInfo.ArgumentList.Add("-m");
                startInfo.ArgumentList.Add("analyzer.main");
                startInfo.EnvironmentVariables["PYTHONPATH"] = analyzerDir;
                startInfo.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
            }

            // Путь передаётся отдельным аргументом — пробелы и кавычки обрабатываются корректно
            startInfo.ArgumentList.Add(folderPath);
            startInfo.ArgumentList.Add("--model");
            startInfo.ArgumentList.Add(model);
            startInfo.ArgumentList.Add($"--{device}");

            return startInfo;
        }

        private static string? FindOnPath(string fileName)
        {
            var path = Environment.GetEnvironmentVariable("PATH");
            if (string.IsNullOrEmpty(path)) return null;

            foreach (var dir in path.Split(Path.PathSeparator, StringSplitOptions.RemoveEmptyEntries))
            {
                try
                {
                    var candidate = Path.Combine(dir.Trim('"'), fileName);
                    if (File.Exists(candidate))
                    {
                        return candidate;
                    }
                }
                catch (ArgumentException)
                {
                    // Некорректная запись в PATH — пропускаем
                }
            }

            return null;
        }

        private void ReportError(string message)
        {
            ProgressMessage?.Invoke(this, $"❌ {message}");
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

                var json = _jsonBuffer.Trim();
                if (json.Length > 0)
                {
                    try
                    {
                        var summary = JsonConvert.DeserializeObject<AnalysisSummary>(json);
                        if (summary != null)
                        {
                            AnalysisCompleted?.Invoke(this, summary);
                        }
                    }
                    catch (Exception ex)
                    {
                        ProgressMessage?.Invoke(this, $"⚠️ Ошибка парсинга JSON: {ex.Message}");
                    }
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
            _cts?.Cancel();
            _currentProcess?.Dispose();
            _cts?.Dispose();
        }

        private sealed class Runner
        {
            public Runner(string fileName, bool isPythonModule)
            {
                FileName = fileName;
                IsPythonModule = isPythonModule;
            }

            public string FileName { get; }
            public bool IsPythonModule { get; }
        }
    }
}
