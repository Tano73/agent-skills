#!/usr/bin/env python3
"""Behavioral proofs for the OKF-aligned frontmatter aliases in wiki_lint.py.

Covers (see .walden/specs/okf-frontmatter-field-alignment/):
  - R2.AC2: `resource` and legacy `source_file` are both accepted as provenance.
  - R2.AC3: missing provenance is still reported when neither field is present.
  - R2.AC4: a `resource`/`source_file` value mismatch is flagged as a conflict.
  - R1.AC2: a legacy `category`-only page is unaffected (no new finding).
  - R1.AC3: a `category`/`type` value mismatch is flagged as a conflict.

Read-only: every fixture lives in a fresh temporary directory; nothing under the
repository is written or mutated by these checks.

Usage:
    test_frontmatter_aliases.py <test-name>|all

Prints "PASS: <test-name>" for each test that succeeds, or raises an
AssertionError (non-zero exit) on the first failure. Running "all" prints one
PASS line per test plus a final "ALL TESTS PASSED" marker.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WIKI_LINT_PATH = SCRIPT_DIR / "wiki_lint.py"


def _load_wiki_lint():
    spec = importlib.util.spec_from_file_location("wiki_lint", WIKI_LINT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


wiki_lint = _load_wiki_lint()


def _make_wiki_root(tmp: Path) -> Path:
    wiki_root = tmp / "wiki-root"
    (wiki_root / "wiki" / "entities").mkdir(parents=True)
    (wiki_root / "wiki" / "concepts").mkdir(parents=True)
    (wiki_root / "wiki" / "sources").mkdir(parents=True)
    (wiki_root / "raw").mkdir(parents=True)
    (wiki_root / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")
    return wiki_root


def _issues_for(root: Path, page: str, category: str) -> list[dict]:
    issues = wiki_lint.lint(root)
    return [i for i in issues if i.get("page") == page and i["category"] == category]


def t_resource_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _make_wiki_root(Path(tmp))
        (root / "raw" / "doc.md").write_text("source content\n", encoding="utf-8")
        (root / "wiki" / "sources" / "doc.md").write_text(
            "---\n"
            "title: \"Doc\"\n"
            "type: source\n"
            "resource: raw/doc.md\n"
            "---\n\n# Doc\n",
            encoding="utf-8",
        )
        missing = _issues_for(root, "sources/doc.md", "missing_provenance")
        assert not missing, f"expected no missing_provenance issue, got: {missing}"


def t_source_file_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _make_wiki_root(Path(tmp))
        (root / "raw" / "doc.md").write_text("source content\n", encoding="utf-8")
        (root / "wiki" / "sources" / "doc.md").write_text(
            "---\n"
            "title: \"Doc\"\n"
            "category: source\n"
            "source_file: raw/doc.md\n"
            "---\n\n# Doc\n",
            encoding="utf-8",
        )
        missing = _issues_for(root, "sources/doc.md", "missing_provenance")
        assert not missing, f"expected no missing_provenance issue, got: {missing}"


def t_neither_resource_nor_source_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _make_wiki_root(Path(tmp))
        (root / "wiki" / "sources" / "doc.md").write_text(
            "---\ntitle: \"Doc\"\ntype: source\n---\n\n# Doc\n",
            encoding="utf-8",
        )
        missing = _issues_for(root, "sources/doc.md", "missing_provenance")
        assert missing, "expected a missing_provenance issue when neither field is present"


def t_resource_source_file_conflict() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _make_wiki_root(Path(tmp))
        (root / "raw" / "doc.md").write_text("source content\n", encoding="utf-8")
        (root / "raw" / "other.md").write_text("other content\n", encoding="utf-8")
        (root / "wiki" / "sources" / "doc.md").write_text(
            "---\n"
            "title: \"Doc\"\n"
            "type: source\n"
            "resource: raw/doc.md\n"
            "source_file: raw/other.md\n"
            "---\n\n# Doc\n",
            encoding="utf-8",
        )
        conflicts = _issues_for(root, "sources/doc.md", "field_conflict")
        assert conflicts, "expected a field_conflict issue for differing resource/source_file"


def t_category_type_conflict() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _make_wiki_root(Path(tmp))
        (root / "wiki" / "entities" / "foo.md").write_text(
            "---\n"
            "title: \"Foo\"\n"
            "category: entity\n"
            "type: concept\n"
            "---\n\n# Foo\n",
            encoding="utf-8",
        )
        conflicts = _issues_for(root, "entities/foo.md", "field_conflict")
        assert conflicts, "expected a field_conflict issue for differing category/type"


def t_category_only_unaffected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = _make_wiki_root(Path(tmp))
        (root / "wiki" / "entities" / "foo.md").write_text(
            "---\ntitle: \"Foo\"\ncategory: entity\n---\n\n# Foo\n",
            encoding="utf-8",
        )
        conflicts = _issues_for(root, "entities/foo.md", "field_conflict")
        assert not conflicts, f"expected no field_conflict issue, got: {conflicts}"


TESTS = {
    "resource_only": t_resource_only,
    "source_file_only": t_source_file_only,
    "neither_resource_nor_source_file": t_neither_resource_nor_source_file,
    "resource_source_file_conflict": t_resource_source_file_conflict,
    "category_type_conflict": t_category_type_conflict,
    "category_only_unaffected": t_category_only_unaffected,
}


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <test-name>|all", file=sys.stderr)
        return 2
    name = sys.argv[1]

    if name == "all":
        for test_name, fn in TESTS.items():
            fn()
            print(f"PASS: {test_name}")
        print("ALL TESTS PASSED")
        return 0

    fn = TESTS.get(name)
    if fn is None:
        print(f"unknown test: {name}", file=sys.stderr)
        return 2
    fn()
    print(f"PASS: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
