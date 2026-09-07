---
name: words
description: Publish poems from ~/poetry to the Words section of the site (static/words/) as book-page images. Use when the user wants to add a poem, render new poetry, rebuild the words index, or check which poems are unpublished.
---

# Words

Poems live as Markdown files in `~/poetry/`, one per file. The site
shows them at `/words/` as images of typeset pages (Baskerville on
cream paper) rather than as text, so they read like a poetry book and
don't lift out with a drag-select. `tools/words.py` does the rendering
and writes the whole section; this skill is the procedure around it.

## Publishing new poems

1. Run the renderer. It is additive: a manifest at
   `static/words/manifest.json` remembers each poem by slug and a hash
   of its source, so only new or edited poems are drawn. Use
   `--report-only` first if you just want to see what is pending.

   ```
   tools/words.py --report-only
   tools/words.py
   ```

   It prints one line per poem (`new`, `changed`, `kept`) and then the
   page images it wrote. Don't Read the WebP outputs; the report says
   what happened. If the user wants to see the page, downscale one to a
   PNG in the scratchpad and Read that.

2. The tool regenerates `static/words/index.html` and one
   `static/words/<slug>.html` per poem every run, newest first, with
   previous/next links between poems. Nothing needs hand-editing.

3. Report to the user: which poems went in, how many pages each took,
   and anything the parser was unsure about (missing title, no
   dedication picked up, very long lines).

4. Commit and push when asked, in this repo's usual one-line poetic
   commit style. Sources in `~/poetry/` are not in the repo; only the
   rendered pages, HTML and manifest are.

## Source format

```
# Title of the poem
-optional dedication, italic, straight after the title

Verse lines. A blank line is a stanza break.
```

- The H1 is the title; without one the filename is used.
- A line beginning `-` (or an en/em dash) right after the title is set
  in italic as a dedication or epigraph.
- Long verse lines wrap with a hanging indent. A poem that overflows a
  page continues on a second page with a running head and "n of m"
  folio.
- The date under the poem is the file's creation date on first render
  and is then kept in the manifest, so editing a poem later does not
  move it. To change a date, edit `written` in the manifest and rerun
  with `--force` for that to reach the image.

## Editing or removing

- Editing a poem's text and rerunning re-renders just that poem (the
  hash changes). Renaming the title changes the slug, so the old entry
  lingers in the manifest: delete its object from `manifest.json` and
  its images from `static/words/pages/` by hand, then rerun.
- `--force` redraws everything, for instance after changing the page
  design in `tools/words.py`.

## Notes

- The renderer needs macOS for the system Baskerville face; it exits
  with a clear message elsewhere.
- Every generated page carries the counter.dev tracking snippet, as all
  static pages must.
- `public/` is gitignored and rebuilt by Hugo, so never mirror edits
  there. The `Words` menu item is in `hugo.toml` next to `Art`.
