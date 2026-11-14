# CellHunter 0.1.0-alpha

**Developer preview.** This is the first public alpha of CellHunter, a Windows
desktop application for automated cell counting in microscopy images. The
desktop app and the Cellpose analysis pipeline work end to end, but the project
is still an MVP: interfaces, report columns, and packaging may change in later
releases.

## Highlights

- Batch analysis of a flat image folder with Cellpose 3.0.7 (`nuclei`).
- Automatic GPU/CPU selection with a safe CPU fallback.
- Live progress bar and streamed analyzer logs.
- Per-image results table: file, nucleus count, dimensions, processing time.
- Excel report written next to the analyzed images.
- Self-contained Windows build: no .NET installation required.

## What is in the archive

```
CellHunter.Desktop.exe     self-contained WPF application (win-x64)
analyzer/                  Python analyzer package (main.py)
requirements.txt           pinned Python dependencies
README.md                  full project documentation
LICENSE                    MIT license
```

The Python analyzer is **not bundled**. Cellpose and PyTorch are large
dependencies, so the application looks for a local Python environment at
runtime.

## Requirements

| Component | Requirement |
|---|---|
| OS | Windows 10/11 (64-bit) |
| Python | 3.10–3.12 (64-bit); 3.12 recommended |
| .NET | Not required for this build |
| GPU | Optional NVIDIA GPU with CUDA |
| Disk | ~5 GB for the Python environment and model weights |

## Quick start

1. Unpack the archive into a writable folder, for example `C:\CellHunter`.
2. Create the Python environment **in the unpacked folder**:

   ```powershell
   cd C:\CellHunter
   py -3.12 -m venv venv
   venv\Scripts\python -m pip install --upgrade pip
   venv\Scripts\pip install -r requirements.txt
   ```

3. Start `CellHunter.Desktop.exe`.
4. Select a folder with images, pick the `cellpose` model, and click **Запуск**
   (*Start*). The user interface is currently in Russian.

For CUDA acceleration, install a CUDA-enabled PyTorch build from
[pytorch.org](https://pytorch.org/get-started/locally/) before step 2, then run
the remaining requirements as shown above.

The first analysis downloads the pretrained Cellpose nuclei weights and
therefore requires an internet connection.

## Known limitations

- Only top-level files in the selected folder are analyzed; subfolders are not
  traversed.
- The GUI has no device selector: it requests GPU execution and falls back to
  CPU automatically.
- The YOLO option is experimental and has no bundled cell-detection weights.
- The **Excel** button in the UI is a placeholder; reports are generated
  automatically after each run.
- Images in non-ASCII paths (for example Cyrillic) cannot be read by OpenCV on
  Windows; keep input paths ASCII-only.
- The executable is not code-signed, so Windows SmartScreen may show a warning.
- The build was verified by compiling and packaging; a full functional pass on
  representative microscopy data has not been performed for this alpha.

## Verification

Download `SHA256SUMS.txt` next to the archive and verify the checksum:

```powershell
Get-FileHash .\CellHunter-0.1.0-alpha-win-x64.zip -Algorithm SHA256
```

## Feedback

Please report issues, including the log output and image modality, at
<https://github.com/bat801/CellHunter/issues>.

## License

MIT. See `LICENSE`.
