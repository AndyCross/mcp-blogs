---
name: lifted
description: Add a new entry to the Lifted from Fate art page (static/art/fate.html). Use when the user wants to record something remarkable that happened today, add to the lifted array, or update the fate threads piece with new words.
---

# Lifted from Fate

The art page at `static/art/fate.html` shows bioluminescent threads of
fate flowing around the viewer, every thread a pair of strands that
drift apart and wind back together, never unlinked. It keeps a record
of remarkable things lifted from fate in a `lifted` array, exactly like
the pledges in `ooo.html`. The newest entry becomes the opening title
and its tint runs through every thread; older entries stay behind the
glyph in the corner.

## Adding an entry

1. Get the words from the user: a `title` (the remarkable thing, one
   short sentence) and optionally a `whisper` (a longer subheading;
   quieter, explanatory). If no whisper is given, reuse nothing: the
   field still needs a value, so ask, or draft one from what they said
   and confirm. English only on this piece.
2. Pick a `tint` unless the user gives one. It colours the title glow
   and washes lightly through the threads and motes. Stay in the family
   of the pledge colours already in the file (`PLEDGE_COLOURS`):
   crimsons and roses for the ardent, slates and sky blues for the calm.
   When unsure, ask, showing two or three candidates.
3. Append an object to the END of the `lifted` array in
   `static/art/fate.html` (oldest first, newest last):

   ```js
   {
       date: 'YYYY-MM-DD',   // today, unless the user says otherwise
       title: '...',
       whisper: '...',
       tint: '#rrggbb'
   }
   ```

   Nothing else needs editing: the page derives the opening words, the
   thread tint, and the timeline from the array at load time.
4. Do not rewrite or delete earlier entries; the history is the point.
   Only edit an old entry if the user explicitly asks.
5. Commit and push when asked, in this repo's usual one-line poetic
   commit style.

## Notes

- The escaping matters: the strings are single-quoted JS, so escape
  any apostrophe in the words as `\'`.
- The piece is listed only on the secret archive
  (`todas-c51e1c2388fe29fe.html`), not the public index, as of
  2026-08-19. Adding entries does not change the listings.
- `public/` is gitignored and rebuilt by Hugo, so never mirror edits
  there.
