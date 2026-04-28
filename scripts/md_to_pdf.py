#!/usr/bin/env python3
"""
md_to_pdf.py — Convert markdown files to styled PDFs using Chrome headless.

Requirements (already installed in this pipeline):
  - python3 with `markdown` library  (pip install markdown)
  - Google Chrome at /Applications/Google Chrome.app

Usage:
  # Single file, output to Desktop (default)
  python3 scripts/md_to_pdf.py references/analyses/001-acme-interview-prep-2026-01-15.md

  # Multiple files
  python3 scripts/md_to_pdf.py file1.md file2.md

  # Custom output directory
  python3 scripts/md_to_pdf.py file1.md --out ~/Documents/output

  # Custom output filename (single file only)
  python3 scripts/md_to_pdf.py file1.md --name my-doc.pdf

How it works:
  1. Converts each .md to styled HTML in /tmp/
  2. Calls Chrome --headless=new --print-to-pdf on each HTML file
  3. Writes PDF to output directory
  4. Cleans up temp HTML files

Known behavior:
  - Chrome emits macOS task_policy_set warnings to stderr — these are harmless,
    the PDF still writes correctly. Suppress with 2>/dev/null if needed.
  - Output filename defaults to the input stem (e.g., foo.md -> foo.pdf)
"""

import argparse
import markdown
import os
import pathlib
import subprocess
import sys
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #1a1a1a;
    max-width: 820px;
    margin: 0 auto;
    padding: 2.5rem 2rem;
  }
  h1 { font-size: 1.7em; border-bottom: 2px solid #333; padding-bottom: 0.3em; margin-top: 1.5em; }
  h2 { font-size: 1.3em; border-bottom: 1px solid #ccc; padding-bottom: 0.2em; margin-top: 1.4em; }
  h3 { font-size: 1.1em; margin-top: 1.2em; color: #222; }
  h4 { font-size: 1em; color: #444; margin-top: 1em; }
  code {
    background: #f4f4f4;
    border-radius: 3px;
    padding: 0.1em 0.3em;
    font-size: 0.9em;
    font-family: "SF Mono", Menlo, Consolas, monospace;
  }
  pre {
    background: #f4f4f4;
    border-left: 3px solid #999;
    padding: 0.8em 1em;
    overflow-x: auto;
    font-size: 0.9em;
  }
  pre code { background: none; padding: 0; }
  blockquote {
    border-left: 4px solid #0066cc;
    margin: 1em 0;
    padding: 0.5em 1em;
    background: #f0f5ff;
    color: #333;
  }
  table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.95em; }
  th { background: #f0f0f0; padding: 0.5em 0.75em; border: 1px solid #ccc; text-align: left; }
  td { padding: 0.4em 0.75em; border: 1px solid #ccc; }
  tr:nth-child(even) td { background: #fafafa; }
  hr { border: none; border-top: 1px solid #ddd; margin: 1.5em 0; }
  ul, ol { padding-left: 1.5em; }
  li { margin-bottom: 0.3em; }
  a { color: #0066cc; }
  strong { color: #111; }
  @media print {
    body { max-width: 100%; padding: 1rem; }
    h1, h2, h3 { page-break-after: avoid; }
    pre, table, blockquote { page-break-inside: avoid; }
  }
</style>
"""


def md_to_html(md_path: pathlib.Path) -> str:
    text = md_path.read_text(encoding="utf-8")
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'>{CSS}</head><body>{body}</body></html>"


def html_to_pdf(html_path: pathlib.Path, pdf_path: pathlib.Path) -> None:
    result = subprocess.run(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--print-to-pdf={pdf_path}",
            "--print-to-pdf-no-header",
            f"file://{html_path}",
        ],
        capture_output=True,
        text=True,
    )
    # Chrome writes the byte count to stderr on success, errors to stderr on failure.
    # Check the PDF actually landed rather than relying on return code.
    if not pdf_path.exists():
        print(f"  ERROR: PDF not created. Chrome stderr:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)


def convert(md_path: pathlib.Path, out_dir: pathlib.Path, name: str | None = None) -> pathlib.Path:
    pdf_name = name if name else md_path.stem + ".pdf"
    pdf_path = out_dir / pdf_name

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as f:
        f.write(md_to_html(md_path))
        tmp_html = pathlib.Path(f.name)

    try:
        html_to_pdf(tmp_html, pdf_path)
    finally:
        tmp_html.unlink(missing_ok=True)

    return pdf_path


def main():
    parser = argparse.ArgumentParser(description="Convert markdown files to PDF via Chrome headless.")
    parser.add_argument("files", nargs="+", help="Markdown file paths to convert")
    parser.add_argument(
        "--out",
        default=str(pathlib.Path.home() / "Desktop"),
        help="Output directory (default: ~/Desktop)",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Output filename override — single file only (e.g. my-doc.pdf)",
    )
    args = parser.parse_args()

    if args.name and len(args.files) > 1:
        print("ERROR: --name can only be used with a single input file.", file=sys.stderr)
        sys.exit(1)

    if not pathlib.Path(CHROME).exists():
        print(f"ERROR: Chrome not found at {CHROME}", file=sys.stderr)
        sys.exit(1)

    out_dir = pathlib.Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    for f in args.files:
        md_path = pathlib.Path(f).expanduser().resolve()
        if not md_path.exists():
            print(f"  SKIP: {f} not found", file=sys.stderr)
            continue

        print(f"  Converting {md_path.name} ...", end=" ", flush=True)
        pdf_path = convert(md_path, out_dir, args.name)
        size_kb = pdf_path.stat().st_size // 1024
        print(f"-> {pdf_path} ({size_kb}K)")


if __name__ == "__main__":
    main()
