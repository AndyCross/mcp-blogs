---
name: samesky
description: Update the Same Sky art page with new sky photos. Use when the user wants to add photos to the sky dome, refresh the samesky assets, or rerun the sky fitter.
---

# Same Sky dome

The art page at `static/art/samesky.html` is a walkable sky dome stitched
from photographs of the sky taken in different places. Sky-heavy photos
feather straight into the dome; seascapes (sky over open water) get their
own horizon line pinned to the dome's horizon; photos with a subject in
front of some sky float as white-framed polaroids; photos with no
meaningful sky are rejected. This skill adds new photos and rebuilds the
assets.

## Adding new photos

1. Source photos (HEIC/JPEG/PNG) live in `~/Downloads/samesky/`. Ask
   where they are if unclear. New photos go in the SAME folder as the
   old ones: the fitter always reprocesses the whole folder and rebuilds
   the manifest from scratch, respreading azimuths around the full
   circle ordered by sky depth.
2. Run the fitter:

   ```
   tools/samesky.py ~/Downloads/samesky static/art/samesky-assets
   ```

   It prints one line per photo (mode, sky %, colour, depth, placement)
   and lists any rejections with the reason. Use `--report-only` first
   if you just want to see how a photo will classify without writing
   anything.

   Keep it token-cheap: don't Read the source HEICs or output JPEGs;
   the printed report tells you everything about how each photo fitted.
3. Mirror to the built site (Hugo copies static/ verbatim at build, but
   the repo keeps `public/` in sync by hand):

   ```
   rsync -a --delete static/art/samesky-assets/ public/art/samesky-assets/
   cp static/art/samesky.html public/art/samesky.html
   ```

4. Report the outcome to the user: which photos went in as sky vs
   polaroid, and any rejections with their reasons so they can decide
   whether to retake or drop them.

## Limits and knobs

- There is no photo cap: the page compiles its dome shader at load time
  with uniform arrays sized to the manifest, so any number of photos
  works without touching the HTML.
- Classification thresholds live at the top of `tools/samesky.py`
  (`SKY_MODE_MIN`, `POLAROID_MIN`, and `HORIZON_MIN_STEP` /
  `HORIZON_MAX_FRAC` for seascape detection). If a photo classifies wrongly,
  discuss adjusting them rather than hand-editing the manifest: the
  fitter overwrites `manifest.json` on every run.
- Checking the fit visually: open the page with `?reveal` in the URL to
  hold every photograph fully visible on the dome.

The page itself rarely needs edits: it reads `samesky-assets/manifest.json`
at load time, so new photos appear without touching the HTML.
