#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pillow>=10.0",
# ]
# ///
"""
Words: poetry set as book pages.

Reads Markdown poems from a folder (default ~/poetry), typesets each one
as if it were a page in a small poetry book, and writes the result as
images rather than text. The words live only in pixels on the site, so
they read as a printed page and don't lift out with a drag-select.

Source format (one poem per .md file):

    # Title of the poem
    -an optional dedication or epigraph, italic, straight after the title

    Lines of the poem.
    A blank line is a stanza break.

Long lines wrap with a hanging indent, the way a printed poem does. If a
poem runs past one page it continues onto a second, and so on.

The run is additive. A manifest (static/words/manifest.json) remembers
each poem by slug together with a hash of its source text; poems whose
text hasn't changed are left alone, new or edited poems are rendered.
The index page and every poem page are regenerated from the manifest
each run, so listings are always complete.

Usage:
    tools/words.py                         # ~/poetry -> static/words
    tools/words.py ~/poetry static/words
    tools/words.py --force                 # re-render everything
    tools/words.py --report-only           # say what would change
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# Page geometry. A small book page at 2x for retina screens.
# ---------------------------------------------------------------------------

SCALE = 2
PAGE_W = 720 * SCALE
PAGE_H = 1040 * SCALE
MARGIN_X = 84 * SCALE
MARGIN_TOP = 120 * SCALE
MARGIN_BOTTOM = 110 * SCALE

TITLE_SIZE = 30 * SCALE
DEDICATION_SIZE = 17 * SCALE
BODY_SIZE = 18 * SCALE
FOLIO_SIZE = 12 * SCALE
LEADING = 30 * SCALE            # baseline to baseline for the body
STANZA_GAP = 18 * SCALE         # extra space between stanzas
HANGING_INDENT = 28 * SCALE     # continuation lines of a wrapped verse line

PAPER = (247, 241, 228)
INK = (38, 34, 30)
INK_SOFT = (110, 102, 92)
RULE = (170, 158, 140)

FONT_FILE = "/System/Library/Fonts/Supplemental/Baskerville.ttc"
FACE_REGULAR, FACE_BOLD, FACE_ITALIC, FACE_BOLD_ITALIC, FACE_SEMIBOLD = 0, 1, 2, 3, 4

TRACKING_ID = "72d92ac8-56cf-4fdd-9899-b73adbab2e4d"


def font(face: int, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(FONT_FILE, size, index=face)
    except OSError:
        sys.exit(f"Baskerville not found at {FONT_FILE}; this renderer expects macOS.")


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

@dataclass
class Poem:
    slug: str
    title: str
    dedication: str | None
    stanzas: list[list[str]]
    source: Path
    written: str            # ISO date
    sha: str

    @property
    def line_count(self) -> int:
        return sum(len(s) for s in self.stanzas)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "untitled"


def parse_poem(path: Path) -> Poem:
    raw = path.read_text(encoding="utf-8")
    lines = raw.replace("\r\n", "\n").split("\n")

    title = path.stem
    dedication = None
    body_start = 0

    # Title: first H1, else the filename.
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            body_start = i + 1
        break

    # Dedication: a line starting with '-' immediately following the title.
    j = body_start
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j < len(lines) and re.match(r"^\s*[-–—]\s*\S", lines[j]) and not lines[j].startswith("- "):
        dedication = re.sub(r"^\s*[-–—]\s*", "", lines[j]).strip()
        body_start = j + 1

    # Stanzas: groups of non-blank lines.
    stanzas: list[list[str]] = []
    current: list[str] = []
    for line in lines[body_start:]:
        if line.strip():
            current.append(line.rstrip())
        elif current:
            stanzas.append(current)
            current = []
    if current:
        stanzas.append(current)

    st = path.stat()
    born = getattr(st, "st_birthtime", None) or st.st_mtime
    written = datetime.fromtimestamp(born).date().isoformat()

    sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return Poem(slugify(title), title, dedication, stanzas, path, written, sha)


# ---------------------------------------------------------------------------
# Typesetting
# ---------------------------------------------------------------------------

@dataclass
class Line:
    text: str
    indent: int = 0
    gap_before: int = 0     # extra vertical space before this line


def wrap_line(text: str, fnt: ImageFont.FreeTypeFont, width: int) -> list[Line]:
    """Wrap one verse line to the measure, continuation lines indented."""
    words = text.split()
    if not words:
        return [Line("")]
    out: list[Line] = []
    current = words[0]
    indent = 0
    for w in words[1:]:
        trial = f"{current} {w}"
        if fnt.getlength(trial) <= width - indent:
            current = trial
        else:
            out.append(Line(current, indent))
            indent = HANGING_INDENT
            current = w
    out.append(Line(current, indent))
    return out


def layout(poem: Poem, body: ImageFont.FreeTypeFont) -> list[Line]:
    measure = PAGE_W - 2 * MARGIN_X
    lines: list[Line] = []
    for si, stanza in enumerate(poem.stanzas):
        first_in_stanza = True
        for verse in stanza:
            wrapped = wrap_line(verse, body, measure)
            if first_in_stanza and si > 0:
                wrapped[0].gap_before = STANZA_GAP
            first_in_stanza = False
            lines.extend(wrapped)
    return lines


def paginate(lines: list[Line], first_page_top: int) -> list[list[Line]]:
    """Split laid-out lines into pages. The first page starts lower (title)."""
    pages: list[list[Line]] = []
    page: list[Line] = []
    y = first_page_top
    bottom = PAGE_H - MARGIN_BOTTOM
    for ln in lines:
        step = LEADING + (ln.gap_before if page else 0)
        if y + step > bottom and page:
            pages.append(page)
            page = []
            y = MARGIN_TOP
            step = LEADING
        y += step
        page.append(ln)
    if page or not pages:
        pages.append(page)
    return pages


# ---------------------------------------------------------------------------
# Paper
# ---------------------------------------------------------------------------

def make_paper(seed: int) -> Image.Image:
    """Cream paper with a whisper of grain and a soft darkening to the gutter."""
    import random

    rnd = random.Random(seed)
    base = Image.new("RGB", (PAGE_W, PAGE_H), PAPER)

    # Grain: coarse noise, blurred, blended very lightly.
    small = Image.effect_noise((PAGE_W // 4, PAGE_H // 4), 22).resize((PAGE_W, PAGE_H), Image.BILINEAR)
    small = small.filter(ImageFilter.GaussianBlur(1.2 * SCALE))
    grain = Image.merge("RGB", (small, small, small))
    base = Image.blend(base, grain, 0.06)

    # A few pale fibres.
    d = ImageDraw.Draw(base)
    for _ in range(140):
        x = rnd.randint(0, PAGE_W)
        y = rnd.randint(0, PAGE_H)
        length = rnd.randint(6, 26) * SCALE
        angle = rnd.uniform(-0.6, 0.6)
        x2 = x + int(length * (1 - abs(angle)))
        y2 = y + int(length * angle)
        shade = rnd.randint(218, 236)
        d.line([(x, y), (x2, y2)], fill=(shade, shade - 6, shade - 18), width=1)

    # Gutter shadow on the left edge, like the page sits in a binding.
    shadow = Image.new("L", (PAGE_W, PAGE_H), 0)
    sd = ImageDraw.Draw(shadow)
    for i in range(70 * SCALE):
        a = int(58 * (1 - i / (70 * SCALE)) ** 2)
        sd.line([(i, 0), (i, PAGE_H)], fill=a)
    dark = Image.new("RGB", (PAGE_W, PAGE_H), (120, 104, 84))
    return Image.composite(dark, base, shadow)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_pages(poem: Poem, out_dir: Path) -> list[str]:
    title_f = font(FACE_REGULAR, TITLE_SIZE)
    ded_f = font(FACE_ITALIC, DEDICATION_SIZE)
    body_f = font(FACE_REGULAR, BODY_SIZE)
    folio_f = font(FACE_ITALIC, FOLIO_SIZE)

    # Title block height decides where the poem starts on page one.
    title_lines = wrap_line(poem.title, title_f, PAGE_W - 2 * MARGIN_X)
    y = MARGIN_TOP
    title_leading = int(TITLE_SIZE * 1.25)
    block_h = len(title_lines) * title_leading
    if poem.dedication:
        block_h += int(DEDICATION_SIZE * 1.6)
    block_h += 34 * SCALE  # rule and breathing room
    first_top = y + block_h

    lines = layout(poem, body_f)
    pages = paginate(lines, first_top)

    seed = int(poem.sha, 16) & 0xFFFF
    written = []
    for pi, page_lines in enumerate(pages):
        img = make_paper(seed + pi)
        d = ImageDraw.Draw(img)
        y = MARGIN_TOP

        if pi == 0:
            for tl in title_lines:
                d.text((MARGIN_X, y), tl.text, font=title_f, fill=INK)
                y += title_leading
            if poem.dedication:
                y += 4 * SCALE
                d.text((MARGIN_X, y), poem.dedication, font=ded_f, fill=INK_SOFT)
                y += int(DEDICATION_SIZE * 1.6) - 4 * SCALE
            y += 12 * SCALE
            d.line([(MARGIN_X, y), (MARGIN_X + 38 * SCALE, y)], fill=RULE, width=max(1, SCALE // 2))
            y = first_top
        else:
            # Running head on continuation pages.
            d.text((MARGIN_X, MARGIN_TOP - 44 * SCALE), poem.title, font=folio_f, fill=INK_SOFT)

        for i, ln in enumerate(page_lines):
            if i > 0:
                y += LEADING + ln.gap_before
            d.text((MARGIN_X + ln.indent, y), ln.text, font=body_f, fill=INK)

        # Folio: date on the left, page count on the right when there are several.
        foot_y = PAGE_H - MARGIN_BOTTOM + 44 * SCALE
        date_txt = datetime.fromisoformat(poem.written).strftime("%-d %B %Y")
        d.text((MARGIN_X, foot_y), date_txt, font=folio_f, fill=INK_SOFT)
        if len(pages) > 1:
            folio = f"{pi + 1} of {len(pages)}"
            w = folio_f.getlength(folio)
            d.text((PAGE_W - MARGIN_X - w, foot_y), folio, font=folio_f, fill=INK_SOFT)

        name = f"{poem.slug}-{pi + 1}.webp" if len(pages) > 1 else f"{poem.slug}.webp"
        img.save(out_dir / name, "WEBP", quality=82, method=6)
        written.append(name)
    return written


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<script src="https://cdn.counter.dev/script.js" data-id="{tracking}" data-utcoffset="0"></script>
<style>
  :root {{
    --bg: #151311;
    --text: #e8e2d6;
    --muted: #9a8f80;
    --accent: #d8b07a;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; background: var(--bg); color: var(--text); }}
  body {{
    min-height: 100vh;
    font-family: Baskerville, "Libre Baskerville", Georgia, "Times New Roman", serif;
    -webkit-font-smoothing: antialiased;
  }}
  .wrap {{ max-width: 860px; margin: 0 auto; padding: 3.5rem 1.25rem 5rem; }}
  a.back {{ color: var(--muted); text-decoration: none; font-size: 0.95rem; }}
  a.back:hover {{ color: var(--accent); }}
  h1 {{ font-weight: 400; font-size: 2.4rem; letter-spacing: 0.01em; margin: 1.5rem 0 0.4rem; }}
  .lede {{ color: var(--muted); font-style: italic; font-size: 1.1rem; margin: 0 0 3rem; max-width: 36rem; }}
  ul.poems {{ list-style: none; margin: 0; padding: 0; }}
  ul.poems li {{ border-top: 1px solid rgba(232, 226, 214, 0.12); }}
  ul.poems li:last-child {{ border-bottom: 1px solid rgba(232, 226, 214, 0.12); }}
  ul.poems a {{
    display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
    padding: 1.1rem 0.25rem; color: inherit; text-decoration: none;
  }}
  ul.poems a:hover .t {{ color: var(--accent); }}
  ul.poems .t {{ font-size: 1.25rem; }}
  ul.poems .d {{ color: var(--muted); font-size: 0.85rem; font-style: italic; white-space: nowrap; }}
  .new-badge {{
    display: inline-block; margin-left: 0.6rem; padding: 0.1rem 0.5rem; font-size: 0.65rem;
    letter-spacing: 0.1em; border-radius: 999px; vertical-align: middle; font-style: normal;
    color: var(--accent); border: 1px solid rgba(216, 176, 122, 0.5);
  }}
  .pages {{ display: flex; flex-direction: column; align-items: center; gap: 2rem; margin-top: 2.5rem; }}
  .page {{
    width: 100%; max-width: 720px; display: block;
    border-radius: 2px;
    box-shadow: 0 30px 60px rgba(0,0,0,0.55), 0 2px 6px rgba(0,0,0,0.4);
    user-select: none; -webkit-user-select: none; -webkit-touch-callout: none;
    pointer-events: none;
  }}
  nav.between {{ display: flex; justify-content: space-between; margin-top: 3rem; font-style: italic; }}
  nav.between a {{ color: var(--muted); text-decoration: none; }}
  nav.between a:hover {{ color: var(--accent); }}
  .colophon {{ color: var(--muted); font-size: 0.8rem; font-style: italic; margin-top: 3rem; text-align: center; }}
  a.close {{
    position: fixed; top: 1rem; right: 1rem; z-index: 10;
    width: 2.75rem; height: 2.75rem; display: flex; align-items: center; justify-content: center;
    border-radius: 999px; color: var(--text); text-decoration: none;
    background: rgba(21, 19, 17, 0.7); border: 1px solid rgba(232, 226, 214, 0.25);
    backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
    font-size: 1.5rem; line-height: 1; transition: border-color 0.2s ease, color 0.2s ease;
  }}
  a.close:hover {{ color: var(--accent); border-color: var(--accent); }}
</style>
</head>
<body>
  <div class="wrap">
"""

FOOT = """  </div>
</body>
</html>
"""


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def write_index(entries: list[dict], out_dir: Path) -> None:
    items = []
    for e in sorted(entries, key=lambda e: (e["written"], e["title"]), reverse=True):
        date_txt = datetime.fromisoformat(e["written"]).strftime("%-d %B %Y")
        items.append(
            f'      <li><a href="/words/{e["slug"]}.html" data-date="{e["written"]}">'
            f'<span class="t">{esc(e["title"])}</span>'
            f'<span class="d">{date_txt}</span></a></li>'
        )
    body = (
        HEAD.format(title="Words — Step Into Dev", tracking=TRACKING_ID)
        + '    <a class="back" href="/">← Step Into Dev</a>\n'
        + "    <h1>Words</h1>\n"
        + '    <p class="lede">Poems, set as pages. They are pictures of words rather than words, '
          'so read them here, slowly, the way you would a book left open on a table.</p>\n'
        + '    <ul class="poems">\n' + "\n".join(items) + "\n    </ul>\n"
        + """    <script>
      // A poem counts as new for 48 hours from its date's midnight.
      const FRESH_MS = 48 * 60 * 60 * 1000;
      document.querySelectorAll('ul.poems a[data-date]').forEach(a => {
        const d = new Date(a.dataset.date + 'T00:00:00');
        if (Date.now() - d.getTime() < FRESH_MS) {
          const b = document.createElement('span');
          b.className = 'new-badge'; b.textContent = 'new';
          a.querySelector('.t').appendChild(b);
        }
      });
    </script>
"""
        + FOOT
    )
    (out_dir / "index.html").write_text(body, encoding="utf-8")


def write_poem_page(entry: dict, prev_e: dict | None, next_e: dict | None, out_dir: Path) -> None:
    imgs = "\n".join(
        f'      <img class="page" src="/words/pages/{name}" alt="{esc(entry["title"])}, page {i + 1}" '
        f'draggable="false" width="{PAGE_W // SCALE}" height="{PAGE_H // SCALE}" loading="{"eager" if i == 0 else "lazy"}">'
        for i, name in enumerate(entry["pages"])
    )
    nav = "    <nav class=\"between\">\n"
    nav += (f'      <a href="/words/{prev_e["slug"]}.html">← {esc(prev_e["title"])}</a>\n' if prev_e else "      <span></span>\n")
    nav += (f'      <a href="/words/{next_e["slug"]}.html">{esc(next_e["title"])} →</a>\n' if next_e else "      <span></span>\n")
    nav += "    </nav>\n"
    body = (
        HEAD.format(title=f"{entry['title']} — Words", tracking=TRACKING_ID)
        + '    <a class="close" href="/words/" aria-label="Back to Words" title="Back to Words">×</a>\n'
        + '    <a class="back" href="/words/">← Words</a>\n'
        + '    <div class="pages">\n' + imgs + "\n    </div>\n"
        + nav
        + '    <p class="colophon">Set in Baskerville.</p>\n'
        + FOOT
    )
    (out_dir / f"{entry['slug']}.html").write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?", default=str(Path.home() / "poetry"))
    ap.add_argument("out", nargs="?", default="static/words")
    ap.add_argument("--force", action="store_true", help="re-render every poem")
    ap.add_argument("--report-only", action="store_true", help="print what would change, write nothing")
    args = ap.parse_args()

    src = Path(args.source).expanduser()
    out = Path(args.out)
    pages_dir = out / "pages"
    manifest_path = out / "manifest.json"

    if not src.is_dir():
        sys.exit(f"no such folder: {src}")

    manifest: dict[str, dict] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    poems = [parse_poem(p) for p in sorted(src.glob("*.md"))]
    if not poems:
        print(f"no .md poems in {src}")

    new, changed, same = [], [], []
    for poem in poems:
        prev = manifest.get(poem.slug)
        if prev is None:
            new.append(poem)
        elif prev.get("sha") != poem.sha or args.force:
            changed.append(poem)
        else:
            same.append(poem)

    for p in new:
        print(f"  new      {p.title!r}  ({p.line_count} lines)")
    for p in changed:
        print(f"  changed  {p.title!r}  ({p.line_count} lines)")
    for p in same:
        print(f"  kept     {p.title!r}")

    if args.report_only:
        return

    out.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    for poem in new + changed:
        # Clear stale page images for this slug before writing fresh ones.
        for old in pages_dir.glob(f"{poem.slug}*.webp"):
            old.unlink()
        # An edit to an existing poem keeps its original date.
        prev_written = (manifest.get(poem.slug) or {}).get("written") or poem.written
        poem.written = prev_written
        names = render_pages(poem, pages_dir)
        manifest[poem.slug] = {
            "slug": poem.slug,
            "title": poem.title,
            "dedication": poem.dedication,
            "written": poem.written,
            "source": poem.source.name,
            "sha": poem.sha,
            "pages": names,
        }
        print(f"  rendered {poem.title!r} -> {', '.join(names)}")

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    entries = sorted(manifest.values(), key=lambda e: (e["written"], e["title"]), reverse=True)
    write_index(entries, out)
    for i, e in enumerate(entries):
        prev_e = entries[i - 1] if i > 0 else None
        next_e = entries[i + 1] if i + 1 < len(entries) else None
        write_poem_page(e, prev_e, next_e, out)
    print(f"  index    {len(entries)} poem(s) -> {out / 'index.html'}")


if __name__ == "__main__":
    main()
