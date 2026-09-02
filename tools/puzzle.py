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
reruns keep any notes already there. The manifest may also hold "ghost"
cards, written by hand for days that were played but never screenshotted
(the page draws these itself); their "name" is a fake filename chosen so
a plain sort drops them between the right neighbours, and reruns keep
them too.

Usage:
    tools/puzzle.py ~/Downloads/puzzle static/art/buenasuerte-assets
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
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
    ap.add_argument("--force", action="store_true", help="reconvert screenshots that already have a JPEG")
    args = ap.parse_args()

    sources = sorted(
        p for p in args.source.iterdir()
        if p.suffix.lower() == ".png" and not p.name.startswith(".")
    )
    if not sources:
        print(f"no screenshots found in {args.source}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)

    # Notes and ghost cards are written into the manifest by hand;
    # carry them across.
    notes = {}
    dates = {}
    ghosts = []
    manifest_path = args.out / "manifest.json"
    if manifest_path.exists():
        old_cards = json.loads(manifest_path.read_text()).get("cards", [])
        notes = {c["name"]: c["note"] for c in old_cards if c.get("note") and not c.get("ghost")}
        dates = {c["name"]: c["date"] for c in old_cards if c.get("date") and not c.get("ghost")}
        ghosts = [c for c in old_cards if c.get("ghost")]

    entries = []
    skipped = 0
    for path in sources:
        out_name = path.stem.lower().replace(" ", "-") + ".jpg"
        out_path = args.out / out_name

        # Incremental: a screenshot that already has its JPEG is only
        # re-read for its manifest entry if forced.
        # The play date: kept from the old manifest once recorded, else
        # read off the screenshot's mtime (the camera roll's timestamp).
        played = dates.get(out_name) or datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()

        if out_path.exists() and not args.force:
            with Image.open(out_path) as done:
                entry = {"name": out_name, "width": done.width, "height": done.height, "date": played}
            if out_name in notes:
                entry["note"] = notes[out_name]
            entries.append(entry)
            skipped += 1
            continue

        img = Image.open(path).convert("RGB")
        w, h = img.size
        # Scale the fixed crop if a screenshot arrives at another size.
        scale = w / 1206
        card = img.crop((0, round(CROP_TOP * scale), w, round(CROP_BOTTOM * scale)))
        card.thumbnail((OUT_WIDTH, OUT_WIDTH * 4), Image.LANCZOS)

        card.save(
            out_path,
            "JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
            progressive=True,
        )
        entry = {"name": out_name, "width": card.width, "height": card.height, "date": played}
        if out_name in notes:
            entry["note"] = notes[out_name]
        entries.append(entry)
        print(f"  {path.name} -> {out_name} ({card.width}x{card.height})")

    merged = sorted(entries + ghosts, key=lambda c: c["name"])
    manifest_path.write_text(json.dumps({"cards": merged}, indent=2) + "\n")
    kept = f" (+ {len(ghosts)} ghost)" if ghosts else ""
    print(f"\n{len(entries)} cards in {args.out} ({len(entries) - skipped} new, {skipped} already done){kept}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
