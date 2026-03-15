---
name: paper-pdf-to-cn-latex
description: End-to-end translation of English academic paper PDFs into complete Chinese LaTeX projects and final Chinese PDFs. Use when Codex must translate a full paper, arXiv article, conference/journal PDF, or technical report from English to Chinese while preserving all prose, equations, references, footnotes, and section structure. Rebuild the output in LaTeX, keep figures and tables as images instead of translating their internal text, and compile or prepare a print-ready Chinese PDF.
---

# Paper Pdf To Cn Latex

## Overview

Produce a complete Chinese paper package instead of a partial summary. Translate all narrative text, preserve equations and citations, keep figures and tables as images, and rebuild the document in clean LaTeX that can compile with XeLaTeX. The Chinese should read like a native academic paper: faithful in meaning, but smooth in sentence flow rather than mechanically mirroring English syntax.

When the paper is on arXiv, fetch the arXiv TeX source package first and use it as the primary textual source. Treat the PDF as the visual/layout reference and as a completeness check. When original figure assets are available from source files, prefer rendering those assets over cropping figures back out of the paper pages.

## Quick Start

1. Run the bootstrap script to create a working project, extract page images, and dump block-level PDF text:

```bash
python scripts/bootstrap_translation_job.py path/to/paper.pdf work/paper-job --title "short-job-name"
```

2. Immediately try to fetch the arXiv source package into the job workspace. If arXiv source exists, use the extracted `.tex`, `.bib`, and figure assets as the primary source materials:

```bash
python scripts/fetch_arxiv_source.py path/to/paper.pdf work/paper-job/source/arxiv-source
```

3. Read [references/workflow.md](references/workflow.md) for the detailed sequence and read [references/quality-gate.md](references/quality-gate.md) before writing translation output.
4. Fill in `work/translation-plan.md` with the original English title, final PDF filename, section map, and terminology sheet before drafting LaTeX. Translate every section into Chinese. Preserve formulas, inline math, equation numbering, references, appendices, acknowledgements, and bibliography entries.
5. Build a figure/table manifest. For page crops, exclude English captions and surrounding body text. When a standalone figure asset exists, point the manifest entry at `source_file` instead of page-cropping it.
6. Run `scripts/crop_pdf_regions.py`, then run `scripts/review_cropped_regions.py` and inspect every crop before treating it as final.
7. Write the Chinese LaTeX into the generated `latex/` project and compile with `scripts/compile_latex.py`. Always pass the original English paper title so the final PDF is renamed to `[original paper title].pdf`:

```bash
python scripts/compile_latex.py latex --title "Original English Paper Title"
```

## Workflow

### 1. Scaffold the translation job

Run `scripts/bootstrap_translation_job.py` first. It creates:

- `source/source.pdf`: local copy of the original PDF
- `source/arxiv-source/`: optional extracted arXiv TeX source package when `scripts/fetch_arxiv_source.py` succeeds
- `work/page-images/`: rendered page PNGs for visual inspection
- `work/page-manifest.json`: page size, text blocks, image blocks, font hints
- `work/source-text.txt`: concatenated extracted text for searching
- `work/translation-plan.md`: source-package notes, section map, readability checklist, and terminology sheet
- `work/regions.example.json`: sample schema for figure/table crop manifests
- `latex/`: Chinese LaTeX project copied from `assets/latex-template/`

Use the manifest to infer the paper structure. Large-font text blocks are often titles or headings; image blocks and caption-adjacent regions usually correspond to figures or tables.

### 2. Fetch arXiv source before drafting

Before translating from PDF extraction alone, try:

```bash
python scripts/fetch_arxiv_source.py path/to/paper.pdf output-dir/source/arxiv-source
```

If the script succeeds, inspect `source/arxiv-source/arxiv-source.json`, then use the extracted `.tex`, `.bib`, and figure files as the primary source of truth for prose, equations, references, and figures. Keep the PDF manifest and page images in the loop to verify ordering, caption placement, and that no content went missing during source-package recovery. If the script cannot find an arXiv ID or arXiv does not provide source, fall back to the PDF workflow without blocking the task.

### 3. Build the translation plan before editing LaTeX

Map the paper into `work/translation-plan.md` before editing LaTeX:

- Source package notes: original English title, final PDF filename, arXiv ID/source directory when available
- Front matter: title, authors, affiliations, abstract, keywords
- Main body: numbered sections, subsections, algorithms, theorem-like blocks
- Back matter: acknowledgements, references, appendices, supplementary notes
- Terminology sheet: specialized concepts, methods, metrics, datasets, objectives, or theorem names that need standardized Chinese renderings

Do not translate piecemeal without a structure map. First confirm that every source page is accounted for and note where each figure/table should appear in the rebuilt Chinese document. Record the preferred translation for important technical terms before they begin to repeat across the paper.

### 4. Translate all prose, not just visible body text

Translate:

- Title, abstract, keywords
- Section and subsection headings
- Main paragraphs, lists, captions, footnotes, appendix text
- Figure/table captions outside the image itself
- Acknowledgements and author notes when present

Do not translate:

- Text embedded inside figures or tables when the figure/table is kept as an image
- Citation keys, BibTeX fields, equation syntax, or code identifiers unless the surrounding prose requires explanation

Write readable academic Chinese, not sentence-by-sentence calques. While translating:

- Reorder clauses to fit Chinese syntax when needed.
- Split overlong English sentences or merge choppy fragments if that improves readability without losing meaning.
- Rewrite stacked modifiers, passive chains, and ambiguous pronouns into clearer Chinese phrasing.
- Keep the technical meaning, hedging, and causal logic intact even when the sentence shape changes.

For terminology:

- Maintain the term sheet in `work/translation-plan.md`.
- On the first occurrence of a specialized technical term in the delivered document, use `中文术语（English Term）`.
- After the first occurrence, reuse the agreed Chinese term or a standard abbreviation consistently. Do not repeat the English parenthetical on every mention unless clarity would otherwise suffer.
- If a term is conventionally kept in English and a Chinese rendering would be awkward or misleading, keep the English term and add a brief Chinese explanation once if needed.

If the source PDF is text-poor or scanned, continue from page images and re-transcribe or OCR the missing text. Never omit content only because extraction is noisy.

### 5. Preserve figures and tables as images

Use `scripts/crop_pdf_regions.py` with a JSON manifest. Prefer cropping directly from the original PDF rather than screenshotting rendered pages because the PDF crop remains sharper. If the paper source package includes standalone figure assets, prefer rendering those files directly via `source_file` manifest entries.

Use this rule:

- Translate the caption outside the image.
- Keep the original figure or table body untouched inside the image.
- Preserve figure/table ordering and cross-references.
- Do not include the original English caption or neighboring paragraph text inside a page crop.

After cropping, run `scripts/review_cropped_regions.py` and inspect every result. Reject any crop that clips borders, legends, axis labels, or table columns.

If a table spans most of a page and rebuilding it in LaTeX would risk content loss, crop the entire table as an image and place it with a translated caption.

### 6. Rebuild in LaTeX, not raw Markdown

Edit the generated `latex/main.tex` and `latex/sections/*.tex` files. Keep the structure clean:

- Put abstract text in `sections/00-abstract.tex`
- Put the translated paper body in `sections/10-body.tex`
- Put references in `sections/99-references.tex`
- Store cropped figure/table images in `latex/figures/`

Preserve the original section order. Match the original column count only if it is straightforward and does not reduce reliability; otherwise prefer a clean single-column Chinese layout with correct hierarchy, equations, and image placement.

### 7. Compile and verify

Compile with:

```bash
python scripts/compile_latex.py latex --title "Original English Paper Title"
```

If `xelatex` is unavailable, still finish the LaTeX project and clearly report that compilation is blocked by the environment. When compilation succeeds, the final PDF should be renamed to `[original paper title].pdf` with only OS-invalid filename characters sanitized. Before concluding, validate the result against the quality gate.

## Non-Negotiable Rules

- Deliver a complete translation. Do not stop at abstract-only or section-only output unless the user explicitly narrows scope.
- If arXiv provides a TeX source package, use it as the primary textual source before falling back to PDF text extraction.
- Preserve equations exactly unless notation is obviously corrupted by extraction.
- Preserve references and numbering. Chinese translation does not justify dropping bibliography entries, appendices, or footnotes.
- Prefer natural, publication-style Chinese over literal English word order.
- Use first-mention terminology glosses for specialized terms: `中文术语（English Term）`.
- Keep figures and tables as images when their internal content would otherwise need translation.
- Place images near the corresponding discussion, and provide translated captions in LaTeX.
- Rename the compiled PDF to `[original paper title].pdf` after successful compilation.
- Prefer faithful meaning over literal English word order, but do not summarize or compress technical arguments.

## Resources

- `scripts/bootstrap_translation_job.py`: initialize a job, copy the template, render pages, and export block manifests
- `scripts/fetch_arxiv_source.py`: detect an arXiv ID from a PDF/URL/ID, download the source package, extract it safely, and summarize the recovered `.tex`, `.bib`, and figure files
- `scripts/crop_pdf_regions.py`: crop figure/table regions from the original PDF using PDF-point or page-image pixel coordinates, or render a standalone source figure asset
- `scripts/review_cropped_regions.py`: generate page-overlay previews and an HTML review sheet for every cropped region
- `scripts/compile_latex.py`: compile the generated LaTeX with repeated XeLaTeX runs and optionally rename the final PDF to the original English paper title
- `references/workflow.md`: detailed operating procedure and manifest formats
- `references/quality-gate.md`: acceptance checklist and edge-case rules
- `assets/latex-template/`: reusable Chinese LaTeX template copied into each translation job
