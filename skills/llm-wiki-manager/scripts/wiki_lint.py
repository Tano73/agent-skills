#!/usr/bin/env python3
"""Deterministic local health checks for an llm-wiki.

Catches the mechanical failures that are easy for an LLM to miss or invent:
dangling source slugs, broken relative links, pages missing from (or drifting
from) index.md, orphan pages (no inbound links), missing provenance, and the
OKF v0.2 structural contract (REQUIRED `type` field, valid `status`, `stale_after`
honoured). Semantic issues (contradictions, stale narrative, schema drift) stay
with the agent — this script only reports what the filesystem can prove.

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wiki_lib
from wiki_index import build_index

MD_LINK_RE = wiki_lib.MD_LINK_RE
SOURCES_SECTION_RE = wiki_lib.SOURCES_SECTION_RE
RESOURCE_RE = re.compile(r"^resource:\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.MULTILINE)
SOURCE_FILE_RE = re.compile(r"^source_file:\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.MULTILINE)
INDEX_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
VALID_STATUS = {"draft", "stable", "deprecated"}


def parse_sources_list(text: str) -> list[str]:
    match = wiki_lib.SOURCES_FM_RE.search(text)
    if not match:
        return []
    inner = match.group(1)
    return [s.strip().strip("\"'") for s in inner.split(",") if s.strip().strip("\"'")]


def collect_pages(wiki_dir: Path) -> dict[str, Path]:
    """Wiki-relative page map including index/log for link resolution."""
    pages = wiki_lib.collect_pages(wiki_dir)
    for name in ("index.md", "log.md"):
        path = wiki_dir / name
        if path.is_file():
            pages[name] = path
    return pages


def stale_after_passed(meta: dict) -> bool:
    value = meta.get("stale_after")
    if not isinstance(value, str):
        return False
    date = value.strip().split("T", 1)[0]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        return False
    return date <= wiki_lib.today_iso()


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
        if k.startswith(("entities/", "concepts/", "sources/", "overview.md"))
    }

    # --- index completeness + drift ---
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
            key = wiki_lib.resolve_link("index.md", href, pages)
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
        if index_text != build_index(wiki_dir):
            issues.append({
                "severity": "medium",
                "category": "index",
                "message": "index.md is out of date (regenerate with wiki_index.py --write)",
                "page": None,
            })

    # inbound / outbound link graph among content pages
    outbound: dict[str, set[str]] = defaultdict(set)
    inbound: dict[str, set[str]] = defaultdict(set)

    for rel, path in content_pages.items():
        meta, body = wiki_lib.load_frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        full_text = path.read_text(encoding="utf-8", errors="replace")

        # --- OKF v0.2 structural contract ---
        if not meta.get("type") and not meta.get("category"):
            issues.append({
                "severity": "medium",
                "category": "okf_type",
                "message": "missing required OKF field: type",
                "page": rel,
            })
        elif not meta.get("type") and meta.get("category"):
            issues.append({
                "severity": "info",
                "category": "okf_type",
                "message": "legacy category field used; OKF v0.2 requires type",
                "page": rel,
            })
        if not meta.get("description"):
            issues.append({
                "severity": "info",
                "category": "okf_description",
                "message": "missing recommended OKF field: description (used by the index generator)",
                "page": rel,
            })
        status = meta.get("status")
        if status is not None and str(status) not in VALID_STATUS:
            issues.append({
                "severity": "low",
                "category": "okf_status",
                "message": f"invalid OKF status: {status!r} (expected draft|stable|deprecated)",
                "page": rel,
            })
        if stale_after_passed(meta):
            issues.append({
                "severity": "info",
                "category": "okf_stale",
                "message": f"content is stale per stale_after: {meta['stale_after']}",
                "page": rel,
            })

        # resource / source_file provenance (resource preferred; source_file is a
        # recognized legacy alias)
        if rel.startswith("sources/"):
            resource_match = RESOURCE_RE.search(full_text)
            resource = resource_match.group(1).strip() if resource_match else wiki_lib.meta_value(meta, "resource")
            sf_match = SOURCE_FILE_RE.search(full_text)
            source_file = sf_match.group(1).strip() if sf_match else wiki_lib.meta_value(meta, "source_file")

            if resource and source_file and resource != source_file:
                issues.append({
                    "severity": "medium",
                    "category": "field_conflict",
                    "message": f"conflicting provenance: resource={resource!r} vs source_file={source_file!r}",
                    "page": rel,
                })

            provenance = resource or source_file
            if not provenance:
                issues.append({
                    "severity": "medium",
                    "category": "missing_provenance",
                    "message": "source page has no resource/source_file frontmatter",
                    "page": rel,
                })
            else:
                candidate = wiki_root / provenance
                if not candidate.is_file():
                    alt = wiki_dir / provenance
                    if not alt.is_file():
                        issues.append({
                            "severity": "medium",
                            "category": "missing_provenance",
                            "message": f"resource/source_file does not exist: {provenance}",
                            "page": rel,
                        })

        # category / type classification (type preferred; category legacy alias)
        category_value = meta.get("category")
        type_value = meta.get("type")
        if (
            isinstance(category_value, str) and isinstance(type_value, str)
            and category_value != type_value
        ):
            issues.append({
                "severity": "medium",
                "category": "field_conflict",
                "message": f"conflicting classification: category={category_value!r} vs type={type_value!r}",
                "page": rel,
            })

        # sources: frontmatter slugs
        for slug in parse_sources_list(full_text):
            expected = f"sources/{slug}.md" if not slug.endswith(".md") else f"sources/{Path(slug).name}"
            candidate_key = expected if expected.endswith(".md") else f"sources/{slug}.md"
            if candidate_key not in pages and f"sources/{slug}" not in pages:
                issues.append({
                    "severity": "high",
                    "category": "dangling_source",
                    "message": f"sources: frontmatter references missing wiki/sources/{slug}.md",
                    "page": rel,
                })

        # ## Sources section links
        for section in SOURCES_SECTION_RE.finditer(body):
            for _, href in MD_LINK_RE.findall(section.group(1)):
                key = wiki_lib.resolve_link(rel, href, pages)
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
            key = wiki_lib.resolve_link(rel, href, pages)
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
        "okf_type": "🟠 Missing Required OKF Field (type)",
        "field_conflict": "🟠 Conflicting Frontmatter Fields",
        "missing_provenance": "🟠 Missing Provenance",
        "orphan": "🟠 Orphan Pages",
        "no_outbound": "🟠 No Outbound Links",
        "index": "🟠 Index Gaps / Drift",
        "okf_status": "🟡 Invalid OKF status",
        "structure": "🟡 Structure",
        "okf_description": "🟢 Recommended OKF Field Missing (description)",
        "okf_stale": "🟢 Stale Content (stale_after)",
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