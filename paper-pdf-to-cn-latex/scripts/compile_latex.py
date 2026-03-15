#!/usr/bin/env python3
"""Compile a LaTeX project with repeated XeLaTeX runs."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path


WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def sanitize_pdf_filename(title: str) -> str:
    cleaned = re.sub(r'[\x00-\x1f<>:"/\\|?*]+', " ", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(". ")
    if not cleaned:
        cleaned = "translated-paper"
    if cleaned.upper() in WINDOWS_RESERVED_NAMES:
        cleaned = f"{cleaned}-paper"
    return f"{cleaned}.pdf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile a LaTeX project with repeated XeLaTeX runs."
    )
    parser.add_argument("latex_dir", type=Path, help="Directory containing main.tex")
    parser.add_argument(
        "--main",
        default="main.tex",
        help="Main LaTeX file relative to latex_dir (default: main.tex)",
    )
    parser.add_argument(
        "--engine",
        default="xelatex",
        help="LaTeX engine to invoke (default: xelatex)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=2,
        help="How many compilation passes to run (default: 2)",
    )
    parser.add_argument(
        "--title",
        help=(
            "Original English paper title. When provided, rename the compiled PDF "
            "to <title>.pdf after sanitizing OS-invalid filename characters."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    latex_dir = args.latex_dir.resolve()
    main_file = latex_dir / args.main

    if not latex_dir.is_dir():
        raise SystemExit(f"LaTeX directory not found: {latex_dir}")
    if not main_file.is_file():
        raise SystemExit(f"Main LaTeX file not found: {main_file}")
    if args.runs <= 0:
        raise SystemExit("--runs must be a positive integer")

    engine = shutil.which(args.engine)
    if not engine:
        raise SystemExit(
            f"LaTeX engine '{args.engine}' was not found on PATH. Install it or compile manually."
        )

    command = [
        engine,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        args.main,
    ]
    for _ in range(args.runs):
        subprocess.run(command, cwd=latex_dir, check=True)

    output_pdf = latex_dir / f"{main_file.stem}.pdf"
    if not output_pdf.is_file():
        raise SystemExit(f"Expected compiled PDF was not produced: {output_pdf}")

    if args.title:
        renamed_pdf = output_pdf.with_name(sanitize_pdf_filename(args.title))
        if renamed_pdf != output_pdf:
            if renamed_pdf.exists():
                renamed_pdf.unlink()
            output_pdf.replace(renamed_pdf)
        output_pdf = renamed_pdf

    print(
        f"Compiled {main_file} with {args.engine} for {args.runs} pass(es). "
        f"Final PDF: {output_pdf}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
