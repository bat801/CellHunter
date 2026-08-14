using System;
using System.Threading.Tasks;
using CellHunter.Desktop.Models;

namespace CellHunter.Desktop.Services
{
    public interface IPythonBridge
    {
        event EventHandler<string> ProgressMessage;
        event EventHandler<AnalysisSummary> AnalysisCompleted;
        Task RunAnalysisAsync(string folderPath, string model = "cellpose", string device = "gpu");
        void CancelAnalysis();
        bool IsRunning { get; }
    }
}