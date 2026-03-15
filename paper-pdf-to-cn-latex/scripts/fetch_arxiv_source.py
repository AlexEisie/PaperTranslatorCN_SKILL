#!/usr/bin/env python3
"""Detect and fetch an arXiv source package for a paper."""

from __future__ import annotations

import argparse
import gzip
import io
import json
import re
import tarfile
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import quote

import fitz


ARXIV_URL_RE = re.compile(
    r"(?:https?://)?(?:export\.)?arxiv\.org/"
    r"(?:abs|pdf|e-print)/(?P<id>[A-Za-z0-9._/-]+)",
    re.IGNORECASE,
)
ARXIV_NEW_ID_RE = re.compile(
    r"(?<!\d)(?:arxiv:)?(?P<id>\d{4}\.\d{4,5}(?:v\d+)?)(?!\d)",
    re.IGNORECASE,
)
ARXIV_OLD_ID_RE = re.compile(
    r"(?<![A-Za-z0-9._/-])(?:arxiv:)?"
    r"(?P<id>[A-Za-z-]+(?:\.[A-Za-z-]+)?/\d{7}(?:v\d+)?)",
    re.IGNORECASE,
)
FIGURE_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Detect an arXiv identifier from a PDF path, arXiv URL, or arXiv ID, "
            "then download and extract the arXiv source package."
        )
    )
    parser.add_argument(
        "paper",
        help="Path to a paper PDF, arXiv URL, or arXiv identifier.",
    )
    parser.add_argument(
        "output_dir",
        nargs="?",
        type=Path,
        help="Directory to extract the arXiv source package into.",
    )
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="Only detect and print the arXiv identifier without downloading anything.",
    )
    parser.add_argument(
        "--base-url",
        default="https://export.arxiv.org/e-print",
        help="Base URL for arXiv source downloads (default: https://export.arxiv.org/e-print).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow writing into an existing non-empty output directory.",
    )
    return parser.parse_args()


def detect_arxiv_id(text: str) -> str | None:
    match = ARXIV_URL_RE.search(text)
    if match:
        candidate = match.group("id")
        candidate = candidate.removesuffix(".pdf")
        return candidate.strip().rstrip("/")

    for pattern in (ARXIV_NEW_ID_RE, ARXIV_OLD_ID_RE):
        match = pattern.search(text)
        if match:
            return match.group("id").strip()
    return None


def detect_from_pdf(pdf_path: Path) -> tuple[str | None, dict[str, Any]]:
    detection: dict[str, Any] = {
        "input_type": "pdf",
        "pdf_path": str(pdf_path),
    }

    with fitz.open(pdf_path) as document:
        pdf_metadata = document.metadata or {}
        samples = [
            pdf_metadata.get("title", ""),
            pdf_metadata.get("subject", ""),
            pdf_metadata.get("keywords", ""),
            pdf_path.stem,
        ]
        pages_to_scan = min(3, len(document))
        for index in range(pages_to_scan):
            samples.append(document.load_page(index).get_text("text"))

    combined = "\n".join(sample for sample in samples if sample)
    arxiv_id = detect_arxiv_id(combined)
    detection["pages_scanned"] = pages_to_scan
    detection["pdf_metadata"] = {key: value for key, value in pdf_metadata.items() if value}
    return arxiv_id, detection


def resolve_arxiv_id(paper: str) -> tuple[str | None, dict[str, Any]]:
    candidate_path = Path(paper)
    if candidate_path.is_file() and candidate_path.suffix.lower() == ".pdf":
        return detect_from_pdf(candidate_path.resolve())

    return detect_arxiv_id(paper), {
        "input_type": "string",
        "input_value": paper,
    }


def safe_extract_tar(archive: tarfile.TarFile, destination: Path) -> list[str]:
    destination = destination.resolve()
    members = archive.getmembers()
    for member in members:
        member_path = (destination / member.name).resolve()
        if member_path != destination and destination not in member_path.parents:
            raise SystemExit(f"Unsafe archive member path: {member.name}")
    archive.extractall(destination)
    return sorted(
        str((destination / member.name).resolve().relative_to(destination))
        for member in members
        if member.name and member.name != "."
    )


def write_single_file(payload: bytes, destination: Path) -> tuple[list[str], str]:
    is_likely_tex = b"\\documentclass" in payload or b"\\begin{document}" in payload
    filename = "source.tex" if is_likely_tex else "source.bin"
    output_path = destination / filename
    output_path.write_bytes(payload)
    return [filename], "single-file"


def extract_payload(payload: bytes, destination: Path) -> tuple[list[str], str]:
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
            return safe_extract_tar(archive, destination), "tar"
    except tarfile.ReadError:
        pass

    try:
        decompressed = gzip.decompress(payload)
    except OSError:
        return write_single_file(payload, destination)

    try:
        with tarfile.open(fileobj=io.BytesIO(decompressed), mode="r:*") as archive:
            return safe_extract_tar(archive, destination), "tar.gz"
    except tarfile.ReadError:
        return write_single_file(decompressed, destination)


def collect_files(output_dir: Path, pattern: str) -> list[str]:
    return sorted(str(path.relative_to(output_dir)) for path in output_dir.rglob(pattern))


def collect_figure_files(output_dir: Path) -> list[str]:
    figures: list[str] = []
    for path in output_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in FIGURE_SUFFIXES:
            figures.append(str(path.relative_to(output_dir)))
    return sorted(figures)


def download_source(base_url: str, arxiv_id: str) -> tuple[bytes, str]:
    quoted_id = quote(arxiv_id, safe="/.")
    url = f"{base_url.rstrip('/')}/{quoted_id}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "paper-pdf-to-cn-latex/1.0"},
    )
    with urllib.request.urlopen(request) as response:
        return response.read(), response.geturl()


def main() -> int:
    args = parse_args()

    arxiv_id, detection = resolve_arxiv_id(args.paper)
    if not arxiv_id:
        raise SystemExit("Could not detect an arXiv identifier from the provided input.")

    result: dict[str, Any] = {
        "arxiv_id": arxiv_id,
        "detection": detection,
    }
    if args.detect_only:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.output_dir is None:
        raise SystemExit("output_dir is required unless --detect-only is used.")

    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()) and not args.force:
        raise SystemExit(
            f"Output directory is not empty: {output_dir}. Use --force to continue."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    payload, download_url = download_source(args.base_url, arxiv_id)
    archive_path = output_dir / "arxiv-source.download"
    archive_path.write_bytes(payload)
    extracted_files, archive_kind = extract_payload(payload, output_dir)

    manifest = {
        **result,
        "download_url": download_url,
        "archive_path": str(archive_path.relative_to(output_dir)),
        "archive_kind": archive_kind,
        "tex_files": collect_files(output_dir, "*.tex"),
        "bib_files": collect_files(output_dir, "*.bib"),
        "figure_files": collect_figure_files(output_dir),
        "extracted_files": extracted_files,
    }
    manifest_path = output_dir / "arxiv-source.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
