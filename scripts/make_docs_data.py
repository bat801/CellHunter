"""Run CellHunter's Cellpose pipeline on the bundled BBBC001 samples.

The results are written to ``.cache/docs-data`` so that the figure script
(``make_docs_figures.py``) does not need to run a neural network again:

  results.json   per-image counts, timings and image metadata
  masks.npz      instance masks produced by Cellpose
  report.xlsx    the same report the desktop app produces

Usage (from the repository root):

    python scripts/make_docs_data.py

The script is intentionally independent of CellHunter.Desktop: it calls the
very same ``analyzer.main`` code path, but caches the masks that the app only
uses internally.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZER_DIR = REPO_ROOT / "src" / "CellHunter.Analyzer"
SAMPLE_DIR = (
    ANALYZER_DIR
    / "examples"
    / "sample_images"
    / "BBBC001_v1_images_tif"
    / "human_ht29_colon_cancer_1_images"
)
MANUAL_COUNTS = ANALYZER_DIR / "examples" / "sample_output" / "BBBC001_v1_counts.txt"
DEFAULT_OUT = REPO_ROOT / ".cache" / "docs-data"


def read_manual_counts(path: Path) -> dict[str, dict[str, int]]:
    """Parse the two manual annotation columns shipped with the sample data."""
    manual: dict[str, dict[str, int]] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.lower().startswith("image"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        values = [int(p) for p in parts[1:] if p.isdigit()]
        if not values:
            continue
        manual[parts[0]] = {
            "manual_1": values[0],
            "manual_2": values[1] if len(values) > 1 else values[0],
        }
    return manual


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, default=SAMPLE_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--model", default="nuclei")
    args = parser.parse_args()

    # Cellpose stores downloaded weights in %USERPROFILE%\.cellpose by default.
    # Keep them inside the workspace instead (see .gitignore).
    os.environ.setdefault(
        "CELLPOSE_LOCAL_MODELS_PATH", str(REPO_ROOT / ".cache" / "cellpose")
    )

    sys.path.insert(0, str(ANALYZER_DIR))
    import cv2
    import numpy as np
    import pandas as pd
    import torch

    from cellpose import models

    images = sorted(p for p in args.images.iterdir() if p.suffix.lower() in {".tif", ".tiff"})
    if not images:
        print(f"No TIFF images in {args.images}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    manual = read_manual_counts(MANUAL_COUNTS)

    print(f"Loading Cellpose '{args.model}' model (CPU)...")
    load_start = time.perf_counter()
    model = models.CellposeModel(model_type=args.model, device=torch.device("cpu"))
    load_seconds = time.perf_counter() - load_start
    print(f"Model ready in {load_seconds:.1f} s")

    masks: dict[str, np.ndarray] = {}
    rows: list[dict] = []
    reference_gray: np.ndarray | None = None

    for index, image_path in enumerate(images, start=1):
        gray = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            print(f"  skip unreadable {image_path.name}", file=sys.stderr)
            continue

        started = time.perf_counter()
        result, _flows, _styles = model.eval(
            gray, diameter=None, channels=[0, 0], do_3D=False
        )
        elapsed = time.perf_counter() - started

        labels = np.asarray(result, dtype=np.uint16)
        masks[image_path.name] = labels
        count = int(labels.max())

        manual_row = manual.get(image_path.name, {})
        rows.append(
            {
                "filename": image_path.name,
                "count": count,
                "width": int(gray.shape[1]),
                "height": int(gray.shape[0]),
                "model": "cellpose",
                "device": "cpu",
                "time_seconds": round(elapsed, 2),
                "manual_1": manual_row.get("manual_1"),
                "manual_2": manual_row.get("manual_2"),
            }
        )

        if reference_gray is None:
            reference_gray = gray

        print(
            f"  [{index}/{len(images)}] {image_path.name}: {count} nuclei "
            f"in {elapsed:.2f} s"
        )

    np.savez_compressed(args.out / "masks.npz", **masks)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cellpose_model": args.model,
        "device": "cpu",
        "cpu_count": os.cpu_count(),
        "model_load_seconds": round(load_seconds, 2),
        "images": rows,
    }
    (args.out / "results.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )

    frame = pd.DataFrame(rows).drop(columns=["manual_1", "manual_2"])
    frame.to_excel(args.out / "report.xlsx", index=False)

    print(f"\nWrote {len(rows)} records to {args.out}")
    print(f"Mean time per image: {np.mean([r['time_seconds'] for r in rows]):.2f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
