# Workflow

Read this file when running a real paper-translation job.

## Goal

Produce a complete Chinese LaTeX project and, when a LaTeX engine is available, a final Chinese PDF. Rebuild the paper faithfully rather than summarizing it. Preserve:

- all textual content outside figure/table images
- formulas, numbering, theorem labels, citations, footnotes
- author information, acknowledgements, appendices, references
- figure/table order and placement logic

## Project Bootstrap

Run:

```bash
python scripts/bootstrap_translation_job.py path/to/paper.pdf work/job-name
```

Inspect these files first:

- `project.json`: top-level manifest
- `work/page-manifest.json`: extracted page/block data
- `work/source-text.txt`: searchable extracted text
- `work/translation-plan.md`: section map, readability reminders, and terminology sheet
- `work/page-images/page-0001.png` etc.: visual reference
- `latex/main.tex`: Chinese LaTeX entrypoint

Before translating from PDF extraction alone, try to fetch the arXiv source package. Use it to recover clean text, bibliography artifacts, and standalone figure files that should be rendered directly instead of page-cropped.

Run:

```bash
python scripts/fetch_arxiv_source.py path/to/paper.pdf output-dir/source/arxiv-source
```

If this succeeds, inspect `source/arxiv-source/arxiv-source.json` first. Use the extracted `.tex`, `.bib`, and figure assets as the primary textual source, and use the PDF/page-manifest only to verify completeness, ordering, captions, and page-level layout.

## Operating Sequence

1. Inspect `project.json` and note page count and table of contents.
2. Try `scripts/fetch_arxiv_source.py` against the source PDF. If it succeeds, read `source/arxiv-source/arxiv-source.json` and inventory the extracted `.tex`, `.bib`, and figure files before relying on `work/source-text.txt`.
3. Read `work/page-manifest.json` to identify the title block, headings, captions, and image-heavy pages.
4. Draft the source notes, section map, and terminology sheet in `work/translation-plan.md` before translating. Record the original English title and the required final PDF filename `[original paper title].pdf`.
5. Translate all prose into readable Chinese and write it into `latex/sections/`.
6. Build a crop manifest for figures/tables. Prefer standalone source figure files when they exist; use page crops mainly for tables or assets that only exist inside the paper PDF.
7. Run `scripts/crop_pdf_regions.py`, then run `scripts/review_cropped_regions.py` and inspect every crop before moving on.
8. Insert the generated images into `latex/figures/` and add translated captions in LaTeX.
9. Compile with `scripts/compile_latex.py latex --title "Original English Paper Title"`.
10. Run the acceptance checks from [quality-gate.md](quality-gate.md).

## Working From the Page Manifest

Each page entry contains:

- `page`: 1-based page number
- `size_pt`: page width/height in PDF points
- `rotation`: page rotation
- `blocks`: ordered block list

Text blocks include:

- `bbox`: `[x0, y0, x1, y1]` in PDF points
- `text`: concatenated text for the block
- `word_count`
- `max_font_size`
- `fonts`

Image blocks include:

- `bbox`
- `width`
- `height`
- `ext` when available

Use `max_font_size` and location heuristics to identify headings. Use caption text plus neighboring image blocks to infer figure/table positions.

## Crop Manifest Format

Use either a bare JSON list or an object with `meta` and `regions`.

Preferred format:

```json
{
  "meta": {
    "unit": "pt",
    "render_dpi": 180
  },
  "regions": [
    {
      "id": "fig-1",
      "page": 3,
      "bbox": [72, 210, 520, 430],
      "kind": "figure",
      "filename": "fig-1.png",
      "caption": "Figure 1"
    },
    {
      "id": "fig-2-from-source",
      "kind": "figure",
      "source_file": "../source/figures/figure-2.pdf",
      "source_page": 1,
      "filename": "fig-2.png",
      "caption": "Figure 2"
    }
  ]
}
```

Coordinate rules:

- `unit: "pt"` means PDF points in the source page coordinate system.
- `unit: "px"` means pixel coordinates measured against the rendered page images.
- When using `px`, provide `render_dpi` in `meta`, in each region, or with `--render-dpi`.
- `bbox` order is always `[x0, y0, x1, y1]`.
- For page crops, `bbox` should contain only the figure/table body. Keep English captions and surrounding paragraphs outside the crop because the Chinese caption will be recreated in LaTeX.
- If `source_file` is present, the region is rendered from that standalone asset instead of from `source/source.pdf`. Resolve relative paths from the manifest first, then from the source PDF directory. `source_page` defaults to `1`.

Run:

```bash
python scripts/crop_pdf_regions.py source/source.pdf work/regions.json latex/figures
```

Review the crops:

```bash
python scripts/review_cropped_regions.py source/source.pdf work/regions.json latex/figures
```

Open `latex/figures/review/index.html` and check each item for:

- missing borders, legends, axis labels, or table columns
- accidental inclusion of English captions or neighboring body text
- page crops that should have been replaced with standalone source figures

## Compile and Finalize

Run:

```bash
python scripts/compile_latex.py latex --title "Original English Paper Title"
```

This should leave the final compiled PDF named `[original paper title].pdf`, with only OS-invalid filename characters sanitized when necessary.

## Translation Rules

- Translate technical prose faithfully into natural academic Chinese, not loose paraphrase and not line-by-line calque.
- Reorder clauses, split long sentences, or merge short fragments when needed to make the Chinese read smoothly without changing the meaning.
- Resolve long modifier chains, passive constructions, and unclear pronouns into explicit Chinese phrasing when the English structure would sound stiff if copied directly.
- Maintain the paper's level of certainty, contrast, and causality. Do not flatten claims like "may", "approximately", "we observe", or "in contrast".
- Record specialized terms in `work/translation-plan.md`. On the first occurrence of a specialized term in the delivered document, use `中文术语（English Term）`.
- After the first occurrence, keep terminology consistent. Reuse the chosen Chinese rendering or the paper's standard abbreviation instead of repeatedly appending English in parentheses.
- If the abstract contains the first occurrence of a term, annotate it there and avoid re-annotating every later use unless the paper switches context or the term would otherwise be ambiguous.
- Keep symbols, variable names, and displayed equations unchanged unless the source extraction is visibly corrupted.
- Translate captions outside the image. Do not edit text inside the image.
- Preserve original numbering of sections, equations, figures, tables, and bibliography references when practical.
- Preserve English proper nouns, dataset names, and product names where Chinese translation would be misleading.

## LaTeX Layout Rules

- Prefer a stable, readable Chinese single-column article unless a two-column recreation is trivial and clearly improves fidelity.
- Keep one figure/table image per logical float unless the source itself combines panels.
- Use `\label{}` for cross-referenced sections, equations, figures, and tables when those references appear in the translated text.
- Rebuild appendix sections explicitly; do not merge them into the main body.

## Failure Modes

If extraction quality is weak:

- fall back to page images and manual re-transcription
- keep a per-page checklist so no text is lost
- avoid silently dropping sidebars, footnotes, or marginal notes

If the environment lacks `xelatex`:

- finish the LaTeX project anyway
- report that compilation is blocked by tooling, not by document completeness

If a crop looks wrong:

- fix the manifest first rather than manually editing the exported PNG
- switch to `source_file` when the original figure asset exists
- rerun both crop and review commands until every image passes visual inspection
