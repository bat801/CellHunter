"""Generate every static image used by README.md.

All figures are derived from real data:

* ``.cache/docs-data/results.json`` + ``masks.npz`` — produced by
  ``scripts/make_docs_data.py`` (Cellpose 3.0.7, CPU, default settings);
* ``src/CellHunter.Analyzer/examples/sample_images`` — the original BBBC001
  TIFF files;
* ``.cache/docs-data/report.xlsx`` — the report the desktop app writes.

Usage (from the repository root, with the docs environment active):

    python scripts/make_docs_figures.py
    python scripts/make_docs_figures.py --only banner,charts
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"
DATA = ROOT / ".cache" / "docs-data"
SAMPLE = (
    ROOT
    / "src"
    / "CellHunter.Analyzer"
    / "examples"
    / "sample_images"
    / "BBBC001_v1_images_tif"
    / "human_ht29_colon_cancer_1_images"
)
REPORT = DATA / "report.xlsx"

FONT_DIR = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
FONT_FILES = {
    "regular": "segoeui.ttf",
    "bold": "segoeuib.ttf",
    "light": "segoeuil.ttf",
    "mono": "consola.ttf",
    "mono_bold": "consolab.ttf",
}

# Palette shared with the WPF application (MainWindow.xaml).
DARK_BG_TOP = (16, 16, 24)
DARK_BG_BOTTOM = (30, 30, 46)
PANEL = (38, 38, 58)
PANEL_SOFT = (45, 45, 68)
GREEN = (76, 175, 80)
GREEN_BRIGHT = (110, 214, 122)
GREEN_DARK = (34, 90, 42)
BLUE = (52, 152, 219)
TEXT = (240, 242, 247)
MUTED = (156, 166, 182)
LINE_DARK = (58, 58, 82)
PAPER = (255, 255, 255)
PAPER_SOFT = (247, 249, 251)
INK = (30, 30, 46)
INK_MUTED = (110, 120, 136)
GRID = (226, 232, 240)

_FONT_CACHE: dict[tuple[int, str], ImageFont.FreeTypeFont] = {}


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    key = (size, weight)
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = ImageFont.truetype(
            str(FONT_DIR / FONT_FILES[weight]), size
        )
    return _FONT_CACHE[key]


def text_width(text: str, fnt: ImageFont.FreeTypeFont, tracking: int = 0) -> float:
    if tracking == 0:
        return fnt.getlength(text)
    return sum(fnt.getlength(ch) for ch in text) + tracking * max(len(text) - 1, 0)


def draw_tracked(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    tracking: float = 2.0,
) -> float:
    """Draw letterspaced text (for small uppercase labels). Returns width."""
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=fnt, fill=fill)
        x += fnt.getlength(char) + tracking
    return x - xy[0]


def draw_paragraph_center(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    top: float,
    lines: list[str],
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    spacing: int = 8,
) -> None:
    y = top
    for line in lines:
        draw.text((center_x, y), line, font=fnt, fill=fill, anchor="ma")
        y += fnt.size + spacing


def vertical_gradient(size: tuple[int, int], top, bottom) -> Image.Image:
    width, height = size
    ramp = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None, None]
    top_arr = np.array(top, dtype=np.float32)[None, None, :]
    bottom_arr = np.array(bottom, dtype=np.float32)[None, None, :]
    column = top_arr * (1 - ramp) + bottom_arr * ramp
    array = np.repeat(column, width, axis=1)
    return Image.fromarray(array.astype(np.uint8), "RGB")


def add_glow(
    canvas: Image.Image,
    center: tuple[float, float],
    radius: float,
    color: tuple[int, int, int],
    strength: float = 0.35,
) -> Image.Image:
    width, height = canvas.size
    yy, xx = np.mgrid[0:height, 0:width]
    distance = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2) / radius
    alpha = np.clip(1.0 - distance, 0.0, 1.0) ** 2.2 * strength
    tint = Image.new("RGB", canvas.size, color)
    mask = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    return Image.composite(tint, canvas, mask)


def rounded(image: Image.Image, radius: int) -> Image.Image:
    rgba = image.convert("RGBA")
    mask = Image.new("L", rgba.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, rgba.size[0] - 1, rgba.size[1] - 1], radius=radius, fill=255
    )
    rgba.putalpha(mask)
    return rgba


def load_json() -> dict:
    return json.loads((DATA / "results.json").read_text(encoding="utf-8"))


def load_masks() -> dict[str, np.ndarray]:
    with np.load(DATA / "masks.npz") as bundle:
        return {name: bundle[name] for name in bundle.files}


def gray_image(name: str) -> np.ndarray:
    image = cv2.imread(str(SAMPLE / name), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise SystemExit(f"Cannot read {SAMPLE / name}")
    return image


def render_overlay(
    gray: np.ndarray,
    labels: np.ndarray,
    size: int,
    boundary=(92, 220, 128),
    centroid=(255, 238, 150),
    thickness: int = 1,
) -> Image.Image:
    """Draw Cellpose boundaries and centroids over the original grayscale."""
    rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    # cv2.findContours needs 8-bit input, so each instance mask is traced
    # separately (labels may exceed 255 in general).
    for label_id in range(1, int(labels.max()) + 1):
        instance = (labels == label_id).astype(np.uint8)
        contours, _ = cv2.findContours(
            instance, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if contours:
            cv2.drawContours(
                rgb, contours, -1, boundary, thickness, lineType=cv2.LINE_AA
            )

    ids = labels.ravel()
    ys, xs = np.indices(labels.shape)
    counts = np.bincount(ids, minlength=int(labels.max()) + 1)
    sum_x = np.bincount(ids, weights=xs.ravel(), minlength=int(labels.max()) + 1)
    sum_y = np.bincount(ids, weights=ys.ravel(), minlength=int(labels.max()) + 1)
    for label_id in range(1, len(counts)):
        if counts[label_id] < 20:
            continue
        point = (
            int(round(sum_x[label_id] / counts[label_id])),
            int(round(sum_y[label_id] / counts[label_id])),
        )
        cv2.circle(rgb, point, 1, centroid, -1, lineType=cv2.LINE_AA)

    image = Image.fromarray(rgb)
    if size != image.size[0]:
        image = image.resize((size, size), Image.LANCZOS)
    return image


def crop_square(gray: np.ndarray, side: int, center_xy=None) -> np.ndarray:
    height, width = gray.shape
    if center_xy is None:
        center_xy = (width // 2, height // 2)
    left = int(center_xy[0] - side / 2)
    top = int(center_xy[1] - side / 2)
    left = max(0, min(left, width - side))
    top = max(0, min(top, height - side))
    return gray[top : top + side, left : left + side]


# --------------------------------------------------------------------------- #
# Individual figures
# --------------------------------------------------------------------------- #


def make_banner(payload: dict, masks: dict[str, np.ndarray]) -> None:
    width, height = 1600, 440
    canvas = vertical_gradient((width, height), DARK_BG_TOP, DARK_BG_BOTTOM)
    canvas = add_glow(canvas, (1330, 220), 460, GREEN, 0.30)

    draw = ImageDraw.Draw(canvas)
    for x in range(0, width, 44):
        draw.line([(x, 0), (x, height)], fill=(27, 27, 41))
    for y in range(0, height, 44):
        draw.line([(0, y), (width, y)], fill=(27, 27, 41))

    # Hero image: a real BBBC001 field with Cellpose boundaries.
    name = "AS_09125_050118150001_A03f04d0.tif"
    gray = crop_square(gray_image(name), 330, (250, 250))
    overlay = render_overlay(gray, crop_labels(masks[name], (250, 250), 330), 400)

    photo = rounded(overlay, 26)
    photo_x, photo_y = 1140, 20
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [photo_x - 10, photo_y + 10, photo_x + 410, photo_y + 420],
        radius=32,
        fill=(0, 0, 0, 140),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow)
    canvas.paste(photo, (photo_x, photo_y), photo)

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        [photo_x, photo_y, photo_x + 399, photo_y + 399],
        radius=26,
        outline=(96, 106, 132),
        width=2,
    )

    draw_tracked(
        draw,
        (84, 74),
        "OPEN SOURCE  ·  WINDOWS DESKTOP  ·  CELLPOSE",
        font(14, "bold"),
        GREEN_BRIGHT,
        tracking=2.6,
    )
    draw.text((80, 104), "CellHunter", font=font(96, "bold"), fill=TEXT)
    draw.text(
        (84, 226),
        "Automated nuclei counting",
        font=font(31, "light"),
        fill=(206, 212, 224),
    )
    draw.text(
        (84, 268),
        "for microscopy images",
        font=font(31, "light"),
        fill=(206, 212, 224),
    )
    draw.line([(86, 330), (226, 330)], fill=GREEN, width=4)
    draw.text(
        (84, 352),
        "Pick a folder, press Start, get an Excel report.",
        font=font(19),
        fill=MUTED,
    )

    canvas.convert("RGB").save(OUT / "banner.png", optimize=True)
    print("  banner.png")


def crop_labels(labels: np.ndarray, center_xy, side: int) -> np.ndarray:
    height, width = labels.shape
    left = max(0, min(int(center_xy[0] - side / 2), width - side))
    top = max(0, min(int(center_xy[1] - side / 2), height - side))
    return labels[top : top + side, left : left + side]


def make_overview(payload: dict, masks: dict[str, np.ndarray]) -> None:
    width, height = 1800, 640
    canvas = vertical_gradient((width, height), DARK_BG_TOP, DARK_BG_BOTTOM)
    draw = ImageDraw.Draw(canvas)

    cards = [
        (60, "INPUT", "1  Folder of images", "TIFF · PNG · JPEG"),
        (650, "SEGMENTATION", "2  Nuclei are detected", "Cellpose nuclei model"),
        (1240, "REPORT", "3  Counts are exported", "Excel · one row per image"),
    ]
    for x, _tag, _title, _sub in cards:
        draw.rounded_rectangle(
            [x, 40, x + 500, 600], radius=20, fill=PANEL, outline=LINE_DARK, width=2
        )

    name = "AS_09125_050118150001_A03f02d0.tif"
    gray = gray_image(name)
    labels = masks[name]

    raw = Image.fromarray(gray).convert("RGB").resize((430, 430), Image.LANCZOS)
    canvas.paste(raw, (95, 75))

    overlay = render_overlay(gray, labels, 430)
    canvas.paste(overlay, (685, 75))

    # "nuclei" badge over the segmentation card
    badge_text = f"{int(labels.max())} nuclei"
    badge_font = font(17, "bold")
    badge_w = text_width(badge_text, badge_font) + 48
    badge_right = 1100
    draw.rounded_rectangle(
        [badge_right - badge_w, 90, badge_right, 130], radius=20, fill=(22, 42, 28)
    )
    draw.ellipse([badge_right - badge_w + 14, 104, badge_right - badge_w + 26, 116], fill=GREEN_BRIGHT)
    draw.text(
        (badge_right - badge_w + 34, 98), badge_text, font=badge_font, fill=GREEN_BRIGHT
    )

    draw_excel_card(canvas, draw, 1275, 75, 430, 430, payload)

    for x, tag, title, sub in cards:
        draw_tracked(draw, (x + 35, 518), tag, font(12, "bold"), MUTED, tracking=2.2)
        draw.text((x + 35, 540), title, font=font(21, "bold"), fill=TEXT)
        draw.text((x + 35, 572), sub, font=font(15), fill=MUTED)

    for arrow_x in (587, 1177):
        draw.line([(arrow_x - 13, 285), (arrow_x + 14, 285)], fill=GREEN, width=3)
        draw.polygon(
            [(arrow_x + 14, 285), (arrow_x + 1, 277), (arrow_x + 1, 293)], fill=GREEN
        )

    canvas.convert("RGB").save(OUT / "overview.png", optimize=True)
    print("  overview.png")


def draw_excel_card(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    payload: dict,
) -> None:
    draw.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=PAPER_SOFT)
    draw.rounded_rectangle([x, y, x + w, y + 52], radius=12, fill=(33, 115, 70))
    draw.rectangle([x, y + 38, x + w, y + 52], fill=(33, 115, 70))
    draw.text(
        (x + 18, y + 13),
        "cellhunter_report.xlsx",
        font=font(16, "bold"),
        fill=PAPER,
    )

    headers = ["Image", "Nuclei", "Time, s"]
    col_x = [x + 18, x + 258, x + 340]
    top = y + 72
    draw.text((col_x[0], top), headers[0], font=font(14, "bold"), fill=INK_MUTED)
    draw.text((col_x[1], top), headers[1], font=font(14, "bold"), fill=INK_MUTED)
    draw.text((col_x[2], top), headers[2], font=font(14, "bold"), fill=INK_MUTED)
    draw.line([(x + 18, top + 26), (x + w - 18, top + 26)], fill=GRID, width=2)

    row_y = top + 38
    for index, row in enumerate(payload["images"]):
        if index % 2 == 0:
            draw.rectangle([x + 10, row_y - 6, x + w - 10, row_y + 32], fill=(234, 242, 236))
        short = f"A03f{index:02d}d0.tif"
        draw.text((col_x[0], row_y), short, font=font(14, "mono"), fill=INK)
        draw.text(
            (col_x[1], row_y), str(row["count"]), font=font(15, "bold"), fill=(30, 110, 60)
        )
        draw.text(
            (col_x[2], row_y),
            f"{row['time_seconds']:.1f}",
            font=font(14, "mono"),
            fill=INK_MUTED,
        )
        row_y += 38

    draw.line([(x + 10, y + h - 42), (x + w - 10, y + h - 42)], fill=GRID, width=2)
    draw.text(
        (x + 18, y + h - 32),
        "Sheet1",
        font=font(14, "bold"),
        fill=(33, 115, 70),
    )
    draw.rectangle([x + 16, y + h - 3, x + 70, y + h], fill=(33, 115, 70))


def make_detection(payload: dict, masks: dict[str, np.ndarray]) -> None:
    name = "AS_09125_050118150001_A03f00d0.tif"
    gray = gray_image(name)
    labels = masks[name]

    before = Image.fromarray(gray).convert("RGB").resize((900, 900), Image.LANCZOS)
    before.save(OUT / "detection-before.png", optimize=True)

    after = render_overlay(gray, labels, 900, thickness=1)
    after.save(OUT / "detection-after.png", optimize=True)
    print("  detection-before.png / detection-after.png")


def _mpl():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "Segoe UI",
            "font.size": 12,
            "axes.edgecolor": "#CBD5E1",
            "axes.labelcolor": "#334155",
            "text.color": "#1E293B",
            "xtick.color": "#475569",
            "ytick.color": "#475569",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    return plt


def make_charts(payload: dict) -> None:
    plt = _mpl()
    images = payload["images"]
    labels_x = [f"{index + 1}" for index in range(len(images))]
    manual_1 = [row["manual_1"] for row in images]
    manual_2 = [row["manual_2"] for row in images]
    automatic = [row["count"] for row in images]

    fig, ax = plt.subplots(figsize=(11.0, 4.9), dpi=150)
    x = np.arange(len(images))
    width = 0.26

    ax.bar(x - width, manual_1, width, label="Annotator 1", color="#B8CCE0")
    ax.bar(x, manual_2, width, label="Annotator 2", color="#7FA6C9")
    bars = ax.bar(x + width, automatic, width, label="CellHunter (Cellpose)", color="#4CAF50")

    for rect in bars:
        ax.annotate(
            f"{int(rect.get_height())}",
            (rect.get_x() + rect.get_width() / 2, rect.get_height()),
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
            color="#1B5E20",
            xytext=(0, 3),
            textcoords="offset points",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels_x, fontsize=12)
    ax.set_xlabel("Image (six fields from the BBBC001 sample set)", labelpad=10)
    ax.set_ylabel("Nuclei per image")
    ax.set_ylim(0, 620)
    ax.set_title(
        "Nuclei counts: CellHunter vs. two manual annotations",
        fontsize=17,
        fontweight="bold",
        loc="left",
        pad=26,
    )
    ax.text(
        0.0,
        1.045,
        "Cellpose 3.0.7 · nuclei model · default settings · 512×512 px",
        transform=ax.transAxes,
        fontsize=10.5,
        color="#64748B",
    )
    ax.legend(frameon=False, loc="upper right", ncol=1, fontsize=11)
    ax.grid(axis="y", color="#E8EDF3", linewidth=1)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    fig.text(
        0.01,
        0.012,
        "Manual counts: examples/sample_output/BBBC001_v1_counts.txt. Dense, low-contrast fields "
        "are under-counted at default settings; see Known limitations.",
        fontsize=8.5,
        color="#8492A6",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "chart-counts.png", dpi=150)
    plt.close(fig)

    # --- timing -----------------------------------------------------------
    times = [row["time_seconds"] for row in images]
    mean_time = float(np.mean(times))

    fig, ax = plt.subplots(figsize=(7.6, 4.0), dpi=150)
    y = np.arange(len(images))[::-1]
    ax.barh(y, times, height=0.58, color="#4CAF50")
    for yi, value in zip(y, times):
        ax.text(value + 0.03, yi, f"{value:.2f} s", va="center", fontsize=11, color="#1B5E20")
    ax.axvline(mean_time, color="#94A3B8", linestyle=(0, (3, 3)), linewidth=1.4, zorder=0)
    ax.text(
        mean_time + 0.04,
        -0.78,
        f"mean {mean_time:.2f} s",
        fontsize=10,
        color="#64748B",
        clip_on=False,
    )
    ax.set_yticks(y)
    ax.set_yticklabels(labels_x, fontsize=11)
    ax.set_xlabel("Seconds per 512×512 image")
    ax.set_xlim(0, 1.9)
    ax.set_title(
        "Processing time on a laptop CPU",
        fontsize=15,
        fontweight="bold",
        loc="left",
        pad=24,
    )
    ax.text(
        0.0,
        1.05,
        "12-core CPU · no GPU · one-time model load 3.9 s",
        transform=ax.transAxes,
        fontsize=9.5,
        color="#64748B",
    )
    ax.grid(axis="x", color="#E8EDF3", linewidth=1)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "chart-timing.png", dpi=150)
    plt.close(fig)
    print("  chart-counts.png / chart-timing.png")


def make_steps() -> None:
    width, height = 1800, 300
    canvas = Image.new("RGB", (width, height), (247, 249, 251))
    draw = ImageDraw.Draw(canvas)

    items = [
        ("1", "Choose a folder", ["Point CellHunter at a folder of", "TIFF, PNG or JPEG images."]),
        ("2", "Press Start", ["Cellpose finds every nucleus", "and counts it automatically."]),
        ("3", "Open the report", ["An Excel file appears next to", "your images, one row per file."]),
    ]
    centers = [300, 900, 1500]

    draw.line([(340, 92), (1460, 92)], fill=(205, 220, 212), width=3)
    for center, (number, title, description) in zip(centers, items):
        draw.ellipse(
            [center - 46, 46, center + 46, 138], fill=GREEN, outline=(255, 255, 255), width=6
        )
        draw.text((center, 92), number, font=font(40, "bold"), fill=(255, 255, 255), anchor="mm")
        draw.text((center, 162), title, font=font(27, "bold"), fill=INK, anchor="ma")
        draw_paragraph_center(
            draw, center, 202, description, font(17), INK_MUTED, spacing=6
        )
    canvas.save(OUT / "steps.png", optimize=True)
    print("  steps.png")


WORKFLOW_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="400" \
viewBox="0 0 1400 400" role="img" \
aria-label="CellHunter workflow: image folder, Cellpose segmentation, nuclei count, Excel report">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" \
markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#4CAF50"/>
    </marker>
    <style>
      .card   { fill:#F6F8FA; stroke:#E2E8F0; stroke-width:2; }
      .title  { font:600 18px 'Segoe UI', Arial, sans-serif; fill:#1E1E2E; }
      .desc   { font:400 13.5px 'Segoe UI', Arial, sans-serif; fill:#5B6779; }
      .step   { font:700 12px 'Segoe UI', Arial, sans-serif; fill:#7A879A; \
letter-spacing:2px; }
      .band   { fill:#EEF6EF; stroke:#D5E8D8; stroke-width:2; }
      .bandtx { font:400 14px 'Segoe UI', Arial, sans-serif; fill:#2F5D3A; }
      .accent { fill:none; stroke:#4CAF50; stroke-width:3; stroke-linejoin:round; }
      .fill   { fill:#4CAF50; }
      .thin   { fill:none; stroke:#8FD19B; stroke-width:2; }
    </style>
  </defs>

  <rect width="1400" height="400" fill="#FFFFFF"/>

  <!-- 1. folder -->
  <rect class="card" x="50" y="70" width="280" height="170" rx="18"/>
  <text class="step" x="78" y="102">STEP 1</text>
  <path class="accent" d="M78 130 h32 l10 12 h44 a8 8 0 0 1 8 8 v30 a8 8 0 0 1 -8 8 \
h-86 a8 8 0 0 1 -8 -8 v-42 a8 8 0 0 1 8 -8 z"/>
  <text class="title" x="78" y="212">Folder of images</text>
  <text class="desc" x="78" y="236">TIFF, PNG or JPEG, 2D microscopy</text>

  <line x1="336" y1="155" x2="388" y2="155" stroke="#4CAF50" stroke-width="3" \
marker-end="url(#arrow)"/>

  <!-- 2. cellpose -->
  <rect class="card" x="400" y="70" width="280" height="170" rx="18"/>
  <text class="step" x="428" y="102">STEP 2</text>
  <circle class="accent" cx="456" cy="140" r="22"/>
  <circle class="fill" cx="450" cy="134" r="5"/>
  <circle class="thin" cx="486" cy="164" r="22"/>
  <circle class="fill" cx="481" cy="159" r="5"/>
  <text class="title" x="428" y="212">Cellpose segmentation</text>
  <text class="desc" x="428" y="236">Nuclei model · runs on CPU or CUDA</text>

  <line x1="686" y1="155" x2="738" y2="155" stroke="#4CAF50" stroke-width="3" \
marker-end="url(#arrow)"/>

  <!-- 3. count -->
  <rect class="card" x="750" y="70" width="280" height="170" rx="18"/>
  <text class="step" x="778" y="102">STEP 3</text>
  <g class="accent">
    <circle cx="798" cy="132" r="7"/><circle cx="822" cy="146" r="7"/>
    <circle cx="794" cy="162" r="7"/><circle cx="824" cy="174" r="7"/>
    <circle cx="850" cy="134" r="7"/><circle cx="854" cy="164" r="7"/>
  </g>
  <text class="title" x="778" y="212">Count and measure</text>
  <text class="desc" x="778" y="236">One count per image, in seconds</text>

  <line x1="1036" y1="155" x2="1088" y2="155" stroke="#4CAF50" stroke-width="3" \
marker-end="url(#arrow)"/>

  <!-- 4. excel -->
  <rect class="card" x="1100" y="70" width="280" height="170" rx="18"/>
  <text class="step" x="1128" y="102">STEP 4</text>
  <rect class="accent" x="1128" y="122" width="64" height="52" rx="6"/>
  <line class="accent" x1="1128" y1="140" x2="1192" y2="140"/>
  <line class="accent" x1="1150" y1="122" x2="1150" y2="174"/>
  <line class="accent" x1="1170" y1="122" x2="1170" y2="174"/>
  <text class="title" x="1128" y="212">Excel report</text>
  <text class="desc" x="1128" y="236">filename, count, size, model, time</text>

  <!-- technology band -->
  <rect class="band" x="50" y="290" width="1330" height="62" rx="14"/>
  <text class="bandtx" x="76" y="327">CellHunter.Desktop (WPF)  →  analyzer.main (Python)  →  \
Cellpose  →  openpyxl  ·  the UI streams progress and shows the result table live</text>
</svg>
"""


def make_workflow() -> None:
    (OUT / "workflow.svg").write_text(WORKFLOW_SVG, encoding="utf-8")
    print("  workflow.svg")


ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" \
viewBox="0 0 512 512" role="img" aria-label="CellHunter icon: a nucleus with a nucleolus">
  <rect width="512" height="512" rx="116" fill="#4CAF50"/>
  <circle cx="222" cy="300" r="128" fill="none" stroke="#12251A" stroke-width="34"/>
  <circle cx="222" cy="300" r="34" fill="#12251A"/>
  <circle cx="366" cy="158" r="48" fill="none" stroke="#12251A" stroke-width="26"/>
</svg>
"""


def make_icon() -> None:
    (OUT / "icon.svg").write_text(ICON_SVG, encoding="utf-8")

    size = 1024
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=232, fill=GREEN)
    draw.ellipse([188, 344, 700, 856], outline=(18, 37, 26), width=68)
    draw.ellipse([376, 532, 512, 668], fill=(18, 37, 26))
    draw.ellipse([620, 200, 760, 340], outline=(18, 37, 26), width=44)

    canvas.resize((512, 512), Image.LANCZOS).save(OUT / "icon.png", optimize=True)
    ico_path = OUT / "app.ico"
    canvas.save(
        ico_path,
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("  icon.svg / icon.png / app.ico")


def make_social_preview(payload: dict, masks: dict[str, np.ndarray]) -> None:
    width, height = 1280, 640
    canvas = vertical_gradient((width, height), DARK_BG_TOP, DARK_BG_BOTTOM)
    canvas = add_glow(canvas, (1030, 300), 420, GREEN, 0.28)
    draw = ImageDraw.Draw(canvas)

    name = "AS_09125_050118150001_A03f04d0.tif"
    gray = crop_square(gray_image(name), 340, (250, 250))
    overlay = render_overlay(gray, crop_labels(masks[name], (250, 250), 340), 420)
    photo = rounded(overlay, 24)
    canvas.paste(photo, (770, 110), photo)
    draw.rounded_rectangle([770, 110, 1189, 529], radius=24, outline=(88, 96, 120), width=2)

    draw_tracked(
        draw, (72, 96), "OPEN SOURCE  ·  WINDOWS  ·  CELLPOSE", font(13, "bold"), GREEN_BRIGHT, 2.4
    )
    draw.text((68, 126), "CellHunter", font=font(78, "bold"), fill=TEXT)
    draw.text(
        (72, 234),
        "Automated nuclei counting",
        font=font(28, "light"),
        fill=(206, 212, 224),
    )
    draw.text((72, 272), "for microscopy images", font=font(28, "light"), fill=(206, 212, 224))
    draw.text(
        (72, 340),
        "Pick a folder → press Start → Excel report",
        font=font(18),
        fill=MUTED,
    )
    draw.text((72, 486), "github.com/bat801/CellHunter", font=font(19, "mono"), fill=GREEN_BRIGHT)

    canvas.convert("RGB").save(OUT / "social-preview.png", optimize=True)
    print("  social-preview.png")


def make_report_preview(payload: dict) -> None:
    from openpyxl import load_workbook

    workbook = load_workbook(REPORT)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    header, body = rows[0], rows[1:]

    width, height = 1500, 580
    canvas = Image.new("RGB", (width, height), PAPER_SOFT)
    draw = ImageDraw.Draw(canvas)

    stamp = payload["generated_at"].replace("-", "").replace(":", "").replace("T", "_")
    draw.text((48, 34), f"cellhunter_report_{stamp}.xlsx", font=font(19, "mono"), fill=INK_MUTED)
    badge = "XLSX"
    badge_font = font(13, "bold")
    badge_w = text_width(badge, badge_font) + 24
    draw.rounded_rectangle([width - 48 - badge_w, 30, width - 48, 62], radius=8, fill=(33, 115, 70))
    draw.text((width - 48 - badge_w + 12, 36), badge, font=badge_font, fill=PAPER)

    card = [48, 92, width - 48, 470]
    draw.rounded_rectangle(card, radius=10, fill=PAPER, outline=(226, 232, 240), width=2)

    columns = [
        ("filename", 500),
        ("count", 120),
        ("width", 120),
        ("height", 120),
        ("model", 170),
        ("device", 140),
        ("time_seconds", 186),
    ]
    x_positions = []
    cursor = card[0] + 24
    for _name, col_width in columns:
        x_positions.append(cursor)
        cursor += col_width

    header_top = card[1] + 1
    draw.rectangle([card[0] + 2, header_top, card[2] - 2, header_top + 54], fill=(33, 115, 70))
    for (label, _w), x in zip(columns, x_positions):
        draw.text((x, header_top + 16), label, font=font(15, "bold"), fill=PAPER)

    row_y = header_top + 66
    for index, row in enumerate(body):
        if index % 2 == 0:
            draw.rectangle([card[0] + 2, row_y - 8, card[2] - 2, row_y + 44], fill=(240, 246, 242))
        for column_index, value in enumerate(row):
            x = x_positions[column_index]
            text = str(value)
            if column_index == 0:
                draw.text((x, row_y), text, font=font(15, "mono"), fill=INK)
            elif column_index in (1, 4, 5):
                draw.text((x, row_y), text, font=font(16, "bold" if column_index == 1 else "regular"), fill=INK)
            else:
                draw.text((x, row_y), text, font=font(15, "mono"), fill=INK_MUTED)
        row_y += 52
        draw.line([(card[0] + 14, row_y - 8), (card[2] - 14, row_y - 8)], fill=(235, 240, 245), width=1)

    draw.line([(card[0] + 14, 486), (card[2] - 14, 486)], fill=(226, 232, 240), width=2)
    draw.text((card[0] + 20, 500), "Sheet1", font=font(15, "bold"), fill=(33, 115, 70))
    draw.rectangle([card[0] + 18, 530, card[0] + 78, 534], fill=(33, 115, 70))

    canvas.save(OUT / "report-preview.png", optimize=True)
    print("  report-preview.png")


TASKS = {
    "banner": make_banner,
    "overview": make_overview,
    "detection": make_detection,
    "charts": lambda payload, masks: make_charts(payload),
    "steps": lambda payload, masks: make_steps(),
    "workflow": lambda payload, masks: make_workflow(),
    "icon": lambda payload, masks: make_icon(),
    "social": make_social_preview,
    "report": lambda payload, masks: make_report_preview(payload),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        default="",
        help="comma-separated subset: " + ", ".join(TASKS),
    )
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    payload = load_json()
    masks = load_masks()

    selected = [name.strip() for name in args.only.split(",") if name.strip()]
    if not selected:
        selected = list(TASKS)
    unknown = [name for name in selected if name not in TASKS]
    if unknown:
        raise SystemExit(f"Unknown task(s): {', '.join(unknown)}")

    for name in selected:
        TASKS[name](payload, masks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
