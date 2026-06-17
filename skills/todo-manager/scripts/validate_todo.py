#!/usr/bin/env python3
"""
validate_todo.py — Validate the format of a todo Markdown file.

Checks:
  - YAML frontmatter presence and parseability
  - Required fields: title, status, priority, created_at
  - Valid values: status in {pending, in_progress, done},
                  priority in {high, medium, low}
  - Date format YYYY-MM-DD for created_at, due_date, completed_at
  - Required sections: ## Task Details, ## Checklist, ## Execution Log
  - At least one checklist item (- [ ] or - [x])

Usage:
    python3 validate_todo.py <path/to/todo.md>

Exit codes:
    0 — valid
    1 — validation errors found
    2 — file not found or unreadable
"""

import re
import sys
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
VALID_STATUS = {"pending", "in_progress", "done"}
VALID_PRIORITY = {"high", "medium", "low"}
REQUIRED_FIELDS = ["title", "status", "priority", "created_at"]
OPTIONAL_DATE_FIELDS = ["due_date", "completed_at"]
REQUIRED_SECTIONS = ["## Task Details", "## Checklist", "## Execution Log"]


def parse_frontmatter_simple(raw: str) -> dict:
    """Minimal YAML-like parser for frontmatter (fallback when PyYAML unavailable)."""
    result = {}
    for line in raw.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            elif value in ("null", "~", ""):
                value = None
            elif value.startswith("[") and value.endswith("]"):
                value = []  # simplified: treat all lists as empty for validation
            result[key] = value
    return result


def validate(path: Path) -> list[str]:
    """Return a list of error strings. Empty list means valid."""
    errors = []

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"Cannot read file: {e}"]

    # --- Frontmatter ---
    match = FRONTMATTER_RE.match(content)
    if not match:
        errors.append("Missing or malformed YAML frontmatter (must start with '---' block)")
        # Can't check fields without frontmatter
        frontmatter = {}
    else:
        raw_fm = match.group(1)
        if YAML_AVAILABLE:
            try:
                frontmatter = yaml.safe_load(raw_fm) or {}
            except yaml.YAMLError as e:
                errors.append(f"YAML frontmatter parse error: {e}")
                frontmatter = {}
        else:
            frontmatter = parse_frontmatter_simple(raw_fm)

    # --- Required fields ---
    for field in REQUIRED_FIELDS:
        if field not in frontmatter or frontmatter[field] is None:
            errors.append(f"Missing required frontmatter field: '{field}'")

    # --- Status value ---
    status = frontmatter.get("status")
    if status and status not in VALID_STATUS:
        errors.append(f"Invalid 'status' value '{status}'. Must be one of: {', '.join(sorted(VALID_STATUS))}")

    # --- Priority value ---
    priority = frontmatter.get("priority")
    if priority and priority not in VALID_PRIORITY:
        errors.append(f"Invalid 'priority' value '{priority}'. Must be one of: {', '.join(sorted(VALID_PRIORITY))}")

    # --- Date formats ---
    date_fields_to_check = ["created_at"] + OPTIONAL_DATE_FIELDS
    for field in date_fields_to_check:
        value = frontmatter.get(field)
        if value and not DATE_RE.match(str(value)):
            errors.append(f"Invalid date format for '{field}': '{value}'. Expected YYYY-MM-DD")

    # --- Required sections ---
    body = content[match.end():] if match else content
    for section in REQUIRED_SECTIONS:
        if section not in body:
            errors.append(f"Missing required section: '{section}'")

    # --- Checklist items ---
    if "## Checklist" in body:
        checklist_match = re.search(r"## Checklist\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
        if checklist_match:
            checklist_body = checklist_match.group(1)
            has_items = bool(re.search(r"- \[[ x]\]", checklist_body))
            if not has_items:
                errors.append("'## Checklist' section has no items (expected at least one '- [ ]' or '- [x]')")

    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: validate_todo.py <path/to/todo.md>", file=sys.stderr)
        sys.exit(2)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(2)

    errors = validate(path)

    if not errors:
        print(f"✅  {path.name}: valid")
        sys.exit(0)
    else:
        print(f"❌  {path.name}: {len(errors)} error(s) found")
        for error in errors:
            print(f"   • {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
