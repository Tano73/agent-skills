#!/usr/bin/env python3
"""Deterministic raw/ versioning check for INGEST.

INGEST used to make the agent read candidate and existing `raw/` files to
decide "create / identical / version". That comparison is hashing, not
reasoning: this script does it with SHA-256 so the agent spends zero
elaboration tokens on it and never has to eyeball content.

Usage:
    raw_check.py <wiki-root> <file-path>                # existing local file
    raw_check.py <wiki-root> <name> --stdin             # content piped to stdin

The first form checks a file that already exists on disk (candidate name = its
basename). The second form checks pasted content; `<name>` is the desired raw
filename (e.g. kubernetes-operators.md). Both compare against everything under
`raw/`.

Output (JSON) — one of:
    {decision: "create",    path: "raw/<name>",              ...}
    {decision: "identical", path: "raw/<name>", matches: [...]}
    {decision: "version",   path: "raw/<name>-vN.md", ...}
    {decision: "duplicate", path: "raw/<other>", matches: [...]}
    {decision: "error",     path: null, reason: "..."}

Exit codes:
    0 — decision produced
    2 — usage / path error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

VERSION_RE = re.compile(r"^(?P<stem>.*)-v(?P<num>\d+)$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def scan_raw(raw_dir: Path) -> list[Path]:
    if not raw_dir.is_dir():
        return []
    return sorted(p for p in raw_dir.rglob("*") if p.is_file())


def next_version(existing: list[Path], stem: str, suffix: str) -> str:
    # The base file (no suffix) occupies v1; the first versioned copy is -v2.
    nums = [1]
    for path in existing:
        m = VERSION_RE.match(path.stem)
        if m and m.group("stem") == stem:
            nums.append(int(m.group("num")))
    return f"{stem}-v{max(nums) + 1}{suffix}"


def check(raw_dir: Path, name: str, content: bytes) -> dict:
    hash_value = sha256_bytes(content)
    raw_files = scan_raw(raw_dir)

    existing_same_name = raw_dir / name
    if existing_same_name.is_file():
        if sha256_bytes(existing_same_name.read_bytes()) == hash_value:
            return {"decision": "identical", "path": f"raw/{name}",
                    "matches": [f"raw/{name}"],
                    "reason": "raw file exists with identical content; reuse it"}
        stem, suffix = Path(name).stem, Path(name).suffix
        versioned = next_version(raw_files, stem, suffix)
        return {"decision": "version", "path": f"raw/{versioned}",
                "matches": [f"raw/{name}"],
                "reason": f"raw/{name} exists with different content; save the new version as raw/{versioned}"}

    # Pure duplicate of any existing raw file under a different name?
    for path in raw_files:
        if sha256_bytes(path.read_bytes()) == hash_value:
            rel = str(path.relative_to(raw_dir.parent))
            return {"decision": "duplicate", "path": f"raw/{path.name}",
                    "matches": [rel], "reason": f"content already exists as {rel}"}

    return {"decision": "create", "path": f"raw/{name}",
            "matches": [], "reason": "no existing raw file with this name"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("wiki_root", type=Path, help="Path to the wiki root (contains wiki/ and raw/)")
    parser.add_argument("candidate", help="file path (existing) or desired raw filename with --stdin")
    parser.add_argument("--stdin", action="store_true",
                        help="read content from standard input (candidate is the desired name)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args()

    root = args.wiki_root.expanduser().resolve()
    if not root.is_dir():
        print("error: wiki root not found", file=sys.stderr)
        return 2
    raw_dir = root / "raw"

    candidate = Path(args.candidate)
    if args.stdin:
        name = candidate.name
        content = sys.stdin.buffer.read()
    else:
        if not candidate.is_file():
            print(f"error: file not found: {candidate}", file=sys.stderr)
            return 2
        name = candidate.name
        content = candidate.read_bytes()

    result = check(raw_dir, name, content)
    if not args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())