namespace CellHunter.Desktop.Models
{
    public class AnalysisSummary
    {
        public string Status { get; set; } = string.Empty;
        public int TotalFiles { get; set; }
        public int ProcessedFiles { get; set; }
        public string ExcelPath { get; set; } = string.Empty;
        public string Model { get; set; } = string.Empty;
        public string Device { get; set; } = string.Empty;
        public double TotalTimeSeconds { get; set; }
        public List<ImageAnalysisResult> Results { get; set; } = new();
    }
}