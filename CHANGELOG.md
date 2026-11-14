# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0-alpha] - 2026-11-14

First public developer preview of the project.

### Added

- WPF desktop application (.NET 8, MVVM) for batch analysis of microscopy
  images with a folder picker, model selector, live progress bar, log console,
  and per-image results grid.
- Python analyzer built on Cellpose 3.0.7 (`nuclei`) with automatic GPU/CPU
  selection and CPU fallback.
- Automatic Excel report (`cellhunter_report_<timestamp>.xlsx`) with file name,
  nucleus count, image dimensions, model, device, and processing time.
- Command-line interface for the analyzer (`python -m analyzer.main`).
- Runtime discovery of the analyzer directory and Python interpreter, including
  `CELLHUNTER_ANALYZER_DIR` and `CELLHUNTER_PYTHON` overrides.
- Actionable diagnostics when Python or the analyzer cannot be located.
- Sample BBBC001 images and expected counts under `src/CellHunter.Analyzer/examples/`.

### Fixed

- The progress bar no longer stays at 0%: the `PROGRESS:<current>/<total>:<file>`
  line is parsed correctly.
- The Start button no longer remains disabled after a failed or cancelled run.
- The analyzer no longer depends on a hard-coded developer path; arguments are
  passed through `ArgumentList`, so paths with spaces are safe.
- A non-zero analyzer exit code is now reported as an error instead of a success.

### Changed

- Pinned a mutually compatible Python dependency set around Cellpose 3.0.7,
  NumPy 1.x, and OpenCV 4.8–4.9; `ultralytics` is optional and disabled by default.
- README rewritten to describe the actual architecture, setup, configuration,
  report format, known limitations, and roadmap.

### Removed

- `builds/` is no longer tracked: it was a stale 10 MB snapshot of the sources
  and is now covered by `.gitignore`.

## Release links

- [0.1.0-alpha](https://github.com/bat801/CellHunter/releases/tag/v0.1.0-alpha)
