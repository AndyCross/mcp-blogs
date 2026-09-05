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

New screenshots arrive in ~/Downloads first. With --collect DIR the
script sweeps that folder before converting: any PNG whose margins are
the puzzle app's green (#038839, sampled at a few fixed spots) is a
score screen and gets moved into the source folder. Other screenshots
are left alone.

Usage:
    tools/puzzle.py ~/puzzle static/art/buenasuerte-assets --collect ~/Downloads
"""

from __future__ import annotations

import argparse
import json
import shutil
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

# The app paints the whole score screen its own green. These spots
# (in 1206x2622 coordinates, scaled for other sizes) sit in the status
# bar, the left margin and the bottom, clear of the white card and any
# text, so they are green on every score screenshot and nothing else.
CORE_GREEN = (2, 135, 56)
GREEN_SPOTS = [(50, 50), (600, 470), (100, 2000), (1100, 600), (600, 2500)]
GREEN_TOLERANCE = 12


def is_score_screen(path: Path) -> bool:
    """True if every sample spot is the app's green."""
    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            w, h = img.size
            if h <= w:  # portrait phone screens only
                return False
            scale = w / 1206
            for x, y in GREEN_SPOTS:
                px = img.getpixel((min(round(x * scale), w - 1), min(round(y * scale), h - 1)))
                if any(abs(a - b) > GREEN_TOLERANCE for a, b in zip(px, CORE_GREEN)):
                    return False
            return True
    except OSError:
        return False


def collect(downloads: Path, dest: Path, dry_run: bool = False) -> list[Path]:
    """Move score screenshots out of downloads into dest. Returns what moved."""
    moved = []
    already = 0
    candidates = sorted(
        p for p in downloads.iterdir()
        if p.is_file() and p.suffix.lower() == ".png" and not p.name.startswith(".")
    )
    for path in candidates:
        if not is_score_screen(path):
            continue
        target = dest / path.name
        if target.exists():
            already += 1
            continue
        print(f"  {'would move' if dry_run else 'move'} {path.name} -> {dest}")
        if not dry_run:
            shutil.move(str(path), str(target))
        moved.append(target)
    if already:
        print(f"  {already} score screenshot(s) in {downloads} already in {dest}, left alone")
    if not moved:
        print(f"  nothing new in {downloads}")
    return moved


def main() -> int:
    ap = argparse.ArgumentParser(description="Crop puzzle score screenshots for the web.")
    ap.add_argument("source", type=Path, help="folder of PNG screenshots")
    ap.add_argument("out", type=Path, help="output folder for JPEGs + manifest.json")
    ap.add_argument("--force", action="store_true", help="reconvert screenshots that already have a JPEG")
    ap.add_argument("--collect", type=Path, metavar="DIR",
                    help="first move any score screenshots found in DIR (e.g. ~/Downloads) into source")
    ap.add_argument("--dry-run", action="store_true", help="with --collect, only report what would move")
    args = ap.parse_args()

    if args.collect:
        args.source.mkdir(parents=True, exist_ok=True)
        print(f"collecting from {args.collect}:")
        collect(args.collect, args.source, dry_run=args.dry_run)
        if args.dry_run:
            return 0

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
