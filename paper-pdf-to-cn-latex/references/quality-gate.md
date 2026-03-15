# Quality Gate

Read this file before declaring the translation complete.

## Acceptance Checklist

- Every source page has been inspected.
- If arXiv source was available, it was fetched and used as the primary textual source instead of relying on PDF extraction alone.
- The Chinese output includes title, authors, affiliations, abstract, keywords, body, acknowledgements, appendices, and references when present in the source.
- No section is summarized or omitted because extraction was messy.
- The Chinese reads like natural academic prose rather than a line-by-line rewrite of English syntax.
- Specialized technical terms use `中文术语（English Term）` on first appearance, and later mentions stay terminologically consistent.
- All displayed equations from the source appear in the Chinese LaTeX.
- All figure/table references in prose still point to an inserted image or a preserved float.
- Every cropped image has a translated caption outside the image.
- Every cropped image has passed visual review in `latex/figures/review/index.html`.
- The bibliography is complete and ordered consistently with the source.
- The final LaTeX compiles cleanly, or the only blocker is a missing local LaTeX engine.
- When compilation succeeds, the delivered PDF filename matches `[original paper title].pdf`, except for minimal sanitization of OS-invalid filename characters.

## Content Rules

- Translate semantics, not typography artifacts.
- Prefer fluent Chinese clause order and punctuation over literal English sentence shape.
- Split or merge sentences when needed for readability, but do not weaken claims, omit qualifiers, or compress arguments.
- Use English-in-parentheses only on the first meaningful occurrence of specialized terms unless repeated annotation is needed to avoid ambiguity.
- Preserve inline math, operators, and notation exactly.
- Preserve citation markers such as `[12]`, `(Smith et al., 2020)`, or `Eq. (4)` and localize only the surrounding prose.
- Keep URLs, DOI strings, email addresses, and code identifiers unchanged unless the source has obvious OCR damage.

## Figures and Tables

- Keep figure and table bodies as images when translating internal labels would require redrawing the asset.
- Translate only the caption, notes outside the image, and surrounding discussion.
- Crop tightly enough to avoid unrelated text, but keep any legend or axis labels that are part of the original figure/table image.
- Never leave the original English caption or adjacent body paragraph inside a page crop.
- If a standalone source figure file exists, prefer it over re-cropping the figure from the paper page.
- If multiple small subfigures belong to one logical figure, crop them together unless the source discusses them separately.

## Common Failure Cases

- Dropping appendix proofs or supplementary tables.
- Translating only the main body while leaving the abstract or references untouched.
- Producing stiff, word-for-word Chinese that preserves English grammar instead of meaning.
- Forgetting to annotate the first occurrence of a specialized term with the original English, or annotating every occurrence until the prose becomes noisy.
- Recreating a table in LaTeX and accidentally losing rows, merged cells, or footnotes.
- Converting formulas into plain text.
- Forgetting page-spanning figures or tables that continue across pages.
- Clipping table borders, axis labels, or legends because the crop box was too tight.
- Leaving English captions or neighboring paragraphs inside the exported figure/table image.
- Cropping a figure from the page even though the source package already contained the original figure asset.

## Minimal Sign-Off

Before closing the task, be able to state:

- where the source PDF lives
- where the Chinese LaTeX entrypoint lives
- where the cropped figure/table images live
- whether PDF compilation succeeded and, if not, which exact compiler is missing
- what the final PDF filename is
