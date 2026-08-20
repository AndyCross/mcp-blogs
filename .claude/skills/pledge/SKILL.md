---
name: pledge
description: Add a new pledge to the My Pledge art page (static/art/ooo.html). Use when the user wants to add a pledge, update the rose piece, or append to the pledges array with a new title, subtitle, and colour.
---

# My Pledge

The art page at `static/art/ooo.html` is a raymarched rose that blooms
and comes apart in an endless cycle. It keeps a record of pledges in a
`pledges` array, oldest first. The newest entry becomes the opening
title, its tint becomes the colour the rose blooms in, and the older
pledges stay behind the glyph in the corner, fading with age.

## Adding a pledge

1. Get the words from the user: a `title` and a `whisper` (the
   subtitle; longer, quieter). "The classic" means the Spanish title
   "Te amaré siempre." exactly, even if the user says it in English.
   Otherwise keep whichever language they give; the user mixes Spanish
   and English freely. Don't translate or "improve" the words; these
   are said words.
2. Pick a `tint` unless the user gives one. Named colours map to hex:
   crimson is `#dc143c`. Otherwise stay in the family already in the
   file: deep reds (`#c4122e`, `#d1102e`) for the ardent, slates and
   sky blues (`#3e4d68`, `#4a7ac9`) for the quiet, pale rose
   (`#c08081`) for the tender. When unsure, ask with two or three
   candidates.
3. Append an object to the END of the `pledges` array:

   ```js
   {
       date: 'YYYY-MM-DD',   // today, unless the user says otherwise
       title: '...',
       whisper: '...',
       tint: '#rrggbb',
       final: true
   }
   ```

4. Move `final: true` to the new entry: delete the `final` line from
   the previous last pledge and set it on the new one. The final pledge
   is the one whose words never fade, whose bloom holds longer, whose
   orbit drifts, and which the timeline marks "la última promesa".
   Exactly one pledge (the last) should carry it.
5. Update the hardcoded markup to mirror the new pledge, since the
   static `<h1>` and `#whisper` div in the body always echo the latest
   entry:

   ```html
   <h1>...new title...</h1>
   <div id="whisper">...new whisper...</div>
   ```

6. Do not rewrite or delete earlier pledges; the history is the point.
   Only edit an old entry if the user explicitly asks.
7. Commit and push when asked, in this repo's usual one-line poetic
   commit style.

## Notes

- The escaping matters: the strings are single-quoted JS, so escape
  any apostrophe in the words as `\'`.
- The art index (`static/art/index.html`) fetches `ooo.html` and reads
  the pledge dates itself, showing a "new" badge for 36 hours after
  the newest pledge's midnight. Adding a pledge needs no index edit.
- `public/` is gitignored and rebuilt by Hugo, so never mirror edits
  there.
