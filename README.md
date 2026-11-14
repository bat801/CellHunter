# CellHunter

![.NET](https://img.shields.io/badge/.NET-8.0-512BD4)
![Python](https://img.shields.io/badge/Python-3.10--3.12-3776AB)
![Cellpose](https://img.shields.io/badge/Cellpose-3.0.7-2E8B57)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D4)
![License](https://img.shields.io/badge/license-MIT-green)

CellHunter is a Windows desktop application for automated cell counting in
microscopy images. It combines a WPF front end with a Python analysis backend
built on [Cellpose](https://github.com/MouseLand/cellpose): select a folder,
start the analysis, and get per-image nuclei counts plus an Excel workbook —
without writing any code.

> **Project status: early-stage MVP.** The desktop shell and the Cellpose
> analysis pipeline work end to end. Some repository areas (tests, docs,
> installer scripts, the Excel button in the UI) are still placeholders; see
> [Known limitations](#known-limitations).

---

## Features

| Capability | Status |
|---|---|
| Batch analysis of a flat image folder | Implemented |
| Cellpose nuclei segmentation on GPU or CPU | Implemented |
| Live progress bar and log console | Implemented |
| Per-image results grid | Implemented |
| Automatic Excel report | Implemented |
| Model selection (Cellpose / YOLO) | Cellpose implemented, YOLO experimental |
| Image preview with detected-cell overlay | Planned |
| Cell area and density metrics | Planned |
| Recursive folder scanning | Planned |
| One-click installer | Not implemented |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│ CellHunter.Desktop — WPF, .NET 8, MVVM                   │
│  folder picker · model selector · progress bar           │
│  log console · results grid · status bar                 │
└──────────────────────────┬───────────────────────────────┘
                           │ Process + stdio
                           │ PROGRESS:…, JSON between markers
┌──────────────────────────▼───────────────────────────────┐
│ CellHunter.Analyzer — Python 3.10–3.12                   │
│  main.py · Cellpose 3 (nuclei)                           │
│  OpenCV · NumPy · pandas · openpyxl                      │
└──────────────────────────┬───────────────────────────────┘
                           ▼
              cellhunter_report_<timestamp>.xlsx
```

### How it works

1. The WPF app (`MainViewModel`) validates the selected folder and starts
   `PythonBridge`.
2. `PythonBridge` locates the analyzer directory and a Python interpreter,
   then runs `python -m analyzer.main <folder> --model <model> --gpu|cpu`.
3. `main.py` loads the requested model (Cellpose or YOLO), iterates over the
   images in the folder, and prints a machine-readable progress line for every
   file: `PROGRESS:<current>/<total>:<file name>`.
4. When finished, the backend writes the Excel report into the selected folder
   and prints a JSON summary between `===CELLHUNTER_JSON_START===` and
   `===CELLHUNTER_JSON_END===` markers.
5. `PythonBridge` parses the JSON, raises `AnalysisCompleted`, and the view
   model fills the results grid and resets the UI state.

The marker-based protocol is intentionally simple: the backend can also be
invoked from the command line or wrapped by another client.

---

## Requirements

| Component | Requirement |
|---|---|
| OS | Windows 10/11 (64-bit) |
| .NET | .NET 8 SDK (to build), .NET 8 Desktop Runtime (to run) |
| Python | 3.10–3.12 (64-bit) |
| GPU | Optional NVIDIA GPU with CUDA for faster inference |
| Disk | ~5 GB for the Python environment and model weights |

---

## Getting started

### 1. Set up the Python backend

```powershell
cd src\CellHunter.Analyzer
py -3.12 -m venv venv
venv\Scripts\python -m pip install --upgrade pip
venv\Scripts\pip install -r requirements.txt
```

`requirements.txt` pins a mutually compatible set around Cellpose 3.0.7.
Cellpose downloads its pretrained nuclei weights on first use, so an internet
connection is required once.

**GPU support (optional).** The pinned `torch` wheel is CPU-only by default.
For CUDA acceleration, install the build that matches your driver from
[pytorch.org](https://pytorch.org/get-started/locally/) before installing the
remaining requirements.

### 2. Build and run the desktop app

```powershell
dotnet build src\CellHunter.Desktop\CellHunter.Desktop.sln
dotnet run --project src\CellHunter.Desktop\CellHunter.Desktop\CellHunter.Desktop.csproj
```

Alternatively, open `src\CellHunter.Desktop\CellHunter.Desktop.sln` in
Visual Studio 2022 and press **F5**.

### 3. Analyze a folder

1. Click **Выбрать папку** (*Select folder*) and choose a folder with images.
2. Pick a model — `cellpose` (default) or `yolo` (experimental).
3. Click **Запуск** (*Start*). Progress and backend logs are streamed into the
   left panel; results appear in the table on the right.
4. A timestamped `.xlsx` report is written to the selected folder automatically.

The interface is currently in Russian; the code and this documentation are in
English.

---

## Command-line usage

The analyzer can be used without the desktop app:

```powershell
cd src\CellHunter.Analyzer
venv\Scripts\python -m analyzer.main C:\data\experiment --model cellpose --gpu
```

| Option | Description |
|---|---|
| `<folder>` | Folder containing images (required) |
| `--model`, `-m` | `cellpose` (default) or `yolo` |
| `--device`, `-d` | `cpu` or `cuda`; defaults to auto-detection |
| `--cpu` | Force CPU execution |
| `--gpu` | Force CUDA execution (falls back to CPU if unavailable) |

Supported formats: `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.bmp`.
Only the top level of the folder is scanned — subfolders are not traversed.

---

## Report format

The report is saved next to the analyzed images as
`cellhunter_report_<YYYYMMDD_HHMMSS>.xlsx`, one row per processed image:

| Column | Description |
|---|---|
| `filename` | Image file name |
| `count` | Number of detected nuclei |
| `width`, `height` | Image dimensions in pixels |
| `model` | Model used (`cellpose` / `yolo`) |
| `device` | Device actually used (`cpu` / `cuda`) |
| `time_seconds` | Processing time for this image |

If an image cannot be read or processed, it is skipped, the reason is printed
to the log, and the remaining images continue to run.

---

## Configuration

`PythonBridge` resolves its environment at runtime; no paths are hard-coded.

| Variable | Purpose |
|---|---|
| `CELLHUNTER_ANALYZER_DIR` | Explicit path to the `CellHunter.Analyzer` directory |
| `CELLHUNTER_PYTHON` | Explicit path to the Python interpreter |

Discovery order for the analyzer directory:

1. `CELLHUNTER_ANALYZER_DIR`
2. the application directory (published layout)
3. parent directories up to the repository root (development layout)

Discovery order for the interpreter:

1. `venv`, `.venv`, `env`, `.env` inside the analyzer directory
2. `CELLHUNTER_PYTHON`
3. bundled `CellHunterAnalyzer.exe` (if present)
4. `python.exe` on `PATH`

If nothing is found, the app shows an actionable error listing every location
it checked and the exact commands needed to create the environment.

---

## Project structure

```
CellHunter/
├── src/
│   ├── CellHunter.Desktop/            # WPF front end (.NET 8)
│   │   └── CellHunter.Desktop/
│   │       ├── Models/                # AnalysisSummary, ImageAnalysisResult
│   │       ├── Services/              # IPythonBridge, PythonBridge
│   │       ├── Utils/                 # RelayCommand, ObservableObject, converter
│   │       ├── ViewModels/            # MainViewModel
│   │       ├── App.xaml(.cs)
│   │       └── MainWindow.xaml(.cs)
│   └── CellHunter.Analyzer/           # Python backend
│       ├── analyzer/main.py           # CLI, detection loop, Excel export
│       ├── examples/                  # BBBC001 sample images and expected counts
│       ├── tests/                     # placeholder
│       └── requirements.txt
├── docs/                              # placeholders
├── scripts/                           # build and installer placeholders
└── README.md
```

Sample data lives in `src/CellHunter.Analyzer/examples/`; expected counts for
the BBBC001 set are in `examples/sample_output/`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| “Python not found” error on start | No `venv` and no Python on `PATH` | Create the environment as shown above, or set `CELLHUNTER_PYTHON` |
| “Analyzer not found” error | App is not running from the repository or a published layout | Set `CELLHUNTER_ANALYZER_DIR` |
| GPU is reported as unavailable | PyTorch CPU wheel or no CUDA driver | Install a CUDA-enabled PyTorch build; the app falls back to CPU automatically |
| Analysis is slow | Running on CPU | Install the CUDA build of PyTorch, or reduce image size |
| Image is skipped as unreadable | Non-ASCII path (e.g. Cyrillic) — OpenCV limitation on Windows | Move the images to an ASCII-only path |
| First run is slow or fails offline | Cellpose is downloading pretrained weights | Ensure internet access for the first run |

---

## Known limitations

- The GUI has no device selector: it requests GPU execution and relies on the
  automatic CPU fallback.
- Only top-level files in the selected folder are analyzed.
- The YOLO branch is experimental: it expects `models/yolov8n.pt` inside
  `CellHunter.Analyzer`, and the stock COCO weights do not detect cells.
- The **Excel** button in the UI is a placeholder; reports are generated
  automatically after each run.
- `docs/`, `tests/`, and the packaging scripts under `scripts/` are empty
  placeholders.
- OpenCV on Windows cannot read images from non-ASCII paths.
- Detection quality depends on image modality and magnification; validate
  counts against manual annotations before using them in publications.

---

## Roadmap

- [ ] Image preview with detected-cell overlay
- [ ] Cell area and density metrics in the report
- [ ] Recursive folder scanning and batch queue
- [ ] Working export button and report re-opening
- [ ] Trained YOLO weights (or removal of the YOLO branch)
- [ ] Unit tests for the bridge protocol and the analyzer
- [ ] PyInstaller bundle and Inno Setup installer
- [ ] English localization of the UI

---

## Contributing

Issues and pull requests are welcome. Please keep commits focused and follow
the [Conventional Commits](https://www.conventionalcommits.org/) format, and
make sure the solution builds with no warnings:

```powershell
dotnet build src\CellHunter.Desktop\CellHunter.Desktop.sln
```

---

## License

Released under the MIT License. See [LICENSE](LICENSE).
