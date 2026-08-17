#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pillow>=10.0",
# ]
# ///
"""
Puzzle score fitter.

Takes a folder of iPhone screenshots of the daily word puzzle's score
screen (all the same 1206x2622 layout) and crops each one down to the
part that matters: the puzzle title, the timer, and the streak. The
status bar, logo and buttons go. Output is a folder of web-ready JPEGs
plus a manifest.json the art page reads.

Screenshots are processed in filename order, which for a camera roll
is chronological, so the manifest preserves the order the puzzles
were played.

Cards may carry a handwritten "note" in the manifest (added by hand);
reruns keep any notes already there.

Usage:
    tools/puzzle.py ~/Downloads/puzzle static/art/buenasuerte-assets
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

# The score screen is a fixed layout. These bounds keep the puzzle
# title at the top, the big timer in the middle, and the hints /
# streak / longest row at the bottom.
CROP_TOP = 470
CROP_BOTTOM = 1460
OUT_WIDTH = 720
JPEG_QUALITY = 78


def main() -> int:
    ap = argparse.ArgumentParser(description="Crop puzzle score screenshots for the web.")
    ap.add_argument("source", type=Path, help="folder of PNG screenshots")
    ap.add_argument("out", type=Path, help="output folder for JPEGs + manifest.json")
    args = ap.parse_args()

    sources = sorted(
        p for p in args.source.iterdir()
        if p.suffix.lower() == ".png" and not p.name.startswith(".")
    )
    if not sources:
        print(f"no screenshots found in {args.source}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)

    # Notes are written into the manifest by hand; carry them across.
    notes = {}
    manifest_path = args.out / "manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        notes = {c["name"]: c["note"] for c in old.get("cards", []) if c.get("note")}

    entries = []
    for path in sources:
        img = Image.open(path).convert("RGB")
        w, h = img.size
        # Scale the fixed crop if a screenshot arrives at another size.
        scale = w / 1206
        card = img.crop((0, round(CROP_TOP * scale), w, round(CROP_BOTTOM * scale)))
        card.thumbnail((OUT_WIDTH, OUT_WIDTH * 4), Image.LANCZOS)

        out_name = path.stem.lower().replace(" ", "-") + ".jpg"
        card.save(
            args.out / out_name,
            "JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
            progressive=True,
        )
        entry = {"name": out_name, "width": card.width, "height": card.height}
        if out_name in notes:
            entry["note"] = notes[out_name]
        entries.append(entry)
        print(f"  {path.name} -> {out_name} ({card.width}x{card.height})")

    manifest_path.write_text(json.dumps({"cards": entries}, indent=2) + "\n")
    print(f"\n{len(entries)} cards written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
