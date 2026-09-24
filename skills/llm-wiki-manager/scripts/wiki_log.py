#!/usr/bin/env python3
"""Deterministic maintainer of a wiki's `wiki/log.md` in OKF v0.2 format.

OKF v0.2 (§9) defines the log as date-grouped headings `## YYYY-MM-DD`,
newest first, with entries as bullets headed by a bold action word. Keeping that
ordering by hand costs the agent tokens on every entry; this script owns the
ordering so the agent only states what happened.

Usage:
    wiki_log.py <wiki-root> append --op <op> --title <text> [--note <text>]
    wiki_log.py <wiki-root> tail [-n N]
    wiki_log.py <wiki-root> init

`append` creates or reuses the date heading for today (or --date) and places the
entry under it, keeping date sections sorted newest-first. `tail` prints the
most recent entries. `init` creates an empty log file (used by SETUP).

Action words (`--op`): setup, ingest, query, lint, sync, spec-created,
spec-done, promote.

Exit codes:
    0 — ok
    2 — usage / path error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wiki_lib

DATE_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s*$")
OPS = ("setup", "ingest", "query", "lint", "sync", "spec-created", "spec-done", "promote")
DATE_OKF_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_log_spans(log_path: Path) -> list[tuple[str, list[str]]]:
    """Parse the log into [(date, [bullets...])] preserving insertion order."""
    if not log_path.is_file():
        return []
    spans: list[tuple[str, list[str]]] = []
    current_date: str | None = None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = DATE_RE.match(line.strip())
        if m:
            current_date = m.group(1)
            spans.append((current_date, []))
            continue
        if current_date and line.strip():
            spans[-1][1].append(line.rstrip())
    return spans


def render_spans(spans: list[tuple[str, list[str]]]) -> str:
    lines = ["# Update Log\n"]
    for date, bullets in spans:
        lines.append(f"## {date}")
        if not bullets:
            lines.append(f"* **note**: —")
        for bullet in bullets:
            lines.append(bullet)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_bullet(op: str, title: str, note: str) -> str:
    body = title
    if note:
        body = f"{body} — {note}"
    return f"* **{op}**: {body}"


def cmd_init(wiki_dir: Path, args: argparse.Namespace) -> int:
    log_path = wiki_dir / "log.md"
    if log_path.is_file():
        print(f"log.md already exists: {log_path}")
        return 0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("# Update Log\n", encoding="utf-8")
    print(f"initialized {log_path}")
    return 0


def cmd_append(wiki_dir: Path, args: argparse.Namespace) -> int:
    log_path = wiki_dir / "log.md"
    date = args.date or wiki_lib.today_iso()
    if not DATE_OKF_RE.match(date):
        print(f"error: --date must be YYYY-MM-DD, got {date!r}", file=sys.stderr)
        return 2
    bullet = build_bullet(args.op, args.title, args.note or "")
    spans = parse_log_spans(log_path)
    for existing_date, bullets in spans:
        if existing_date == date:
            bullets.append(bullet)
            break
    else:
        spans.append((date, [bullet]))
    spans.sort(key=lambda item: item[0], reverse=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(render_spans(spans), encoding="utf-8")
    print(f"appended: {bullet} → {log_path}")
    return 0


def cmd_tail(wiki_dir: Path, args: argparse.Namespace) -> int:
    log_path = wiki_dir / "log.md"
    spans = parse_log_spans(log_path)
    if not spans:
        print("(log is empty)", file=sys.stderr)
        return 1
    shown = 0
    for date, bullets in spans:
        for bullet in bullets:
            if shown >= args.n:
                return 0
            print(f"{date}  {bullet}")
            shown += 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("wiki_root", type=Path, help="Path to the wiki root (contains wiki/ and raw/)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create an empty log.md if missing")
    p_init.set_defaults(handler=cmd_init)

    p_append = sub.add_parser("append", help="append an entry under the right date heading")
    p_append.add_argument("--date", default=None, help="YYYY-MM-DD (default: today, UTC)")
    p_append.add_argument("--op", required=True, choices=OPS, help="action word for the entry")
    p_append.add_argument("--title", required=True, help="short subject, e.g. 'Kubernetes Operators'")
    p_append.add_argument("--note", default=None, help="one-line description of what happened")
    p_append.set_defaults(handler=cmd_append)

    p_tail = sub.add_parser("tail", help="print the most recent entries")
    p_tail.add_argument("-n", type=int, default=5, help="number of entries (default: 5)")
    p_tail.set_defaults(handler=cmd_tail)

    args = parser.parse_args()
    root = args.wiki_root.expanduser().resolve()
    if not root.is_dir():
        print(f"error: wiki root not found: {root}", file=sys.stderr)
        return 2
    return args.handler(root / "wiki", args)


if __name__ == "__main__":
    sys.exit(main())