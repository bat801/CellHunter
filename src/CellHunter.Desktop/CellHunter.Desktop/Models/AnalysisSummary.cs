using Newtonsoft.Json;

namespace CellHunter.Desktop.Models
{
    public class AnalysisSummary
    {
        public string Status { get; set; } = string.Empty;

        [JsonProperty("total_files")]
        public int TotalFiles { get; set; }

        [JsonProperty("processed_files")]
        public int ProcessedFiles { get; set; }

        [JsonProperty("excel_path")]
        public string ExcelPath { get; set; } = string.Empty;

        public string Model { get; set; } = string.Empty;
        public string Device { get; set; } = string.Empty;

        [JsonProperty("total_time_seconds")]
        public double TotalTimeSeconds { get; set; }

        [JsonProperty("results")]
        public List<ImageAnalysisResult> Results { get; set; } = new();
    }
}