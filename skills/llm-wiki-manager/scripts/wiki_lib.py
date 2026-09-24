#!/usr/bin/env python3
"""Shared helpers for the deterministic llm-wiki scripts.

Centralizes the parsing and path logic that `wiki_index.py`, `wiki_log.py`,
`wiki_search.py`, and `wiki_lint.py` all need (frontmatter via PyYAML, page
enumeration, link resolution, OKF-aligned index generation). Keeping it in one
module avoids three copies of the same 40 lines and makes the behavior of the
lint/index pair consistent by construction.

Nothing here writes to disk except the builders each script calls.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - guarded so scripts fail loudly, not obscurely
    yaml = None

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
MD_LINK_RE = re.compile(r"(?<!!)\[([^\]]*)\]\(([^)\s]+)\)")
SOURCES_SECTION_RE = re.compile(
    r"^##\s+Sources(?:\s*&?\s*Examples)?\s*\n(.*?)(?=^##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
SOURCES_FM_RE = re.compile(r"^sources:\s*\[(.*?)\]\s*$", re.MULTILINE | re.DOTALL)

# wiki page type values (also satisfy OKF v0.2's REQUIRED `type` field)
PAGE_TYPES = ("entity", "concept", "source", "overview")

YAML_LOADER_KWARGS = {"Loader": yaml.SafeLoader} if yaml else {}


def now_utc() -> datetime:
    """Current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def today_iso() -> str:
    """Today's date in OKF log heading form (YYYY-MM-DD, UTC)."""
    return now_utc().strftime("%Y-%m-%d")


def load_frontmatter(text: str) -> tuple[dict, str]:
    """Split a markdown file into an OKF frontmatter dict and the body text.

    Returns ({}, text) when there is no parseable frontmatter block. Prefers a
    real YAML parse (trust/lifecycle/provenance families are nested maps and
    lists) and falls back to a naive key: value split only if PyYAML is missing.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    raw = match.group(1)
    meta: dict = {}
    if yaml is not None:
        try:
            parsed = yaml.safe_load(raw)
        except yaml.YAMLError:
            parsed = None
        if isinstance(parsed, dict):
            meta = parsed
        else:
            meta = {}
    else:
        for line in raw.splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip("\"'")
    return meta, text[match.end():]


def read_page(path: Path) -> tuple[str, str]:
    """Return (frontmatter dict, body) for a markdown page on disk."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return load_frontmatter(text)


def meta_value(meta: dict, *keys: str) -> str:
    """First non-empty scalar among the given keys, normalized to a string.

    Handles legacy aliases (category/type, source_file/resource) uniformly:
    callers pass the current key first and the alias second.
    """
    for key in keys:
        value = meta.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, (list, dict)):
            return str(value)
        return str(value).strip()
    return ""


def collect_pages(wiki_dir: Path) -> dict[str, Path]:
    """Map wiki-relative posix paths (e.g. entities/foo.md) to absolute Paths."""
    pages: dict[str, Path] = {}
    for sub in ("entities", "concepts", "sources"):
        folder = wiki_dir / sub
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.md")):
            pages[f"{sub}/{path.name}"] = path
    if (wiki_dir / "overview.md").is_file():
        pages["overview.md"] = wiki_dir / "overview.md"
    return pages


def resolve_link(from_rel: str, target: str, pages: dict[str, Path]) -> str | None:
    """Return the canonical page key a link resolves to, or None for non-pages.

    Matches the historical lint semantics: ignores absolute URLs, anchors, and
    docmind:// links; normalizes ./ and ../; does not require the target to
    exist (the caller decides whether a missing target is a finding).
    """
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
    parts: list[str] = []
    for part in resolved.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    return "/".join(parts)


def is_source_slug_target(key: str) -> bool:
    """True when the resolved link/key points into the source pages folder."""
    return key == "sources" or key.startswith("sources/")


def title_for(meta: dict, name: str) -> str:
    """A page's display title: frontmatter `title`, else the file stem."""
    title = meta_value(meta, "title")
    if title:
        return title
    return Path(name).stem.replace("-", " ").capitalize()


def description_for(meta: dict) -> str:
    """The one-line description OKF recommends and the index displays."""
    return meta_value(meta, "description")


def list_tags(meta: dict) -> list[str]:
    """Tags as a sorted list of strings (accepts list or comma string)."""
    tags = meta.get("tags")
    if isinstance(tags, list):
        return sorted(str(t) for t in tags)
    if isinstance(tags, str):
        return sorted(t.strip() for t in tags.split(",") if t.strip())
    return []


def count_sources_in_body(body: str, from_rel: str, pages: dict[str, Path]) -> int:
    """Count which wiki source pages a page's `## Sources` section links to.

    Deterministic provenance signal used by the index; mirrors how lint
    validates `## Sources` links so the two never disagree.
    """
    count = 0
    for section in SOURCES_SECTION_RE.finditer(body):
        for _, href in MD_LINK_RE.findall(section.group(1)):
            key = resolve_link(from_rel, href, pages)
            if key is not None and is_source_slug_target(key) and key in pages:
                count += 1
    return count


def source_slugs(meta: dict, body: str) -> list[str]:
    """Source slugs listed in the `sources:` frontmatter field."""
    # Prefer a real YAML list when available; fall back to the regex form.
    value = meta.get("sources")
    if isinstance(value, list):
        return [str(s).strip() for s in value if str(s).strip()]
    match = SOURCES_FM_RE.search(body)
    if not match:
        return []
    return [s.strip().strip("\"'") for s in match.group(1).split(",") if s.strip().strip("\"'")]