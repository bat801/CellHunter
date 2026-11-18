"""Turn the raw UI captures into the screenshots and demo GIF used by README.

Run ``scripts/capture-ui.ps1`` first; it writes to ``.cache/ui-capture``:

    main.png          the app with a folder selected
    results.png       the app after the analysis finished
    frames/*.png      one frame every 250 ms during the run
    rects.json        bounds of the annotated controls

Usage:

    python scripts/make_docs_screenshots.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / ".cache" / "ui-capture"
OUT = ROOT / "docs" / "images"

FONT_DIR = Path(r"C:\Windows\Fonts")
GREEN = (76, 175, 80)
GREEN_BRIGHT = (110, 214, 122)
DARK = (22, 22, 32)
DARK_SOFT = (30, 30, 46)
MUTED = (150, 160, 176)
TEXT = (240, 242, 247)
LINE = (58, 58, 82)

_FONT_CACHE: dict[tuple[int, str], ImageFont.FreeTypeFont] = {}


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    key = (size, weight)
    if key not in _FONT_CACHE:
        name = {"regular": "segoeui.ttf", "bold": "segoeuib.ttf", "light": "segoeuil.ttf"}[weight]
        _FONT_CACHE[key] = ImageFont.truetype(str(FONT_DIR / name), size)
    return _FONT_CACHE[key]


def progress_fraction(image: Image.Image, rect: dict) -> float:
    """Measure how much of the progress bar is filled (green pixels)."""
    x0 = rect["x"]
    y = rect["y"] + rect["h"] // 2
    row = np.asarray(image.crop((x0, y, x0 + rect["w"], y + 1)).convert("RGB"))
    green = (row[:, :, 1] > 120) & (row[:, :, 0] < 120) & (row[:, :, 2] < 120)
    if not green.any():
        return 0.0
    return float(np.flatnonzero(green)[-1] + 1) / rect["w"]


def badge(draw: ImageDraw.ImageDraw, center: tuple[int, int], number: str) -> None:
    radius = 15
    draw.ellipse(
        [
            center[0] - radius,
            center[1] - radius,
            center[0] + radius,
            center[1] + radius,
        ],
        fill=GREEN,
        outline=DARK,
        width=2,
    )
    draw.text(center, number, font=font(17, "bold"), fill=(255, 255, 255), anchor="mm")


LEGEND = [
    ("1", "Choose the folder", "TIFF, PNG or JPEG"),
    ("2", "Pick a model", "cellpose or yolo"),
    ("3", "Start the analysis", "runs in the background"),
    ("4", "Watch progress", "percent of the folder"),
    ("5", "Read the log", "per-image counts"),
    ("6", "Open the results", "one row per image"),
]


def make_annotated(main: Image.Image, rects: dict) -> Image.Image:
    width = main.size[0]
    legend_height = 232
    canvas = Image.new("RGB", (width, main.size[1] + legend_height), DARK)
    canvas.paste(main, (0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.line([(0, main.size[1] + 1), (width, main.size[1] + 1)], fill=LINE, width=2)

    # Numbered markers on top of the controls they describe.
    positions = {
        "1": (rects["folder"]["x"], rects["folder"]["y"]),
        "2": (rects["model"]["x"], rects["model"]["y"]),
        "3": (rects["start"]["x"], rects["start"]["y"]),
        "4": (rects["progress"]["x"] + 6, rects["progress"]["y"] + rects["progress"]["h"] // 2),
        "5": (rects["logs"]["x"] - 12, rects["logs"]["y"] - 4),
        "6": (rects["results"]["x"], rects["results"]["y"]),
    }
    for number, (x, y) in positions.items():
        badge(draw, (x, y), number)

    # Legend strip below the screenshot.
    top = main.size[1] + 34
    for index, (number, title, subtitle) in enumerate(LEGEND):
        column = index % 3
        row = index // 3
        x = 38 + column * 356
        y = top + row * 84
        badge(draw, (x + 15, y + 16), number)
        draw.text((x + 44, y), title, font=font(19, "bold"), fill=TEXT)
        draw.text((x + 44, y + 27), subtitle, font=font(14), fill=MUTED)

    draw.text(
        (38, main.size[1] + legend_height - 28),
        "The application interface is in Russian; the labels above translate each control.",
        font=font(13),
        fill=(120, 130, 146),
    )
    return canvas


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rects = json.loads((CAPTURE / "rects.json").read_text(encoding="utf-8-sig"))
    window = rects["window"]

    main_image = Image.open(CAPTURE / "main.png").convert("RGB")
    results_image = Image.open(CAPTURE / "results.png").convert("RGB")

    frame_paths = sorted((CAPTURE / "frames").glob("frame_*.png"))
    if not frame_paths:
        raise SystemExit("No frames found - run scripts/capture-ui.ps1 first")

    scored = []
    for path in frame_paths:
        with Image.open(path) as frame:
            rgb = frame.convert("RGB")
            scored.append((path, progress_fraction(rgb, rects["progress"]), rgb.copy()))

    # A mid-run frame: near 55% with some rows already in the table.
    running = min(scored, key=lambda item: abs(item[1] - 0.55))[2]

    main_image.save(OUT / "ui-main.png", optimize=True)
    running.save(OUT / "ui-running.png", optimize=True)
    results_image.save(OUT / "ui-results.png", optimize=True)

    annotated = make_annotated(results_image, rects)
    annotated.save(OUT / "ui-annotated.png", optimize=True)

    # --- demo.gif ---------------------------------------------------------
    width = 880
    height = round(window["h"] * width / window["w"])
    gif_frames: list[Image.Image] = []
    durations: list[int] = []

    idle_kept = 0
    for index, (path, fraction, rgb) in enumerate(scored):
        if fraction <= 0.001 and index > 0:
            # The model takes a few seconds to load; keep only every 3rd
            # frame so the GIF spends its time on the actual progress.
            idle_kept += 1
            if idle_kept % 3:
                continue
            durations.append(90)
        else:
            durations.append(130)

        gif_frames.append(
            rgb.resize((width, height), Image.LANCZOS).quantize(
                colors=128, method=Image.MEDIANCUT, dither=Image.NONE
            )
        )

    # End on the final window with the summary visible (the last capture frame
    # stops mid-scroll), held a little longer so the result can be read.
    gif_frames.append(
        results_image.resize((width, height), Image.LANCZOS).quantize(
            colors=128, method=Image.MEDIANCUT, dither=Image.NONE
        )
    )
    durations.append(1800)

    gif_frames[0].save(
        OUT / "demo.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )

    print(f"  ui-main.png / ui-running.png / ui-results.png / ui-annotated.png")
    print(f"  demo.gif ({len(gif_frames)} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
