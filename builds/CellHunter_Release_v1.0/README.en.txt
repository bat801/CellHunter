# 🧬 CellHunter

**AI-powered desktop application for automated cell detection and counting in microscopy images.**

CellHunter uses CellPose neural network for nuclei detection, processes folders with images, and exports results to Excel.

---

## 📦 Features

- **CellPose** — neural network for nuclei detection
- **YOLO** — alternative model for general objects
- **GPU acceleration** (CUDA) — if you have NVIDIA GPU
- **Excel export** — report with cell counts per image
- **WPF interface** — clean and user-friendly

---

## ⚡ Requirements

- **Windows 10/11** (64-bit)
- **~5 GB free space** (for Python + libraries)
- **NVIDIA GPU** (optional, but 50-100x faster)

---

## 🚀 Installation (portable, no system pollution)

1. **Download** `CellHunter_Release_v1.0.zip`
2. **Extract** to any folder (e.g., `C:\CellHunter`)
3. **Run** `setup.bat` and wait 3-5 minutes
   - It will download Python, install dependencies, and create a desktop shortcut
4. **Launch** via desktop shortcut **CellHunter**

---

## 🖥️ How to use

1. Click **"Select Folder"** and choose a folder with images
   - Supported formats: `.tif`, `.tiff`, `.png`, `.jpg`, `.jpeg`, `.bmp`
2. Choose model:
   - **CellPose** (recommended for nuclei detection)
   - **YOLO** (for general objects)
3. Click **"Run"** and wait for completion
4. View results in the table:
   - Filename, nuclei count, dimensions, processing time
5. Click **"Excel"** to save the report in the image folder

---

## 📁 Sample Data

Test images are in `CellHunter.Analyzer\examples\`:
- **BBBC001** — human colon cancer cells (6 images)
- **BBBC002** — Drosophila cells (50 images)

---

## 🗑️ Uninstall

To completely remove CellHunter:
1. Delete the desktop shortcut
2. Delete the folder where you extracted the archive

Either run uninstall.bat.

**That's it!** No registry entries or system folders left.

---

## ❓ FAQ

**Error "Python not found" when starting?**
Run `setup.bat` again.

**Why is it slow?**
Use GPU. On CPU it's ~30-50 sec per image.

**Can I process 1000 images?**
Yes. The app processes all images in the folder.

**What's the accuracy?**
On BBBC001 test data: 10-20% deviation from manual counting.

---

## 📝 License

MIT License

---

## 🙏 Acknowledgments

- [CellPose](https://github.com/MouseLand/cellpose) — cell segmentation model
- [BBBC](https://bbbc.broadinstitute.org/) — test datasets

---

## 📧 Contact

Questions and suggestions: bat20039@gmail.com