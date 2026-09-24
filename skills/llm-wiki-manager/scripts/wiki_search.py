#!/usr/bin/env python3
"""Targeted keyword search over a wiki's pages.

QUERY used to tell the agent to open the index and then read up to 8 whole
pages hunting for the answer. That burn of input tokens is avoidable: this
script returns the few pages that actually match, each with a compact reason
and the matched body lines, so the agent opens only the pages worth reading.

Usage:
    wiki_search.py <wiki-root> <words...> [--limit N] [--match-lines K]
                   [--sources] [--overview] [--json]

Searches page filenames, frontmatter (title/description/tags) and body
(headings and text), case-insensitively. A page matches when every word appears
somewhere in it. Pages are ranked by where the match lands (title/frontmatter
first, headings next, then body).

Exit codes:
    0 — ok (even with zero matches; that is a legitimate "no coverage" answer)
    2 — usage / path error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wiki_lib

# search folders and how a hit ranks by location
BOOST = {"title": 100, "tags": 50, "description": 40, "heading": 20, "body": 10}


def search(wiki_dir: Path, words: list[str], include_sources: bool,
           include_overview: bool) -> list[dict]:
    pages = wiki_lib.collect_pages(wiki_dir)
    lowered = [w.lower() for w in words]
    results = []
    for key in sorted(pages):
        if key == "index.md" or key == "log.md":
            continue
        if key.startswith("sources/") and not include_sources:
            continue
        if key == "overview.md" and not include_overview:
            continue
        page = pages[key]
        meta, body = wiki_lib.read_page(page)
        name = key.rsplit("/", 1)[1]
        title = wiki_lib.title_for(meta, name)
        tags = wiki_lib.list_tags(meta)
        haystack = {
            "title": (title + " " + name).lower(),
            "tags": " ".join(tags).lower(),
            "description": wiki_lib.description_for(meta).lower(),
            "body": body.lower(),
        }
        if not all(any(w in hay for hay in haystack.values()) for w in lowered):
            continue
        score = 0
        matched = []
        matched_words = set()
        for w in lowered:
            if w in haystack["title"]:
                score += BOOST["title"]
                matched_words.add(w)
            if w in haystack["tags"]:
                score += BOOST["tags"]
                matched_words.add(w)
            if w in haystack["description"]:
                score += BOOST["description"]
                matched_words.add(w)
        # headings and body line matches
        lines = body.splitlines()
        line_hits = []
        heading_hits = []
        for idx, line in enumerate(lines, start=1):
            low = line.lower()
            if not any(w in low for w in lowered):
                continue
            line_hits.append((idx, line.strip()))
            if line.lstrip().startswith("#"):
                score += BOOST["heading"]
                heading_hits.append(idx)
            else:
                score += BOOST["body"]
        results.append({
            "page": key,
            "title": title,
            "score": score,
            "matched_words": sorted(matched_words),
            "line_hits": [(idx, text) for idx, text in line_hits],
        })
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("wiki_root", type=Path, help="Path to the wiki root (contains wiki/ and raw/)")
    parser.add_argument("words", nargs="+", help="search words (AND semantics)")
    parser.add_argument("--limit", type=int, default=8, help="max pages to report (default: 8)")
    parser.add_argument("--match-lines", type=int, default=2,
                        help="matched body lines shown per page (default: 2)")
    parser.add_argument("--sources", action="store_true", help="include source pages in the search")
    parser.add_argument("--overview", action="store_true", help="include overview.md in the search")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    root = args.wiki_root.expanduser().resolve()
    if not root.is_dir():
        print("error: wiki root not found", file=sys.stderr)
        return 2

    results = search(root / "wiki", args.words, args.sources, args.overview)
    results = results[: args.limit]

    if args.json:
        print(json.dumps({"matches": results, "count": len(results)}))
        return 0

    if not results:
        print("No matching wiki pages.")
        return 0
    for r in results:
        print(f"{r['page']}  ({r['title']}; words: {', '.join(r['matched_words'])})")
        for idx, text in r["line_hits"][: args.match_lines]:
            print(f"  {idx}: {text}")
    print(f"\n{len(results)} page(s) matched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())