#!/usr/bin/env python3
"""Convert a PDF or image to Markdown with MinerU, then flatten and QC the result.

MinerU writes a nested, backend-dependent tree (out/<stem>/<backend>/<stem>.md
plus several debug artefacts). Consumers almost always want just the Markdown
and its images side by side, so this script normalises the layout to:

    <output-dir>/
    ├── <stem>.md
    └── images/

It also runs a quality report, because a document parse that "succeeded" can
still have silently dropped pages — the exit status of `mineru` alone does not
tell you whether the output is usable.

Usage:
    mineru_convert.py INPUT [-o OUTPUT_DIR] [--backend ...] [--server-url URL]
                            [--lang LANG] [--start N] [--end N]
                            [--venv PATH] [--keep-raw] [--no-check] [--dry-run]
    mineru_convert.py --check-only OUTPUT_DIR [--source PDF]
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mineru_env import DEFAULT_VENV, find_mineru, inspect  # noqa: E402

SUPPORTED_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
HTTP_CLIENT_BACKENDS = {"vlm-http-client", "hybrid-http-client"}
# `-l` only affects the OCR models used by the pipeline backend, and the CLI
# restricts it to non-Latin scripts. Italian and English need no flag at all.
LANG_BACKENDS = {"pipeline"}
VALID_LANGS = {"ch", "ch_server", "korean", "ta", "te", "ka", "th", "el",
               "arabic", "east_slavic", "cyrillic", "devanagari"}

IMAGE_REF_RE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
MD_TABLE_SEP_RE = re.compile(r"^\s*\|[\s:|-]{3,}\|\s*$", re.MULTILINE)
HEADING_RE = re.compile(r"^#{1,6}\s+\S", re.MULTILINE)


def build_command(executable, source, raw_dir, backend, server_url, lang, start, end):
    cmd = [executable, "-p", str(source), "-o", str(raw_dir), "-b", backend]
    if backend in HTTP_CLIENT_BACKENDS:
        if not server_url:
            raise SystemExit(
                f"backend {backend} needs a server URL (--server-url or "
                "MINERU_SERVER_URL)")
        cmd += ["-u", server_url]
    if lang:
        if lang not in VALID_LANGS:
            raise SystemExit(
                f"unsupported --lang {lang!r}; the CLI accepts {sorted(VALID_LANGS)}. "
                "Latin-script languages such as Italian and English are the default "
                "and need no --lang.")
        if backend not in LANG_BACKENDS:
            raise SystemExit(
                f"--lang is only honoured by the pipeline backend, not {backend}")
        cmd += ["-l", lang]
    if start is not None:
        cmd += ["-s", str(start)]
    if end is not None:
        cmd += ["-e", str(end)]
    return cmd


def pick_markdown(raw_dir, stem):
    candidates = [p for p in raw_dir.rglob("*.md")]
    if not candidates:
        return None
    exact = [p for p in candidates if p.stem == stem]
    pool = exact or candidates
    return max(pool, key=lambda p: p.stat().st_size)


def flatten(raw_dir, output_dir, stem):
    """Move the Markdown and its images out of MinerU's nested output tree."""
    markdown = pick_markdown(raw_dir, stem)
    if markdown is None:
        return None, None, None

    output_dir.mkdir(parents=True, exist_ok=True)
    target_md = output_dir / f"{stem}.md"
    shutil.copyfile(markdown, target_md)

    # Relative image links stay valid as long as images/ sits next to the .md.
    source_images = markdown.parent / "images"
    target_images = output_dir / "images"
    if source_images.is_dir():
        if target_images.exists():
            shutil.rmtree(target_images)
        shutil.copytree(source_images, target_images)

    content_list = next(iter(sorted(raw_dir.rglob("*content_list.json"))), None)
    return target_md, target_images if target_images.exists() else None, content_list


def pdf_text_layer(source):
    """Characters per page in the PDF's own text layer, or None if unavailable.

    This is the reference the parse can be measured against. A digital PDF whose
    text layer holds 176k characters but yields 24k of Markdown has silently
    lost most of the document, and nothing in MinerU's exit status says so.
    Scanned PDFs have no text layer, so the caller must treat a near-zero total
    as "no reference available" rather than as a perfect score.
    """
    if source is None or Path(source).suffix.lower() != ".pdf":
        return None
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(source))
    except Exception:
        return None
    counts = []
    for page in reader.pages:
        try:
            counts.append(len((page.extract_text() or "").strip()))
        except Exception:
            counts.append(0)
    return counts


def pdf_page_count(source):
    if source is None or Path(source).suffix.lower() != ".pdf":
        return None
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        try:
            out = subprocess.run([pdfinfo, str(source)], capture_output=True,
                                 text=True, timeout=60, check=True).stdout
            for line in out.splitlines():
                if line.startswith("Pages:"):
                    return int(line.split(":", 1)[1].strip())
        except (subprocess.SubprocessError, OSError, ValueError):
            pass
    return None


def quality_report(markdown_path, content_list_path=None, source=None, backend=None,
                   page_range=None):
    """Summarise what came out, and flag the failure modes that stay silent."""
    text = markdown_path.read_text(encoding="utf-8", errors="replace")
    image_refs = IMAGE_REF_RE.findall(text)
    missing_images = sorted({
        ref for ref in image_refs
        if not ref.startswith(("http://", "https://", "data:"))
        and not (markdown_path.parent / ref).exists()
    })

    report = {
        "markdown": str(markdown_path),
        "characters": len(text),
        "headings": len(HEADING_RE.findall(text)),
        "html_tables": text.count("<table"),
        "markdown_tables": len(MD_TABLE_SEP_RE.findall(text)),
        "formula_blocks": text.count("$$") // 2,
        "image_references": len(image_refs),
        "missing_images": missing_images,
        "backend": backend,
        "warnings": [],
    }

    text_layer = pdf_text_layer(source)
    source_pages = len(text_layer) if text_layer else pdf_page_count(source)
    seen = set()
    if content_list_path and Path(content_list_path).is_file():
        try:
            items = json.loads(Path(content_list_path).read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            items = []
        if isinstance(items, list):
            seen = {item.get("page_idx") for item in items
                    if isinstance(item, dict) and item.get("page_idx") is not None}

    # Only the pages actually requested count as expected output — otherwise a
    # deliberate --start/--end range would look like a massive parsing failure.
    start, end = page_range or (None, None)
    last = source_pages - 1 if source_pages else (max(seen) if seen else None)
    if end is not None and last is not None:
        last = min(end, last)
    elif end is not None:
        last = end
    expected = list(range(start or 0, last + 1)) if last is not None else []

    report["source_pages"] = source_pages
    report["expected_pages"] = len(expected) or None
    report["pages_with_content"] = len(seen) if seen else None
    report["empty_pages"] = [p for p in expected if p not in seen] if seen else []
    empty_pages = report["empty_pages"]

    # An empty page is only worth alarm when the source proves there was text on
    # it — otherwise it is a frontispiece or a separator and flagging it is noise.
    lost_pages = []
    coverage = None
    if text_layer:
        lost_pages = [p for p in empty_pages
                      if p < len(text_layer) and text_layer[p] > 100]
        reference = sum(text_layer[p] for p in expected if p < len(text_layer))
        if reference > 500:
            coverage = round(report["characters"] / reference, 3)
    report["lost_pages"] = lost_pages
    report["text_coverage"] = coverage

    if report["characters"] < 200:
        report["warnings"].append(
            "the Markdown is nearly empty — the source is likely a scan the backend "
            "could not read, or the wrong page range was requested")
    if lost_pages:
        report["warnings"].append(
            f"CONTENT LOST on {len(lost_pages)} page(s): "
            f"{lost_pages[:10]}{' …' if len(lost_pages) > 10 else ''} — the source "
            "has text there but the parse produced nothing")
    elif empty_pages and text_layer:
        report["warnings"].append(
            f"{len(empty_pages)} page(s) produced no content, but they are blank in "
            "the source too, so this is expected")
    elif empty_pages:
        report["warnings"].append(
            f"{len(empty_pages)} page(s) produced no content: "
            f"{empty_pages[:10]}{' …' if len(empty_pages) > 10 else ''} — check "
            "whether they are blank in the original")
    if coverage is not None and coverage < 0.6:
        report["warnings"].append(
            f"only {coverage:.0%} of the text in the source's own text layer made it "
            "into the Markdown — a large part of the document is missing")
    if missing_images:
        report["warnings"].append(
            f"{len(missing_images)} image reference(s) point to files that do not "
            "exist next to the Markdown")
    if coverage is None and expected and report["characters"] / len(expected) < 150:
        report["warnings"].append(
            "very low text density per page — check a few pages against the original")
    if backend == "pipeline":
        report["warnings"].append(
            "the pipeline backend was used, so MinerU2.5-Pro was NOT involved; "
            "tables and formulas are noticeably weaker than with a vlm-* backend")

    report["ok"] = (report["characters"] >= 200 and not missing_images
                    and not lost_pages and (coverage is None or coverage >= 0.6))
    return report


def print_report(report):
    print("\n=== MinerU quality report ===", file=sys.stderr)
    print(f"Markdown:       {report['markdown']}", file=sys.stderr)
    print(f"Backend:        {report['backend'] or 'unknown'}", file=sys.stderr)
    print(f"Characters:     {report['characters']:,}", file=sys.stderr)
    pages = (f"{report.get('pages_with_content')} with content "
             f"/ {report.get('expected_pages')} requested")
    if report.get("source_pages"):
        pages += f" (source has {report['source_pages']})"
    print(f"Pages:          {pages}", file=sys.stderr)
    if report.get("text_coverage") is not None:
        print(f"Text coverage:  {report['text_coverage']:.0%} of the source text layer",
              file=sys.stderr)
    print(f"Headings:       {report['headings']}", file=sys.stderr)
    print(f"Tables:         {report['html_tables']} HTML + "
          f"{report['markdown_tables']} Markdown", file=sys.stderr)
    print(f"Formula blocks: {report['formula_blocks']}", file=sys.stderr)
    print(f"Images:         {report['image_references']} referenced, "
          f"{len(report['missing_images'])} missing", file=sys.stderr)
    for warning in report["warnings"]:
        print(f"  ! {warning}", file=sys.stderr)
    if not report["warnings"]:
        print("  no issues detected", file=sys.stderr)


def convert(args):
    source = Path(args.input).expanduser().resolve()
    if not source.is_file():
        raise SystemExit(f"input file not found: {source}")
    if source.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise SystemExit(
            f"unsupported input {source.suffix!r}; this skill handles "
            f"{sorted(SUPPORTED_SUFFIXES)}")

    venv = Path(args.venv)
    executable = find_mineru(venv)
    if not executable:
        raise SystemExit(
            "mineru not found. Run: python3 scripts/mineru_env.py install")

    backend = args.backend
    server_url = args.server_url
    if backend == "auto":
        info = inspect(server_url=server_url, venv=venv)
        backend = info["recommended_backend"]
        server_url = server_url or info["server"]["url"]
        print(f"Auto-selected backend {backend}: {info['reason']}", file=sys.stderr)

    output_dir = Path(args.output).expanduser().resolve() if args.output \
        else source.parent / f"{source.stem}-md"
    raw_dir = output_dir / ".mineru-raw"

    cmd = build_command(executable, source, raw_dir, backend, server_url,
                        args.lang, args.start, args.end)
    print("$ " + " ".join(cmd), file=sys.stderr)
    if args.dry_run:
        return {"dry_run": True, "command": cmd, "output_dir": str(output_dir)}

    raw_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(cmd)
    if completed.returncode != 0:
        raise SystemExit(f"mineru exited with status {completed.returncode}")

    markdown, images, content_list = flatten(raw_dir, output_dir, source.stem)
    if markdown is None:
        raise SystemExit(f"mineru produced no Markdown under {raw_dir}")

    result = {
        "input": str(source),
        "output_dir": str(output_dir),
        "markdown": str(markdown),
        "images_dir": str(images) if images else None,
        "backend": backend,
        "uses_mineru25pro": backend != "pipeline",
    }

    if not args.no_check:
        result["quality"] = quality_report(markdown, content_list, source, backend,
                                           page_range=(args.start, args.end))
        print_report(result["quality"])

    if not args.keep_raw:
        shutil.rmtree(raw_dir, ignore_errors=True)
    else:
        result["raw_dir"] = str(raw_dir)

    return result


def check_only(args):
    output_dir = Path(args.check_only).expanduser().resolve()
    markdown = next(iter(sorted(output_dir.glob("*.md"))), None)
    if markdown is None:
        raise SystemExit(f"no Markdown file found in {output_dir}")
    content_list = next(iter(sorted(output_dir.rglob("*content_list.json"))), None)
    backend = None if args.backend == "auto" else args.backend
    report = quality_report(markdown, content_list, args.source, backend,
                            page_range=(args.start, args.end))
    print_report(report)
    return {"quality": report}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", nargs="?", help="PDF or image to convert")
    parser.add_argument("-o", "--output", help="output directory "
                        "(default: <input-dir>/<stem>-md)")
    parser.add_argument("-b", "--backend", default="auto",
                        choices=["auto", "pipeline", "vlm-auto-engine",
                                 "hybrid-auto-engine", "vlm-http-client",
                                 "hybrid-http-client"])
    parser.add_argument("--server-url")
    parser.add_argument("--lang", help="OCR script hint, pipeline backend only")
    parser.add_argument("-s", "--start", type=int, help="first page, 0-based")
    parser.add_argument("-e", "--end", type=int, help="last page, 0-based")
    parser.add_argument("--venv", default=str(DEFAULT_VENV))
    parser.add_argument("--keep-raw", action="store_true",
                        help="keep MinerU's raw output tree (middle.json, layout PDFs)")
    parser.add_argument("--no-check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--check-only", metavar="OUTPUT_DIR",
                        help="only re-run the quality report on an existing output dir")
    parser.add_argument("--source", help="original PDF, for page-count checks "
                        "when using --check-only")
    args = parser.parse_args()

    if args.check_only:
        result = check_only(args)
    elif args.input:
        result = convert(args)
    else:
        parser.print_usage(sys.stderr)
        print("error: provide an input file or --check-only", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2))
    elif "markdown" in result:
        print(result["markdown"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
