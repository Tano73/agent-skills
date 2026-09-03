#!/usr/bin/env python3
"""Deterministic local health checks for an llm-wiki.

Catches the mechanical failures that are easy for an LLM to miss or invent:
dangling source slugs, broken relative links, pages missing from index.md,
orphan pages (no inbound links), and source_file paths that do not exist under
raw/. Semantic issues (contradictions, stale narrative, schema drift) stay with
the agent — this script only reports what the filesystem can prove.

Usage:
    wiki_lint.py <wiki-root> [--json] [--strict]

Exit codes:
    0 — no issues (or only info-level findings when --strict is off)
    1 — one or more high/medium severity issues
    2 — usage / path error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MD_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)\)")
SOURCES_FM_RE = re.compile(r"^sources:\s*\[(.*?)\]\s*$", re.MULTILINE | re.DOTALL)
SOURCE_FILE_RE = re.compile(r"^source_file:\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.MULTILINE)
SOURCES_SECTION_RE = re.compile(
    r"^##\s+Sources(?:\s*&?\s*Examples)?\s*\n(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
INDEX_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    meta: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip().strip("\"'")
    return meta, text[match.end():]


def parse_sources_list(text: str) -> list[str]:
    match = SOURCES_FM_RE.search(text)
    if not match:
        return []
    inner = match.group(1)
    return [s.strip().strip("\"'") for s in inner.split(",") if s.strip().strip("\"'")]


def collect_pages(wiki_dir: Path) -> dict[str, Path]:
    """Map wiki-relative posix paths (e.g. entities/foo.md) to absolute Paths."""
    pages: dict[str, Path] = {}
    for sub in ("entities", "concepts", "sources"):
        folder = wiki_dir / sub
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            pages[f"{sub}/{path.name}"] = path
    for name in ("overview.md", "index.md", "log.md"):
        path = wiki_dir / name
        if path.is_file():
            pages[name] = path
    return pages


def resolve_link(from_rel: str, target: str, pages: dict[str, Path]) -> str | None:
    """Return the canonical page key if the link targets a wiki page, else None."""
    if target.startswith(("http://", "https://", "mailto:", "docmind://", "#")):
        return None
    clean = target.split("#", 1)[0].split("?", 1)[0]
    if not clean.endswith(".md"):
        return None
    base = Path(from_rel).parent
    try:
        resolved = (base / clean).as_posix()
    except ValueError:
        return None
    # Normalise ./ and ../ without requiring the file to exist yet
    parts: list[str] = []
    for part in resolved.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    key = "/".join(parts)
    return key if key in pages else key  # return key even if missing so caller can flag


def lint(wiki_root: Path) -> list[dict]:
    wiki_dir = wiki_root / "wiki"
    raw_dir = wiki_root / "raw"
    issues: list[dict] = []

    if not wiki_dir.is_dir():
        issues.append({
            "severity": "high",
            "category": "structure",
            "message": f"missing wiki/ directory under {wiki_root}",
            "page": None,
        })
        return issues

    pages = collect_pages(wiki_dir)
    content_pages = {
        k: v for k, v in pages.items()
        if k.startswith(("entities/", "concepts/", "sources/"))
    }

    # --- index completeness ---
    index_path = wiki_dir / "index.md"
    indexed: set[str] = set()
    if not index_path.is_file():
        issues.append({
            "severity": "high",
            "category": "index",
            "message": "wiki/index.md is missing",
            "page": None,
        })
    else:
        index_text = index_path.read_text(encoding="utf-8", errors="replace")
        for _, href in INDEX_LINK_RE.findall(index_text):
            key = resolve_link("index.md", href, pages)
            if key and key in content_pages:
                indexed.add(key)
        for key in sorted(content_pages):
            if key not in indexed:
                issues.append({
                    "severity": "medium",
                    "category": "index",
                    "message": f"page not listed in index.md: {key}",
                    "page": key,
                })

    # inbound / outbound link graph among content pages
    outbound: dict[str, set[str]] = defaultdict(set)
    inbound: dict[str, set[str]] = defaultdict(set)

    for rel, path in content_pages.items():
        text = path.read_text(encoding="utf-8", errors="replace")
        meta, body = parse_frontmatter(text)
        full = text  # frontmatter + body for sources: field

        # source_file existence
        if rel.startswith("sources/"):
            sf_match = SOURCE_FILE_RE.search(full)
            source_file = sf_match.group(1).strip() if sf_match else meta.get("source_file")
            if not source_file:
                issues.append({
                    "severity": "medium",
                    "category": "missing_provenance",
                    "message": "source page has no source_file frontmatter",
                    "page": rel,
                })
            else:
                candidate = wiki_root / source_file
                if not candidate.is_file():
                    # also accept path relative to wiki/ (legacy mistakes)
                    alt = wiki_dir / source_file
                    if not alt.is_file():
                        issues.append({
                            "severity": "medium",
                            "category": "missing_provenance",
                            "message": f"source_file does not exist: {source_file}",
                            "page": rel,
                        })

        # sources: frontmatter slugs
        for slug in parse_sources_list(full):
            expected = f"sources/{slug}.md" if not slug.endswith(".md") else f"sources/{Path(slug).name}"
            if expected not in pages and f"sources/{slug}" not in pages:
                # slug without .md
                candidate_key = expected if expected.endswith(".md") else f"sources/{slug}.md"
                if candidate_key not in pages:
                    issues.append({
                        "severity": "high",
                        "category": "dangling_source",
                        "message": f"sources: frontmatter references missing wiki/sources/{slug}.md",
                        "page": rel,
                    })

        # ## Sources section links
        for section in SOURCES_SECTION_RE.finditer(body):
            for _, href in MD_LINK_RE.findall(section.group(1)):
                key = resolve_link(rel, href, pages)
                if key is None:
                    continue
                if not key.startswith("sources/"):
                    continue
                if key not in pages:
                    issues.append({
                        "severity": "high",
                        "category": "dangling_source",
                        "message": f"## Sources links to missing page: {href}",
                        "page": rel,
                    })

        # all relative .md links
        for _, href in MD_LINK_RE.findall(body):
            key = resolve_link(rel, href, pages)
            if key is None:
                continue
            if key not in pages:
                issues.append({
                    "severity": "high",
                    "category": "broken_link",
                    "message": f"broken relative link: {href}",
                    "page": rel,
                })
                continue
            if key in content_pages and key != rel:
                outbound[rel].add(key)
                inbound[key].add(rel)

    for rel in content_pages:
        if not rel.startswith("sources/") and not outbound.get(rel):
            issues.append({
                "severity": "medium",
                "category": "no_outbound",
                "message": "page has no outbound links to other wiki pages",
                "page": rel,
            })
        if not inbound.get(rel):
            # Pages missing from the index already get an index finding; still
            # flag orphans so a page that is indexed but never linked is visible.
            issues.append({
                "severity": "medium",
                "category": "orphan",
                "message": "page has no inbound links from other content pages",
                "page": rel,
            })

    # empty raw/ is info only
    if raw_dir.is_dir():
        raw_files = [p for p in raw_dir.rglob("*") if p.is_file()]
        if not raw_files:
            issues.append({
                "severity": "info",
                "category": "structure",
                "message": "raw/ exists but contains no files yet",
                "page": None,
            })
    else:
        issues.append({
            "severity": "medium",
            "category": "structure",
            "message": "missing raw/ directory",
            "page": None,
        })

    issues.sort(key=lambda i: (SEVERITY_ORDER.get(i["severity"], 9), i["category"], i.get("page") or ""))
    return issues


def render_text(issues: list[dict], wiki_root: Path) -> str:
    lines = [f"# Wiki Lint Report — local checks", f"Root: `{wiki_root}`", ""]
    if not issues:
        lines.append("No mechanical issues found.")
        return "\n".join(lines)

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for issue in issues:
        by_cat[issue["category"]].append(issue)

    labels = {
        "dangling_source": "🔴 Dangling Source References",
        "broken_link": "🔴 Broken Relative Links",
        "missing_provenance": "🟠 Missing Provenance",
        "orphan": "🟠 Orphan Pages",
        "no_outbound": "🟠 No Outbound Links",
        "index": "🟠 Index Gaps",
        "structure": "🟡 Structure",
    }
    for cat, title in labels.items():
        bucket = by_cat.get(cat)
        if not bucket:
            continue
        lines.append(f"## {title}")
        for issue in bucket:
            loc = f" (`{issue['page']}`)" if issue.get("page") else ""
            lines.append(f"- [{issue['severity']}]{loc} {issue['message']}")
        lines.append("")

    # any unexpected categories
    for cat, bucket in by_cat.items():
        if cat in labels:
            continue
        lines.append(f"## {cat}")
        for issue in bucket:
            loc = f" (`{issue['page']}`)" if issue.get("page") else ""
            lines.append(f"- [{issue['severity']}]{loc} {issue['message']}")
        lines.append("")

    counts = defaultdict(int)
    for issue in issues:
        counts[issue["severity"]] += 1
    summary = ", ".join(f"{k}={v}" for k, v in sorted(counts.items(), key=lambda x: SEVERITY_ORDER.get(x[0], 9)))
    lines.append(f"**Summary:** {len(issues)} issue(s) ({summary})")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("wiki_root", type=Path, help="Path to the wiki root (contains wiki/ and raw/)")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 also when only low/info findings exist")
    args = parser.parse_args()

    root = args.wiki_root.expanduser().resolve()
    if not root.is_dir():
        print(f"error: wiki root not found: {root}", file=sys.stderr)
        return 2

    issues = lint(root)
    if args.json:
        print(json.dumps({"wiki_root": str(root), "issues": issues, "count": len(issues)}, indent=2))
    else:
        print(render_text(issues, root))

    blocking = {"high", "medium"} if not args.strict else {"high", "medium", "low", "info"}
    if any(i["severity"] in blocking for i in issues):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
