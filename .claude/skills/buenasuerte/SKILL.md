---
name: buenasuerte
description: Update the Buena Suerte art page with new puzzle score screenshots and optional handwritten notes. Use when the user wants to add new kept scores, write a note on a card, or refresh the puzzle score wall.
---

# Buena Suerte score wall

The art page at `static/art/buenasuerte.html` shows kept scores from the
daily word puzzle as polaroid tickets pinned to a dark green wall, in the
order they were played. This skill updates it.

## Adding new scores

1. Screenshots are iPhone score screens (1206x2622 PNGs), usually in
   `~/Downloads/puzzle/`. Ask where they are if unclear. New screenshots
   go in the SAME folder as the old ones: the converter processes the
   whole folder and filename order (IMG_NNNN) is the play order.
2. Run the converter:

   ```
   tools/puzzle.py ~/Downloads/puzzle static/art/buenasuerte-assets
   ```

   It crops each screenshot to title + timer + streak, writes web-ready
   JPEGs and `manifest.json`, and preserves any existing `note` fields.
3. Mirror to the built site (Hugo copies static/ verbatim at build, but
   the repo keeps `public/` in sync by hand):

   ```
   cp static/art/buenasuerte.html public/art/buenasuerte.html
   cp -R static/art/buenasuerte-assets/. public/art/buenasuerte-assets/
   ```

4. If the run of puzzle numbers or streak range changed, update the
   page's card text on the secret archive
   `static/art/todas-c51e1c2388fe29fe.html` (it mentions "#885 to #900"
   and "39 to 54") and mirror that file to `public/art/` too.

## Writing a note on a card

Notes are handwriting on a card's polaroid chin. Add a `"note"` field to
that card's entry in `static/art/buenasuerte-assets/manifest.json`:

```json
{ "name": "img_5299.jpg", "width": 720, "height": 591, "note": "Happy holidays, chica x" }
```

Cards are named after their source screenshot. To find the right card,
match the user's description (usually "today's" = the latest = last
entry) or Read the JPEGs in `static/art/buenasuerte-assets/` to see
which puzzle is which. Keep notes short (one line, it has to fit the
chin). Reruns of the converter keep notes, so edit the manifest freely.
Mirror the manifest to `public/art/buenasuerte-assets/` after editing.

## Verifying

Screenshot the page headlessly and Read the PNG to check the layout:

```
cd static/art && python3 -m http.server 8471 &
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
  --window-size=1280,2400 --virtual-time-budget=15000 \
  --screenshot=<scratchpad>/buenasuerte.png "http://localhost:8471/buenasuerte.html"
kill %1
```

Check: every card fades in pinned at a slight tilt, noted cards show
their handwriting in the deeper chin, and the closing line "buena
suerte, donde estés" sits under the wall.

## Style

The page is an elegy, not a dashboard. Keep any new text quiet and
tender, in the voice of the title and whisper already there. No em
dashes (see CLAUDE.md). Don't commit unless asked.
