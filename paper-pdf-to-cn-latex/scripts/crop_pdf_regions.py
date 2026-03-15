#!/usr/bin/env python3
"""Crop figure/table regions from a PDF or figure asset based on a JSON manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import fitz


def load_manifest(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, list):
        return {}, raw
    if isinstance(raw, dict) and isinstance(raw.get("regions"), list):
        meta = raw.get("meta", {})
        if meta is None:
            meta = {}
        if not isinstance(meta, dict):
            raise SystemExit("Manifest meta must be an object when present.")
        return meta, raw["regions"]
    raise SystemExit("Manifest must be a list or an object with a 'regions' array.")


def resolve_source_path(source_file: str, manifest_path: Path, source_pdf: Path) -> Path:
    candidate = Path(source_file).expanduser()
    if candidate.is_absolute():
        return candidate

    manifest_relative = (manifest_path.parent / candidate).resolve()
    if manifest_relative.exists():
        return manifest_relative

    pdf_relative = (source_pdf.parent / candidate).resolve()
    if pdf_relative.exists():
        return pdf_relative

    return manifest_relative


def to_rect(
    region: dict[str, Any],
    meta: dict[str, Any],
    page: fitz.Page,
    render_dpi: int | None,
) -> fitz.Rect:
    bbox = region.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise SystemExit(f"Invalid bbox for region: {region}")
    try:
        x0, y0, x1, y1 = [float(value) for value in bbox]
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"bbox must contain numbers: {region}") from exc

    unit = region.get("unit") or meta.get("unit") or "pt"
    if unit == "px":
        dpi = region.get("render_dpi") or meta.get("render_dpi") or render_dpi
        if not dpi:
            raise SystemExit(
                "Pixel bbox requires render_dpi in the region, meta, or --render-dpi."
            )
        scale = 72.0 / float(dpi)
        x0, y0, x1, y1 = [value * scale for value in (x0, y0, x1, y1)]
    elif unit != "pt":
        raise SystemExit(f"Unsupported unit '{unit}'. Use 'pt' or 'px'.")

    margin = float(region.get("margin", 0.0))
    rect = fitz.Rect(x0 - margin, y0 - margin, x1 + margin, y1 + margin)
    rect = rect & page.rect
    if rect.is_empty or rect.width <= 0 or rect.height <= 0:
        raise SystemExit(f"Region bbox is empty after clipping: {region}")
    return rect


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crop figure/table regions from a PDF or standalone figure asset using a JSON manifest."
    )
    parser.add_argument("source_pdf", type=Path, help="Path to the source PDF")
    parser.add_argument("manifest_json", type=Path, help="JSON manifest describing regions")
    parser.add_argument("output_dir", type=Path, help="Directory for cropped PNG files")
    parser.add_argument(
        "--dpi",
        type=int,
        default=220,
        help="Render DPI for the cropped output images (default: 220)",
    )
    parser.add_argument(
        "--render-dpi",
        type=int,
        help="Render DPI used for page-image pixel coordinates when manifest unit=px",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.dpi <= 0:
        raise SystemExit("--dpi must be a positive integer")
    if args.render_dpi is not None and args.render_dpi <= 0:
        raise SystemExit("--render-dpi must be a positive integer")
    if not args.source_pdf.is_file():
        raise SystemExit(f"Source PDF not found: {args.source_pdf}")
    if not args.manifest_json.is_file():
        raise SystemExit(f"Manifest not found: {args.manifest_json}")

    meta, regions = load_manifest(args.manifest_json)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scale = args.dpi / 72.0
    matrix = fitz.Matrix(scale, scale)

    results: list[dict[str, Any]] = []
    with fitz.open(args.source_pdf) as document:
        for index, region in enumerate(regions, start=1):
            if not isinstance(region, dict):
                raise SystemExit(f"Each region must be an object: {region}")

            page_number: int | None = None
            source_file_value = region.get("source_file")
            source_path: Path | None = None
            source_page_number: int | None = None

            if source_file_value:
                if not isinstance(source_file_value, str):
                    raise SystemExit(f"source_file must be a string when present: {region}")
                source_path = resolve_source_path(
                    source_file_value,
                    args.manifest_json,
                    args.source_pdf,
                )
                if not source_path.is_file():
                    raise SystemExit(f"Source asset not found for region: {region}")

                with fitz.open(source_path) as asset_document:
                    source_page_number = region.get("source_page", 1)
                    if (
                        not isinstance(source_page_number, int)
                        or source_page_number < 1
                        or source_page_number > len(asset_document)
                    ):
                        raise SystemExit(f"Invalid source_page for region: {region}")
                    page = asset_document[source_page_number - 1]
                    rect = (
                        to_rect(region, meta, page, args.render_dpi)
                        if region.get("bbox") is not None
                        else page.rect
                    )
                    pixmap = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
            else:
                page_number = region.get("page")
                if (
                    not isinstance(page_number, int)
                    or page_number < 1
                    or page_number > len(document)
                ):
                    raise SystemExit(f"Invalid page number for region: {region}")
                page = document[page_number - 1]
                rect = to_rect(region, meta, page, args.render_dpi)
                pixmap = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)

            filename = region.get("filename") or f"{region.get('id', f'region-{index:04d}')}.png"
            output_path = args.output_dir / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            pixmap.save(output_path)

            results.append(
                {
                    "id": region.get("id", f"region-{index:04d}"),
                    "page": page_number,
                    "source_page": source_page_number,
                    "bbox_pt": [
                        round(rect.x0, 2),
                        round(rect.y0, 2),
                        round(rect.x1, 2),
                        round(rect.y1, 2),
                    ],
                    "output": str(output_path),
                    "source_file": str(source_path) if source_path else None,
                    "kind": region.get("kind"),
                    "caption": region.get("caption"),
                }
            )

    summary_path = args.output_dir / "cropped-regions.json"
    summary_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "cropped_count": len(results),
                "summary": str(summary_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
