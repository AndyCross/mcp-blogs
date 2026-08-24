#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pillow>=10.0",
#   "pillow-heif>=0.16",
# ]
# ///
"""
Same Sky photo fitter.

Takes a folder of photos (HEIC/JPEG/PNG), downscales them to web-ready
JPEGs, works out how much of each one is actually sky, and fits each
photo onto a shared skybox:

  - mostly sky            -> "sky" mode, it blends straight into the dome
  - sky over open water   -> "horizon" mode, its own horizon line is
                             pinned to the dome's horizon
  - some sky behind a     -> "polaroid" mode, it gets a white frame and
    person / foreground      floats in the sky instead of merging with it
  - no meaningful sky     -> rejected, reported and skipped

For every accepted photo it computes the mean colour of its sky pixels,
then places it on the dome: deeper blue sits higher, paler sky sits
nearer the horizon, and azimuths are ordered by hue so the skybox
gradient can interpolate smoothly from one photo's sky to the next.

Output: resized JPEGs plus a manifest.json the art page reads.

Usage:
    tools/samesky.py ~/Downloads/samesky static/art/samesky-assets
    tools/samesky.py ~/Downloads/samesky static/art/samesky-assets --report-only
"""

from __future__ import annotations

import argparse
import colorsys
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()

SOURCE_SUFFIXES = {".heic", ".heif", ".jpg", ".jpeg", ".png"}

# Long-edge pixel sizes for the web copies.
SKY_LONG_EDGE = 1600
POLAROID_LONG_EDGE = 1200
JPEG_QUALITY = 72

# Thumbnail size used for the sky analysis. Small on purpose: we want
# broad colour statistics, not detail.
ANALYSIS_EDGE = 256

# Classification thresholds (mean fraction of each column, walking down
# from the top of the frame, that still reads as sky).
SKY_MODE_MIN = 0.70        # this much sky and the photo merges with the dome
POLAROID_MIN = 0.25        # some sky behind a subject -> framed snapshot

# Seascape (horizon mode) detection: the sea must be at least this much
# darker than the sky right above it, sustained and sharp at the line.
HORIZON_MIN_STEP = 14      # 0..255 luma drop across the horizon
HORIZON_MAX_FRAC = 0.80    # horizon lower than this and there is no sea to speak of


@dataclass
class Fit:
    name: str          # output file name
    source: str        # original file name
    mode: str          # "sky" | "horizon" | "polaroid"
    width: int
    height: int
    sky_fraction: float  # mean top-down walk depth across columns
    sky_color: str     # mean colour of the walked sky pixels, hex
    depth: float       # 0 pale/washed .. 1 deep blue
    elevation: float = 0.0  # degrees above horizon, set after placement
    azimuth: float = 0.0    # degrees, set after placement
    horizon: float | None = None  # horizon line as a fraction of frame height from the top
    taken: str | None = None  # capture date, YYYY-MM-DD


@dataclass
class Report:
    fits: list[Fit] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)


def taken_date(path: Path, img: Image.Image) -> str | None:
    """The day the photograph was taken, YYYY-MM-DD.

    EXIF first (DateTimeOriginal, then the plain DateTime); the file's
    own modification time if the camera left nothing behind.
    """
    try:
        exif = img.getexif()
        raw = exif.get(36867) or exif.get(306)
        if not raw:
            ifd = exif.get_ifd(0x8769)
            raw = ifd.get(36867) or ifd.get(36868)
        if raw:
            stamp = str(raw).strip().split(" ")[0].replace(":", "-")
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stamp):
                return stamp
    except Exception:  # noqa: BLE001 - a missing date is not worth failing over
        pass
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return None


def is_sky_pixel(r: int, g: int, b: int) -> bool:
    """A pixel counts as sky if it is blue-dominant, cloud, or pastel dusk."""
    # Blue sky: blue clearly above red, not far below green, and bright
    # enough that it isn't a shadow or dark water.
    if b > r + 12 and b >= g - 6 and b > 90:
        return True
    # Deep zenith blue: a clear sky shot nearly straight up reads navy,
    # well under the brightness floor above, but strongly blue-dominant.
    if b > r + 30 and b > g + 20 and b > 60:
        return True
    # Cloud / haze: bright and nearly grey.
    lo, hi = min(r, g, b), max(r, g, b)
    if lo > 165 and (hi - lo) < 42:
        return True
    # Dusk pastels: warm but bright and gently saturated (sunset bands).
    if hi > 150 and hi > 0 and (hi - lo) / hi < 0.45 and lo > 100:
        return True
    return False


def analyse(img: Image.Image) -> tuple[float, tuple[int, int, int]]:
    """Return (sky_fraction, mean_sky_rgb).

    The sky fraction is a columnar walk: for each column of the (small)
    analysis thumbnail, walk down from the top of the frame while the
    pixels still read as sky, with a little tolerance so a stray branch
    or bird doesn't end the walk. The mean of those walk depths is the
    fraction. This deliberately excludes the sea: blue water below a
    treeline or horizon is never connected to the top of the frame.
    Only walked pixels contribute to the mean sky colour.
    """
    thumb = img.copy()
    thumb.thumbnail((ANALYSIS_EDGE, ANALYSIS_EDGE))
    thumb = thumb.convert("RGB")
    w, h = thumb.size
    px = thumb.load()

    depth_sum = 0
    sky_count = 0
    acc = [0, 0, 0]
    tolerance = max(2, h // 32)  # non-sky pixels a walk may step through
    # Colour is sampled only from the top quarter of the frame: the mean
    # of the whole sky gets dragged grey by pale horizon haze, and the
    # dome should match the blue the photo actually leads with.
    color_cut = max(1, h // 4)

    for x in range(w):
        misses = 0
        depth = 0
        for y in range(h):
            r, g, b = px[x, y]
            if is_sky_pixel(r, g, b):
                misses = 0
                depth = y + 1
                if y < color_cut:
                    sky_count += 1
                    acc[0] += r
                    acc[1] += g
                    acc[2] += b
            else:
                misses += 1
                if misses > tolerance:
                    break
        depth_sum += depth

    if sky_count:
        mean = tuple(c // sky_count for c in acc)
    else:
        # No sky at all; fall back to the overall mean so the caller
        # still gets a colour (it will be rejecting this image anyway).
        stat = thumb.resize((1, 1)).getpixel((0, 0))
        mean = tuple(stat[:3])

    return depth_sum / (w * h) if w and h else 0.0, mean  # type: ignore[return-value]


def find_sea_horizon(img: Image.Image) -> float | None:
    """Detect open water under the sky.

    The column walk in analyse() marches straight through sea (water
    passes the same blue test as sky), so seascapes would otherwise be
    classified as pure sky and hoisted up the dome. This looks for the
    strongest sustained luma drop between two blue-ish regions: sky
    above, darker water below. The drop must also be sharp right at the
    line, which is what separates a horizon from a cloud bank fading
    into blue. Returns the horizon as a fraction of frame height from
    the top, or None if the photo doesn't read as a seascape.
    """
    thumb = img.copy()
    thumb.thumbnail((ANALYSIS_EDGE, ANALYSIS_EDGE))
    thumb = thumb.convert("RGB")
    w, h = thumb.size
    if w < 8 or h < 16:
        return None
    px = thumb.load()

    lum: list[float] = []
    skyish: list[float] = []
    bluish: list[float] = []
    for y in range(h):
        s = 0
        sky_n = 0
        blue_n = 0
        for x in range(w):
            r, g, b = px[x, y]
            s += (r * 299 + g * 587 + b * 114) // 1000
            if is_sky_pixel(r, g, b):
                sky_n += 1
            if b >= r + 4:
                blue_n += 1
        lum.append(s / w)
        skyish.append(sky_n / w)
        bluish.append(blue_n / w)

    win = max(2, h // 24)
    best_y = None
    best_step = 0.0
    for y in range(win, h - win):
        step = sum(lum[y - win:y]) / win - sum(lum[y:y + win]) / win
        if step > best_step:
            best_step, best_y = step, y

    if best_y is None or best_step < HORIZON_MIN_STEP:
        return None
    frac = best_y / h
    if not 0.04 <= frac <= HORIZON_MAX_FRAC:
        return None
    # The line itself must be crisp, not a slow gradient.
    sharp = (lum[max(0, best_y - 2)] + lum[best_y - 1]) / 2 \
        - (lum[best_y] + lum[min(h - 1, best_y + 1)]) / 2
    if sharp < HORIZON_MIN_STEP * 0.5:
        return None
    # Sky above, water below; both have to actually look the part.
    if sum(skyish[:best_y]) / best_y < 0.6:
        return None
    below = bluish[best_y:]
    if sum(below) / len(below) < 0.6:
        return None
    return round(frac, 3)


def blue_depth(rgb: tuple[int, int, int]) -> float:
    """0 for pale, washed-out sky; 1 for deep saturated blue."""
    r, g, b = (c / 255.0 for c in rgb)
    _, lightness, saturation = colorsys.rgb_to_hls(r, g, b)
    # Deep sky = saturated and not too light. Both terms in 0..1.
    depth = saturation * (1.0 - lightness)
    return max(0.0, min(1.0, depth * 2.2))


def classify(sky_fraction: float) -> str | None:
    if sky_fraction >= SKY_MODE_MIN:
        return "sky"
    if sky_fraction >= POLAROID_MIN:
        return "polaroid"
    return None


def place(fits: list[Fit]) -> None:
    """Assign each fit an azimuth and elevation on the dome.

    Azimuths: photos are ordered by the hue/depth of their sky and
    spread evenly around the full circle, so the dome's gradient can
    walk smoothly from the palest sky to the deepest and back.
    Elevation: deeper blue sits higher; polaroids hang lower so they
    read as pinned snapshots rather than patches of the sky itself.
    """
    if not fits:
        return
    ordered = sorted(fits, key=lambda f: f.depth)
    step = 360.0 / len(ordered)
    for i, f in enumerate(ordered):
        f.azimuth = round((i * step) % 360.0, 1)
        if f.mode == "sky":
            f.elevation = round(16.0 + 30.0 * f.depth, 1)
        elif f.mode == "horizon":
            # Straddles the horizon; the page offsets so the photo's
            # own horizon line lands exactly on the dome's.
            f.elevation = 0.0
        else:
            f.elevation = round(8.0 + 12.0 * f.depth, 1)


def process_one(path: Path, out_dir: Path, report: Report, write: bool) -> None:
    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
    except Exception as exc:  # noqa: BLE001 - report and move on
        report.rejected.append((path.name, f"could not read ({exc})"))
        return

    taken = taken_date(path, img)
    sky_fraction, mean_rgb = analyse(img)
    mode = classify(sky_fraction)
    # A seascape trumps the walk-based classes: its own horizon gets
    # pinned to the dome's. This can also rescue a photo the walk
    # rejected (dark water stops the walk early).
    horizon = find_sea_horizon(img)
    if horizon is not None:
        mode = "horizon"
    if mode is None:
        report.rejected.append((path.name, f"only {sky_fraction:.0%} sky from the top"))
        return

    long_edge = POLAROID_LONG_EDGE if mode == "polaroid" else SKY_LONG_EDGE
    resized = img.convert("RGB")
    resized.thumbnail((long_edge, long_edge), Image.LANCZOS)

    out_name = path.stem.lower().replace(" ", "-") + ".jpg"
    if write:
        out_dir.mkdir(parents=True, exist_ok=True)
        resized.save(
            out_dir / out_name,
            "JPEG",
            quality=JPEG_QUALITY,
            optimize=True,
            progressive=True,
        )

    report.fits.append(
        Fit(
            name=out_name,
            source=path.name,
            mode=mode,
            width=resized.width,
            height=resized.height,
            sky_fraction=round(sky_fraction, 3),
            sky_color="#{:02x}{:02x}{:02x}".format(*mean_rgb),
            depth=round(blue_depth(mean_rgb), 3),
            horizon=horizon,
            taken=taken,
        )
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Fit photos of the sky onto a shared skybox.")
    ap.add_argument("source", type=Path, help="folder of HEIC/JPEG/PNG photos")
    ap.add_argument("out", type=Path, help="output folder for JPEGs + manifest.json")
    ap.add_argument("--report-only", action="store_true", help="analyse and report, write nothing")
    args = ap.parse_args()

    sources = sorted(
        p for p in args.source.iterdir()
        if p.suffix.lower() in SOURCE_SUFFIXES and not p.name.startswith(".")
    )
    if not sources:
        print(f"no photos found in {args.source}", file=sys.stderr)
        return 1

    report = Report()
    for path in sources:
        process_one(path, args.out, report, write=not args.report_only)

    place(report.fits)

    if not args.report_only:
        manifest = {
            "photos": [vars(f) for f in sorted(report.fits, key=lambda f: f.azimuth)],
        }
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"{len(report.fits)} fitted, {len(report.rejected)} rejected\n")
    for f in sorted(report.fits, key=lambda f: f.azimuth):
        print(
            f"  {f.source:<18} {f.mode:<8} sky {f.sky_fraction:>4.0%}  "
            f"{f.sky_color}  depth {f.depth:.2f}  "
            f"az {f.azimuth:>5.1f}  el {f.elevation:>4.1f}"
            + (f"  horizon {f.horizon:.0%} down" if f.horizon is not None else "")
            + (f"  {f.taken}" if f.taken else "  (no date)")
        )
    for name, reason in report.rejected:
        print(f"  {name:<18} REJECTED {reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
