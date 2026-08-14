namespace CellHunter.Desktop.Models;

public class ImageAnalysisResult
{
    public string Filename { get; set; } = string.Empty;
    public int Count { get; set; }
    public int Width { get; set; }
    public int Height { get; set; }
    public string Model { get; set; } = string.Empty;
    public string Device { get; set; } = string.Empty;
    public double TimeSeconds { get; set; }
}