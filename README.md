![.NET](https://img.shields.io/badge/.NET-8.0-purple)
![Python](https://img.shields.io/badge/Python-3.10-blue)
![YOLO](https://img.shields.io/badge/YOLO-v8-red)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows-blue)

# 🧬 CellHunter

AI-powered desktop application for automated cell detection, counting and quantitative analysis in microscopy images.

> **Built with WPF (C#) + Python + YOLOv8 | One-click Excel export | Batch processing**

## 🎯 What CellHunter does

CellHunter is a desktop tool designed for **biologists and researchers** who need to quickly analyze large sets of microscopy images. Just select a folder with images, click "Analyze", and get:

- ✅ **Cell count** per image  
- 📐 **Average cell area** and **total area**  
- 📊 **Density metrics**  
- 📁 **Excel report** with all data  
- 🖼️ **Visual previews** with detected cells highlighted

No Python installation required — it's packaged as a single `.exe` installer.

## Getting Started
[Installation and launch instructions]

---

## ⚙️ Architecture

```
┌─────────────────────────────────────────────────┐
│              CellHunter Desktop (WPF)           │
│  ┌───────────────────────────────────────────┐  │
│  │  Beautiful UI · Progress Bar · Table      │  │
│  └───────────────────────────────────────────┘  │
│                       │                          │
│                       ▼                          │
│  ┌───────────────────────────────────────────┐  │
│  │  C# ↔ Python Bridge (JSON over stdio)    │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│            Python Backend (YOLOv8)              │
│  ┌───────────────────────────────────────────┐  │
│  │  Detection · Segmentation · Metrics       │  │
│  └───────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────┐  │
│  │  OpenCV · NumPy · Pandas · OpenPyXL      │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 🚀 Key Features

| Feature | Description |
|---------|-------------|
| 📁 **Batch processing** | Process thousands of images in one click |
| 🎯 **YOLO-powered detection** | State-of-the-art AI model for cell detection |
| 📊 **Excel export** | Generate clean `.xlsx` reports with all metrics |
| 🖼️ **Image preview** | Click any row to see the image with bounding boxes |
| 📈 **Progress tracking** | Real-time logs and progress bar |
| 🔒 **Self-contained** | Packaged with Python, no dependencies to install |
| ⚠️ **Smart path handling** | Warns about Cyrillic characters that may break OpenCV |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend (UI)** | WPF (.NET 8) + XAML |
| **Styling** | Material Design In XAML Toolkit |
| **Backend** | Python 3.10+ |
| **Detection** | YOLOv8 (Ultralytics) |
| **Image Processing** | OpenCV, NumPy |
| **Data Export** | Pandas, OpenPyXL |
| **Packaging** | PyInstaller + Inno Setup |

---

## 📸 Screenshots

> *(Add your screenshots here after the MVP is ready)*

| Main Dashboard | Detection Preview | Excel Export |
|----------------|-------------------|--------------|
| *[screenshot]* | *[screenshot]*   | *[screenshot]* |

## License
MIT
