#!/usr/bin/env python3
"""Initialize a paper translation workspace from a source PDF."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz


ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "latex-template"


TRANSLATION_PLAN_TEMPLATE = """# Translation Plan

## Source package

- Original English title:
- Final PDF filename:
- arXiv ID:
- arXiv source directory:
- Source-package notes:

## Section map

- Front matter:
- Main sections:
- Back matter:

## Readability reminders

- Write publication-style Chinese, not word-for-word English.
- Reorder clauses, split long sentences, or merge short fragments when needed.
- Preserve the paper's technical meaning, qualifiers, and argumentative structure.

## Terminology sheet

Record specialized terms that should appear as `中文术语（English Term）` on first mention in the delivered document. After first mention, reuse the agreed Chinese term or abbreviation consistently.

| First mention | Chinese term | Original English | Later form | Notes |
| --- | --- | --- | --- | --- |
| Abstract / Sec. 1 |  |  |  |  |

## Figure and table placement

- Figure/Table:
- Source page or source file:
- Chinese caption:
"""


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-") or "paper-job"


def copy_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        target = destination / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def round_box(rect: tuple[float, float, float, float]) -> list[float]:
    return [round(value, 2) for value in rect]


def sanitize_for_json(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, fitz.Point):
        return [round(value.x, 2), round(value.y, 2)]
    if isinstance(value, fitz.Rect):
        return round_box((value.x0, value.y0, value.x1, value.y1))
    if isinstance(value, dict):
        return {
            str(key): sanitize_for_json(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_json(item) for item in value]
    return str(value)


def extract_text(block: dict[str, Any]) -> tuple[str, float, list[str]]:
    lines: list[str] = []
    max_size = 0.0
    fonts: set[str] = set()
    for line in block.get("lines", []):
        fragments: list[str] = []
        for span in line.get("spans", []):
            text = span.get("text", "")
            if text:
                fragments.append(text)
            size = float(span.get("size", 0.0))
            max_size = max(max_size, size)
            font_name = span.get("font")
            if font_name:
                fonts.add(str(font_name))
        if fragments:
            joined = "".join(fragments).rstrip()
            if joined:
                lines.append(joined)
    text = "\n".join(lines).strip()
    return text, round(max_size, 2), sorted(fonts)


def manifest_for_page(page: fitz.Page) -> dict[str, Any]:
    page_dict = page.get_text("dict", sort=True)
    blocks: list[dict[str, Any]] = []
    for index, block in enumerate(page_dict.get("blocks", []), start=1):
        block_type = block.get("type", -1)
        entry: dict[str, Any] = {
            "id": f"block-{index:04d}",
            "bbox": round_box(tuple(block.get("bbox", (0, 0, 0, 0)))),
        }
        if block_type == 0:
            text, max_size, fonts = extract_text(block)
            entry.update(
                {
                    "type": "text",
                    "text": text,
                    "word_count": len(text.split()),
                    "max_font_size": max_size,
                    "fonts": fonts,
                }
            )
        elif block_type == 1:
            entry.update(
                {
                    "type": "image",
                    "width": int(block.get("width", 0)),
                    "height": int(block.get("height", 0)),
                    "ext": block.get("ext"),
                }
            )
        else:
            entry["type"] = f"other:{block_type}"
        blocks.append(entry)

    return {
        "page": page.number + 1,
        "size_pt": [round(page.rect.width, 2), round(page.rect.height, 2)],
        "rotation": page.rotation,
        "blocks": blocks,
    }


def render_pages(document: fitz.Document, output_dir: Path, dpi: int) -> None:
    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    for page in document:
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        output_path = output_dir / f"page-{page.number + 1:04d}.png"
        pixmap.save(output_path)


def extract_job(source_pdf: Path, output_dir: Path, dpi: int) -> dict[str, Any]:
    source_dir = output_dir / "source"
    work_dir = output_dir / "work"
    page_images_dir = work_dir / "page-images"
    latex_dir = output_dir / "latex"
    figures_dir = latex_dir / "figures"

    for directory in (source_dir, work_dir, page_images_dir, latex_dir, figures_dir):
        directory.mkdir(parents=True, exist_ok=True)

    copied_pdf = source_dir / "source.pdf"
    shutil.copy2(source_pdf, copied_pdf)
    copy_tree(ASSETS_DIR, latex_dir)

    with fitz.open(source_pdf) as document:
        render_pages(document, page_images_dir, dpi)
        page_manifest = [manifest_for_page(page) for page in document]
        toc = document.get_toc(simple=False)
        metadata = document.metadata

    page_manifest_path = work_dir / "page-manifest.json"
    page_manifest_path.write_text(
        json.dumps(page_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    source_text_lines: list[str] = []
    for page in page_manifest:
        source_text_lines.append(f"===== Page {page['page']} =====")
        for block in page["blocks"]:
            if block["type"] == "text" and block["text"]:
                source_text_lines.append(block["text"])
        source_text_lines.append("")
    (work_dir / "source-text.txt").write_text(
        "\n".join(source_text_lines).strip() + "\n",
        encoding="utf-8",
    )
    (work_dir / "translation-plan.md").write_text(
        TRANSLATION_PLAN_TEMPLATE,
        encoding="utf-8",
    )

    region_example = {
        "meta": {
            "unit": "pt",
            "render_dpi": dpi,
            "notes": "Use page numbers starting at 1. bbox uses [x0, y0, x1, y1]. Exclude English captions/body text from page crops. Set unit to px to use page-image pixel coordinates. When a standalone source figure exists, prefer source_file over page cropping.",
        },
        "regions": [
            {
                "id": "fig-1",
                "page": 1,
                "bbox": [72, 220, 520, 450],
                "kind": "figure",
                "filename": "fig-1.png",
                "caption": "图 1",
            },
            {
                "id": "fig-2-from-source",
                "kind": "figure",
                "source_file": "../source/figures/figure-2.pdf",
                "source_page": 1,
                "filename": "fig-2.png",
                "caption": "图 2",
            }
        ],
    }
    (work_dir / "regions.example.json").write_text(
        json.dumps(region_example, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    job_manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_pdf": str(copied_pdf.relative_to(output_dir)),
        "page_count": len(page_manifest),
        "render_dpi": dpi,
        "latex_entrypoint": "latex/main.tex",
        "page_manifest": "work/page-manifest.json",
        "source_text": "work/source-text.txt",
        "translation_plan": "work/translation-plan.md",
        "regions_manifest_example": "work/regions.example.json",
        "pdf_metadata": sanitize_for_json(metadata),
        "toc": sanitize_for_json(toc),
    }
    (output_dir / "project.json").write_text(
        json.dumps(job_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return job_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a translation workspace for an English paper PDF."
    )
    parser.add_argument("source_pdf", type=Path, help="Path to the source PDF")
    parser.add_argument("output_dir", type=Path, help="Destination working directory")
    parser.add_argument(
        "--title",
        help="Optional short title for logging only; when omitted the source filename is used",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=180,
        help="Render DPI for page reference images (default: 180)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow writing into an existing non-empty output directory",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_pdf = args.source_pdf.resolve()
    output_dir = args.output_dir.resolve()
    title = args.title or slugify(source_pdf.stem)

    if not source_pdf.is_file():
        raise SystemExit(f"Source PDF not found: {source_pdf}")
    if args.dpi <= 0:
        raise SystemExit("--dpi must be a positive integer")
    if output_dir.exists() and any(output_dir.iterdir()) and not args.force:
        raise SystemExit(
            f"Output directory is not empty: {output_dir}. Use --force to continue."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    job_manifest = extract_job(source_pdf, output_dir, args.dpi)
    summary = {
        "title": title,
        "output_dir": str(output_dir),
        "page_count": job_manifest["page_count"],
        "render_dpi": job_manifest["render_dpi"],
        "latex_entrypoint": job_manifest["latex_entrypoint"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
