#!/usr/bin/env python3
"""Generate a visual review page for cropped figure/table outputs."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
from typing import Any

import fitz

from crop_pdf_regions import load_manifest, resolve_source_path, to_rect


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create overlay previews and an HTML review page for cropped regions."
    )
    parser.add_argument("source_pdf", type=Path, help="Path to the source PDF")
    parser.add_argument("manifest_json", type=Path, help="JSON manifest describing regions")
    parser.add_argument("output_dir", type=Path, help="Directory containing cropped PNG files")
    parser.add_argument(
        "--review-dir",
        type=Path,
        help="Directory for review artifacts (default: <output_dir>/review)",
    )
    parser.add_argument(
        "--page-dpi",
        type=int,
        default=120,
        help="Render DPI for full-page overlay previews (default: 120)",
    )
    parser.add_argument(
        "--render-dpi",
        type=int,
        help="Render DPI used for page-image pixel coordinates when manifest unit=px",
    )
    return parser.parse_args()


def render_overlay(
    source_pdf: Path,
    page_number: int,
    rect: fitz.Rect,
    output_path: Path,
    dpi: int,
) -> None:
    with fitz.open(source_pdf) as document:
        page = document[page_number - 1]
        page.draw_rect(rect, color=(1, 0, 0), width=2)
        matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(output_path)


def relpath(path: Path, start: Path) -> str:
    return os.path.relpath(path, start).replace("\\", "/")


def build_card(region: dict[str, Any], body: str) -> str:
    region_id = html.escape(str(region.get("id", "")))
    kind = html.escape(str(region.get("kind") or "unknown"))
    page = region.get("page")
    source_file = region.get("source_file")
    caption = region.get("caption")

    lines = [f"<section class='card'><h2>{region_id}</h2>"]
    meta_parts = [f"kind: {kind}"]
    if isinstance(page, int):
        meta_parts.append(f"page: {page}")
    if source_file:
        meta_parts.append(f"source_file: {html.escape(str(source_file))}")
    if caption:
        meta_parts.append(f"caption: {html.escape(str(caption))}")
    lines.append(f"<p class='meta'>{' | '.join(meta_parts)}</p>")
    lines.append(body)
    lines.append("</section>")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    if args.page_dpi <= 0:
        raise SystemExit("--page-dpi must be a positive integer")
    if args.render_dpi is not None and args.render_dpi <= 0:
        raise SystemExit("--render-dpi must be a positive integer")
    if not args.source_pdf.is_file():
        raise SystemExit(f"Source PDF not found: {args.source_pdf}")
    if not args.manifest_json.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest_json}")
    if not args.output_dir.is_dir():
        raise SystemExit(f"Output directory not found: {args.output_dir}")

    review_dir = args.review_dir or (args.output_dir / "review")
    overlay_dir = review_dir / "overlays"
    review_dir.mkdir(parents=True, exist_ok=True)
    overlay_dir.mkdir(parents=True, exist_ok=True)

    meta, regions = load_manifest(args.manifest_json)
    cards: list[str] = []
    summary: list[dict[str, Any]] = []

    with fitz.open(args.source_pdf) as document:
        page_count = len(document)

        for index, region in enumerate(regions, start=1):
            if not isinstance(region, dict):
                raise SystemExit(f"Each region must be an object: {region}")

            region_id = str(region.get("id", f"region-{index:04d}"))
            filename = region.get("filename") or f"{region_id}.png"
            crop_path = (args.output_dir / filename).resolve()
            if not crop_path.is_file():
                raise SystemExit(
                    f"Cropped output not found for region '{region_id}': {crop_path}"
                )

            crop_rel = relpath(crop_path, review_dir)
            source_file_value = region.get("source_file")

            if source_file_value:
                if not isinstance(source_file_value, str):
                    raise SystemExit(f"source_file must be a string when present: {region}")
                source_path = resolve_source_path(
                    source_file_value,
                    args.manifest_json,
                    args.source_pdf,
                )
                if not source_path.is_file():
                    raise SystemExit(
                        f"Source asset not found for region '{region_id}': {source_path}"
                    )
                body = "\n".join(
                    [
                        "<p class='note'>Rendered from a standalone source asset. Verify that page cropping was not needed for this figure.</p>",
                        f"<div class='single'><figure><figcaption>Cropped output</figcaption><img src='{html.escape(crop_rel)}' alt='cropped output'></figure></div>",
                    ]
                )
                cards.append(build_card(region, body))
                summary.append(
                    {
                        "id": region_id,
                        "review_type": "source-file",
                        "crop_output": str(crop_path),
                        "source_file": str(source_path),
                    }
                )
                continue

            page_number = region.get("page")
            if not isinstance(page_number, int) or page_number < 1 or page_number > page_count:
                raise SystemExit(f"Invalid page number for region '{region_id}': {region}")

            rect = to_rect(region, meta, document[page_number - 1], args.render_dpi)
            overlay_path = overlay_dir / f"{region_id}.png"
            render_overlay(args.source_pdf, page_number, rect, overlay_path, args.page_dpi)
            overlay_rel = relpath(overlay_path, review_dir)

            body = "\n".join(
                [
                    "<div class='grid'>",
                    f"<figure><figcaption>Page overlay</figcaption><img src='{html.escape(overlay_rel)}' alt='page overlay'></figure>",
                    f"<figure><figcaption>Cropped output</figcaption><img src='{html.escape(crop_rel)}' alt='cropped output'></figure>",
                    "</div>",
                ]
            )
            cards.append(build_card(region, body))
            summary.append(
                {
                    "id": region_id,
                    "review_type": "page-crop",
                    "page": page_number,
                    "overlay": str(overlay_path),
                    "crop_output": str(crop_path),
                }
            )

    html_path = review_dir / "index.html"
    html_path.write_text(
        "\n".join(
            [
                "<!doctype html>",
                "<html lang='en'>",
                "<head>",
                "<meta charset='utf-8'>",
                "<title>Cropped Region Review</title>",
                "<style>",
                "body { font-family: Arial, sans-serif; margin: 24px; background: #f4f4f4; color: #111; }",
                "h1 { margin-bottom: 8px; }",
                ".meta { color: #444; font-size: 14px; }",
                ".note { margin: 8px 0 12px; color: #444; }",
                ".card { background: #fff; border: 1px solid #ddd; padding: 16px; margin: 0 0 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }",
                ".grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; align-items: start; }",
                ".single { max-width: 720px; }",
                "figure { margin: 0; }",
                "figcaption { font-weight: 600; margin-bottom: 8px; }",
                "img { width: 100%; height: auto; border: 1px solid #ccc; background: #fff; }",
                "</style>",
                "</head>",
                "<body>",
                "<h1>Cropped Region Review</h1>",
                "<p>Check every page overlay for cut edges, missing legends, and accidental English captions/body text in the crop.</p>",
                *cards,
                "</body>",
                "</html>",
            ]
        ),
        encoding="utf-8",
    )

    summary_path = review_dir / "review-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "review_count": len(summary),
                "html": str(html_path),
                "summary": str(summary_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
