# Capture real CellHunter.Desktop screenshots and GIF frames.
#
# The script starts the built desktop app with a demo folder, presses the
# "Start" button through UI Automation, and records the window while the
# Python analyzer runs. No manual interaction is required.
#
#   powershell -ExecutionPolicy Bypass -File scripts\capture-ui.ps1
#
# Output goes to .cache\ui-capture (ignored by git):
#   main.png / results.png   before and after the run
#   frames\frame_XXXX.png    one frame every -IntervalMs while running
#   rects.json               bounds of the annotated UI elements

[CmdletBinding()]
param(
    [string]$Folder,
    [string]$OutDir,
    [int]$IntervalMs = 250,
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
if (-not $Folder) { $Folder = Join-Path $root '.cache\ui-demo' }
if (-not $OutDir) { $OutDir = Join-Path $root '.cache\ui-capture' }

$exe = Join-Path $root 'src\CellHunter.Desktop\CellHunter.Desktop\bin\Release\net8.0-windows\CellHunter.Desktop.exe'
$analyzer = Join-Path $root 'src\CellHunter.Analyzer'
$python = Join-Path $root '.cache\docs-venv\Scripts\python.exe'

foreach ($required in @($exe, $python)) {
    if (-not (Test-Path $required)) { throw "Missing: $required" }
}

# --- demo data --------------------------------------------------------------
New-Item -ItemType Directory -Force -Path $Folder | Out-Null
Get-ChildItem $Folder -Filter '*.xlsx' -ErrorAction SilentlyContinue | Remove-Item -Force
$samples = Join-Path $analyzer 'examples\sample_images\BBBC001_v1_images_tif\human_ht29_colon_cancer_1_images'
Copy-Item (Join-Path $samples '*.tif') $Folder -Force

# --- environment for the child process --------------------------------------
$env:CELLHUNTER_PYTHON = $python
$env:CELLHUNTER_ANALYZER_DIR = $analyzer
$env:CELLPOSE_LOCAL_MODELS_PATH = Join-Path $root '.cache\cellpose'
$env:PYTHONIOENCODING = 'utf-8'

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$framesDir = Join-Path $OutDir 'frames'
if (Test-Path $framesDir) { Remove-Item $framesDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $framesDir | Out-Null

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName UIAutomationClient

# PowerShell resolves GetCurrentPattern to an internal overload, so the
# InvokePattern call is compiled in C# where overload resolution is exact.
if (-not ('UiaInvoker' -as [type])) {
    $uiaAssemblies = [AppDomain]::CurrentDomain.GetAssemblies() |
        Where-Object { $_.GetName().Name -in @('UIAutomationClient', 'UIAutomationTypes') } |
        ForEach-Object { $_.Location }
    Add-Type -ReferencedAssemblies $uiaAssemblies -TypeDefinition @"
using System.Windows.Automation;

public static class UiaInvoker
{
    public static void Invoke(AutomationElement element)
    {
        var pattern = (InvokePattern)element.GetCurrentPattern(InvokePattern.Pattern);
        pattern.Invoke();
    }

    public static bool ScrollToBottom(AutomationElement element)
    {
        try
        {
            var pattern = (ScrollPattern)element.GetCurrentPattern(ScrollPattern.Pattern);
            if (!pattern.Current.VerticallyScrollable) return false;
            pattern.SetScrollPercent(ScrollPattern.NoScroll, 100);
            return true;
        }
        catch
        {
            return false;
        }
    }
}
"@
}

if (-not ('Win32Window' -as [type])) {
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public struct RECT { public int Left, Top, Right, Bottom; }
public static class Win32Window {
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdc, uint flags);
}
"@
}

function Save-WindowShot {
    param([IntPtr]$Handle, [string]$Path)

    $rect = New-Object RECT
    if (-not [Win32Window]::GetWindowRect($Handle, [ref]$rect)) {
        throw 'GetWindowRect failed'
    }
    $width = $rect.Right - $rect.Left
    $height = $rect.Bottom - $rect.Top

    # PrintWindow renders the window even when it is covered by another
    # window, which keeps the capture deterministic on a busy desktop.
    $bitmap = New-Object System.Drawing.Bitmap($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $hdc = $graphics.GetHdc()
    try {
        if (-not [Win32Window]::PrintWindow($Handle, $hdc, 2)) {
            throw 'PrintWindow failed'
        }
    }
    finally {
        $graphics.ReleaseHdc($hdc)
    }
    try {
        $bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
    return @{ Left = $rect.Left; Top = $rect.Top; Width = $width; Height = $height }
}

$process = Start-Process -FilePath $exe -ArgumentList @('--folder', "`"$Folder`"") -PassThru
try {
    $deadline = (Get-Date).AddSeconds(40)
    while ($process.MainWindowHandle -eq [IntPtr]::Zero -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 200
        $process.Refresh()
    }
    if ($process.MainWindowHandle -eq [IntPtr]::Zero) { throw 'Main window did not appear' }

    $handle = $process.MainWindowHandle
    [Win32Window]::SetForegroundWindow($handle) | Out-Null
    Start-Sleep -Milliseconds 2000

    # --- locate controls through UI Automation -----------------------------
    $window = [System.Windows.Automation.AutomationElement]::FromHandle($handle)
    $elements = $window.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        [System.Windows.Automation.Condition]::TrueCondition
    )

    $byName = @{}
    $byType = @{}
    foreach ($element in $elements) {
        try {
            $name = $element.Current.Name
            $type = $element.Current.ControlType.ProgrammaticName.Replace('ControlType.', '')
            if ($name) { $byName[$name] = $element }
            if (-not $byType.ContainsKey($type)) { $byType[$type] = @() }
            $byType[$type] += $element
        }
        catch { }
    }

    $startButton = $byName.Keys | Where-Object { $_ -like '*Запуск*' } | Select-Object -First 1
    if (-not $startButton) { throw 'Start button not found' }
    $startElement = $byName[$startButton]

    $shot = Save-WindowShot -Handle $handle -Path (Join-Path $OutDir 'main.png')

    function Get-RelativeBounds($element) {
        if ($null -eq $element) { return $null }
        $r = $element.Current.BoundingRectangle
        return [ordered]@{
            x = [int]($r.X - $shot.Left)
            y = [int]($r.Y - $shot.Top)
            w = [int]$r.Width
            h = [int]$r.Height
        }
    }

    # WPF exposes both a Button and the TextBlock inside it under the same
    # name; walk up until the real control is found.
    function Get-ControlAncestor($element, [string]$controlType) {
        if ($null -eq $element) { return $null }
        $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
        $current = $element
        while ($null -ne $current) {
            if ($current.Current.ControlType.ProgrammaticName -eq "ControlType.$controlType") {
                return $current
            }
            $current = $walker.GetParent($current)
        }
        return $element
    }

    $folderButtonName = $byName.Keys | Where-Object { $_ -like '*Выбрать папку*' } | Select-Object -First 1
    $folderButton = if ($folderButtonName) { Get-ControlAncestor $byName[$folderButtonName] 'Button' } else { $null }
    $startElement = Get-ControlAncestor $startElement 'Button'
    $combo = if ($byType.ContainsKey('ComboBox')) { $byType['ComboBox'][0] } else { $null }
    $progress = if ($byType.ContainsKey('ProgressBar')) { $byType['ProgressBar'][0] } else { $null }
    $grid = if ($byType.ContainsKey('DataGrid')) { $byType['DataGrid'][0] } else { $null }
    $logs = $byType['Edit'] | Sort-Object { $_.Current.BoundingRectangle.Width * $_.Current.BoundingRectangle.Height } -Descending | Select-Object -First 1

    $rects = [ordered]@{
        window = [ordered]@{ w = $shot.Width; h = $shot.Height }
        folder = Get-RelativeBounds $folderButton
        model = Get-RelativeBounds $combo
        start = Get-RelativeBounds $startElement
        progress = Get-RelativeBounds $progress
        logs = Get-RelativeBounds $logs
        results = Get-RelativeBounds $grid
    }
    $rects | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $OutDir 'rects.json') -Encoding UTF8
    # --- press Start --------------------------------------------------------
    [UiaInvoker]::Invoke($startElement)
    Write-Host 'Started analysis through UI Automation.'

    # --- record frames until the report appears -----------------------------
    $started = Get-Date
    $frame = 0
    $reportSeenAt = $null
    while (((Get-Date) - $started).TotalSeconds -lt $TimeoutSeconds) {
        $path = Join-Path $framesDir ('frame_{0:D4}.png' -f $frame)
        Save-WindowShot -Handle $handle -Path $path | Out-Null
        $frame++

        if (-not $reportSeenAt) {
            $report = Get-ChildItem $Folder -Filter '*.xlsx' -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($report) { $reportSeenAt = Get-Date }
        }
        elseif (((Get-Date) - $reportSeenAt).TotalSeconds -gt 2.5) {
            break
        }

        Start-Sleep -Milliseconds $IntervalMs
    }

    Start-Sleep -Milliseconds 800
    [Win32Window]::SetForegroundWindow($handle) | Out-Null
    Start-Sleep -Milliseconds 400

    # Scroll the log panel to the end so the final summary is visible.
    foreach ($element in $elements) {
        try {
            $bounds = $element.Current.BoundingRectangle
            if ($bounds.X -lt ($shot.Left + 500) -and $bounds.Height -gt 100) {
                if ([UiaInvoker]::ScrollToBottom($element)) { break }
            }
        }
        catch { }
    }
    Start-Sleep -Milliseconds 500

    Save-WindowShot -Handle $handle -Path (Join-Path $OutDir 'results.png') | Out-Null

    Write-Host "Captured $frame frames in $([int]((Get-Date) - $started).TotalSeconds) s."
}
finally {
    if (-not $process.HasExited) {
        $process.CloseMainWindow() | Out-Null
        Start-Sleep -Milliseconds 600
        if (-not $process.HasExited) { $process.Kill() }
    }
}
