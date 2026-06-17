#!/usr/bin/env python3
"""
todo.py — Deterministic filesystem engine for personal todo management.

Subcommands:
    init      Create .todos/ directory structure
    create    Create a new todo file and update governance READMEs
    update    Update an existing active todo
    complete  Mark a todo as done and archive to completed/
    find      Search active todos by title or slug
    validate  Validate a todo Markdown file

All subcommands print JSON to stdout. Usage/errors go to stderr.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import date
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
MAX_SLUG_LEN = 50
MAX_RECENT_CHANGES = 10

RULE_MD_TEMPLATE = """# .todos — Personal Task Management

## Purpose

Centralized management of all todo items.

## Todo Tracking

enabled: true
todos_directory: {todos_dir}

## Structure

.todos/
├── active/     # Todo attivi
└── completed/  # Todo completati

## Naming Convention

YYYY-MM-DD_todo-title-slug.md

## Allowed Operations

- Create: Allowed
- Update: Allowed (must update execution log)
- Delete: Not allowed (archive to completed/ instead)
- Move: Only between active/ and completed/
"""

ROOT_README_TEMPLATE = """# .todos — Personal Task Management

## Stats

- Active: {active_count}
- Completed: {completed_count}
- Last updated: {today}

## Recent Changes

"""

ACTIVE_README_TEMPLATE = """# Active Todos

Last updated: {today}

## Todos

"""


def today_str() -> str:
    return date.today().isoformat()


def emit(payload: dict, exit_code: int = 0) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.exit(exit_code)


def emit_error(message: str, exit_code: int = 1, **extra) -> None:
    payload = {"success": False, "error": message, **extra}
    emit(payload, exit_code)


def slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    if len(slug) > MAX_SLUG_LEN:
        slug = slug[:MAX_SLUG_LEN].rstrip("-")
    return slug or "todo"


def parse_frontmatter_simple(raw: str) -> dict:
    result: dict = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
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
            inner = value[1:-1].strip()
            if not inner:
                result[key] = []
            else:
                result[key] = [
                    item.strip().strip("'\"") for item in inner.split(",") if item.strip()
                ]
        else:
            result[key] = value
    return result


def parse_frontmatter(content: str) -> tuple[dict, str, re.Match | None]:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}, content, None
    raw_fm = match.group(1)
    if YAML_AVAILABLE:
        try:
            frontmatter = yaml.safe_load(raw_fm) or {}
        except yaml.YAMLError:
            frontmatter = parse_frontmatter_simple(raw_fm)
    else:
        frontmatter = parse_frontmatter_simple(raw_fm)
    body = content[match.end():]
    return frontmatter, body, match


def dump_frontmatter(data: dict) -> str:
    lines = ["---"]
    field_order = [
        "title",
        "status",
        "priority",
        "created_at",
        "due_date",
        "completed_at",
        "source_file",
        "source_type",
        "tags",
        "dependencies",
        "related_files",
    ]
    seen = set()
    for key in field_order:
        if key not in data:
            continue
        seen.add(key)
        lines.append(format_yaml_line(key, data[key]))
    for key, value in data.items():
        if key not in seen:
            lines.append(format_yaml_line(key, value))
    lines.append("---")
    return "\n".join(lines) + "\n"


def format_yaml_line(key: str, value) -> str:
    if value is None:
        return f"{key}: null"
    if isinstance(value, list):
        if not value:
            return f"{key}: []"
        rendered = ", ".join(json.dumps(item) for item in value)
        return f"{key}: [{rendered}]"
    if isinstance(value, str) and (
        ":" in value or value.startswith("#") or "\n" in value
    ):
        return f'{key}: "{value}"'
    return f"{key}: {value}"


def validate_todo_content(content: str, path: Path | None = None) -> list[str]:
    errors: list[str] = []
    frontmatter, body, match = parse_frontmatter(content)

    if not match:
        errors.append("Missing or malformed YAML frontmatter (must start with '---' block)")
        return errors

    for field in REQUIRED_FIELDS:
        if field not in frontmatter or frontmatter[field] is None:
            errors.append(f"Missing required frontmatter field: '{field}'")

    status = frontmatter.get("status")
    if status and status not in VALID_STATUS:
        errors.append(
            f"Invalid 'status' value '{status}'. Must be one of: {', '.join(sorted(VALID_STATUS))}"
        )

    priority = frontmatter.get("priority")
    if priority and priority not in VALID_PRIORITY:
        errors.append(
            f"Invalid 'priority' value '{priority}'. Must be one of: {', '.join(sorted(VALID_PRIORITY))}"
        )

    for field in ["created_at"] + OPTIONAL_DATE_FIELDS:
        value = frontmatter.get(field)
        if value and not DATE_RE.match(str(value)):
            errors.append(
                f"Invalid date format for '{field}': '{value}'. Expected YYYY-MM-DD"
            )

    for section in REQUIRED_SECTIONS:
        if section not in body:
            errors.append(f"Missing required section: '{section}'")

    if "## Checklist" in body:
        checklist_match = re.search(r"## Checklist\n(.*?)(?=\n## |\Z)", body, re.DOTALL)
        if checklist_match:
            checklist_body = checklist_match.group(1)
            has_items = bool(re.search(r"- \[[ x]\]", checklist_body))
            if not has_items:
                errors.append(
                    "'## Checklist' section has no items (expected at least one '- [ ]' or '- [x]')"
                )

    if path is not None:
        for error in errors:
            pass
    return errors


def validate_file(path: Path) -> list[str]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"Cannot read file: {exc}"]
    return validate_todo_content(content, path)


def ensure_dirs(todos_dir: Path) -> tuple[Path, Path]:
    active_dir = todos_dir / "active"
    completed_dir = todos_dir / "completed"
    active_dir.mkdir(parents=True, exist_ok=True)
    completed_dir.mkdir(parents=True, exist_ok=True)
    return active_dir, completed_dir


def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.write_text(content, encoding="utf-8")
    return True


def count_todos(directory: Path) -> int:
    if not directory.exists():
        return 0
    return len([p for p in directory.glob("*.md") if p.name != "README.md"])


def parse_active_readme(path: Path) -> tuple[str, list[str]]:
    if not path.exists():
        return today_str(), []
    content = path.read_text(encoding="utf-8")
    last_updated = today_str()
    match = re.search(r"Last updated:\s*(\d{4}-\d{2}-\d{2})", content)
    if match:
        last_updated = match.group(1)
    entries: list[str] = []
    if "## Todos" in content:
        section = content.split("## Todos", 1)[1]
        for line in section.splitlines():
            stripped = line.strip()
            if stripped.startswith("- ["):
                entries.append(stripped)
    return last_updated, entries


def write_active_readme(path: Path, entries: list[str]) -> None:
    content = ACTIVE_README_TEMPLATE.format(today=today_str())
    content += "\n".join(entries)
    if entries:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def parse_root_readme(path: Path) -> tuple[int, int, list[str]]:
    if not path.exists():
        return 0, 0, []
    content = path.read_text(encoding="utf-8")
    active_count = 0
    completed_count = 0
    active_match = re.search(r"Active:\s*(\d+)", content)
    completed_match = re.search(r"Completed:\s*(\d+)", content)
    if active_match:
        active_count = int(active_match.group(1))
    if completed_match:
        completed_count = int(completed_match.group(1))
    recent: list[str] = []
    if "## Recent Changes" in content:
        section = content.split("## Recent Changes", 1)[1]
        for line in section.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                recent.append(stripped)
    return active_count, completed_count, recent


def write_root_readme(path: Path, active_count: int, completed_count: int, recent: list[str]) -> None:
    content = ROOT_README_TEMPLATE.format(
        active_count=active_count,
        completed_count=completed_count,
        today=today_str(),
    )
    trimmed = recent[:MAX_RECENT_CHANGES]
    if trimmed:
        content += "\n".join(trimmed) + "\n"
    path.write_text(content, encoding="utf-8")


def make_active_entry(filename: str, title: str, priority: str, due: str | None) -> str:
    due_display = due if due else "none"
    return f"- [{filename}]({filename}) — {title} (Priority: {priority}, Due: {due_display})"


def build_todo_content(
    title: str,
    priority: str,
    created_at: str,
    details: str,
    checklist: list[str],
    due_date: str | None = None,
) -> str:
    frontmatter = {
        "title": title,
        "status": "pending",
        "priority": priority,
        "created_at": created_at,
        "source_file": None,
        "source_type": "manual",
        "tags": [],
        "dependencies": [],
        "related_files": [],
    }
    if due_date:
        frontmatter["due_date"] = due_date

    checklist_lines = "\n".join(f"- [ ] {step}" for step in checklist)
    body = f"""# {title}

## Task Details

{details}

## Checklist

{checklist_lines}

## Execution Log

### {created_at}
- Todo created manually
- Status: pending
- Priority: {priority}
"""
    return dump_frontmatter(frontmatter) + body


def json_safe(value):
    if isinstance(value, date):
        return value.isoformat()
    return value


def list_active_todos(active_dir: Path) -> list[dict]:
    todos: list[dict] = []
    if not active_dir.exists():
        return todos
    for path in sorted(active_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        content = path.read_text(encoding="utf-8")
        frontmatter, _, _ = parse_frontmatter(content)
        todos.append(
            {
                "filename": path.name,
                "path": str(path),
                "slug": path.stem.split("_", 1)[-1] if "_" in path.stem else path.stem,
                "title": frontmatter.get("title", path.stem),
                "priority": frontmatter.get("priority"),
                "due_date": json_safe(frontmatter.get("due_date")),
                "status": frontmatter.get("status"),
            }
        )
    return todos


def find_duplicates(active_dir: Path, title: str, slug: str) -> list[dict]:
    matches: list[dict] = []
    title_lower = title.lower()
    for todo in list_active_todos(active_dir):
        todo_title = (todo.get("title") or "").lower()
        todo_slug = todo.get("slug") or ""
        if todo_title == title_lower or todo_slug == slug or slug in todo_slug:
            matches.append(todo)
    return matches


def resolve_filename(
    active_dir: Path, created_at: str, title: str, slug: str, force: bool
) -> tuple[str, list[dict]]:
    base_slug = slug
    filename = f"{created_at}_{base_slug}.md"
    duplicates = find_duplicates(active_dir, title, base_slug)
    if duplicates and not force:
        return filename, duplicates

    if force and duplicates:
        counter = 2
        while (active_dir / f"{created_at}_{base_slug}_{counter}.md").exists():
            counter += 1
        base_slug = f"{base_slug}_{counter}"
        filename = f"{created_at}_{base_slug}.md"
    elif (active_dir / filename).exists():
        if not force:
            return filename, find_duplicates(active_dir, title, base_slug)
        counter = 2
        while (active_dir / f"{created_at}_{base_slug}_{counter}.md").exists():
            counter += 1
        base_slug = f"{base_slug}_{counter}"
        filename = f"{created_at}_{base_slug}.md"

    return filename, []


def find_todo_by_slug(active_dir: Path, slug: str) -> Path | None:
    slug_lower = slug.lower()
    candidates: list[Path] = []
    for path in active_dir.glob("*.md"):
        if path.name == "README.md":
            continue
        file_slug = path.stem.split("_", 1)[-1] if "_" in path.stem else path.stem
        if file_slug.lower() == slug_lower or slug_lower in file_slug.lower():
            candidates.append(path)
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        for path in active_dir.glob("*.md"):
            if path.name == "README.md":
                continue
            content = path.read_text(encoding="utf-8")
            frontmatter, _, _ = parse_frontmatter(content)
            title = (frontmatter.get("title") or "").lower()
            if slug_lower in title:
                candidates.append(path)
    if len(candidates) == 1:
        return candidates[0]
    return None


def append_execution_log(body: str, today: str, lines: list[str]) -> str:
    block = f"\n### {today}\n" + "\n".join(f"- {line}" for line in lines) + "\n"
    if "## Execution Log" in body:
        return body.rstrip() + "\n" + block
    return body.rstrip() + f"\n\n## Execution Log\n{block}"


def update_body_title(body: str, new_title: str) -> str:
    return re.sub(r"^# .+$", f"# {new_title}", body, count=1, flags=re.MULTILINE)


def cmd_init(args: argparse.Namespace) -> None:
    todos_dir = Path(args.dir).expanduser().resolve()
    active_dir, completed_dir = ensure_dirs(todos_dir)
    created_files: list[str] = []

    rule_path = todos_dir / "RULE.md"
    if write_if_missing(rule_path, RULE_MD_TEMPLATE.format(todos_dir=str(todos_dir))):
        created_files.append(str(rule_path))

    root_readme = todos_dir / "README.md"
    if write_if_missing(
        root_readme,
        ROOT_README_TEMPLATE.format(active_count=0, completed_count=0, today=today_str()),
    ):
        created_files.append(str(root_readme))

    active_readme = active_dir / "README.md"
    if write_if_missing(active_readme, ACTIVE_README_TEMPLATE.format(today=today_str())):
        created_files.append(str(active_readme))

    emit(
        {
            "success": True,
            "operation": "init",
            "todos_dir": str(todos_dir),
            "created_files": created_files,
            "already_existed": len(created_files) == 0,
        }
    )


def cmd_create(args: argparse.Namespace) -> None:
    todos_dir = Path(args.dir).expanduser().resolve()
    if not todos_dir.exists():
        emit_error(f"Todos directory not found: {todos_dir}", exit_code=2)

    title = args.title.strip()
    priority = args.priority
    due = None if args.due == "none" else args.due
    details = args.details
    checklist = args.check or []

    if not title:
        emit_error("Title is required", exit_code=2)
    if priority not in VALID_PRIORITY:
        emit_error(f"Invalid priority: {priority}", exit_code=2)
    if due and not DATE_RE.match(due):
        emit_error(f"Invalid due date format: {due}. Expected YYYY-MM-DD or 'none'", exit_code=2)
    if not details:
        emit_error("Task details are required", exit_code=2)
    if not checklist:
        emit_error("At least one checklist item is required", exit_code=2)

    active_dir, _ = ensure_dirs(todos_dir)
    created_at = today_str()
    slug = slugify(title)
    filename, duplicates = resolve_filename(active_dir, created_at, title, slug, args.force)
    if duplicates:
        emit(
            {
                "success": False,
                "operation": "create",
                "error": "duplicate_found",
                "duplicates": duplicates,
                "message": "Similar todo already exists. Re-run with --force to create anyway.",
            },
            exit_code=1,
        )

    content = build_todo_content(title, priority, created_at, details, checklist, due)
    errors = validate_todo_content(content)
    if errors:
        emit_error("Generated content failed validation", validation_errors=errors)

    todo_path = active_dir / filename
    todo_path.write_text(content, encoding="utf-8")

    active_readme_path = active_dir / "README.md"
    _, entries = parse_active_readme(active_readme_path)
    entries.append(make_active_entry(filename, title, priority, due))
    write_active_readme(active_readme_path, entries)

    root_readme_path = todos_dir / "README.md"
    active_count, completed_count, recent = parse_root_readme(root_readme_path)
    active_count = count_todos(active_dir)
    recent.insert(0, f'- {created_at}: Added "{title}"')
    write_root_readme(root_readme_path, active_count, completed_count, recent)

    validation_errors = validate_file(todo_path)
    emit(
        {
            "success": True,
            "operation": "create",
            "title": title,
            "priority": priority,
            "due_date": due,
            "filename": filename,
            "path": str(todo_path),
            "slug": filename.removesuffix(".md").split("_", 1)[-1],
            "valid": len(validation_errors) == 0,
            "validation_errors": validation_errors,
        }
    )


def cmd_update(args: argparse.Namespace) -> None:
    todos_dir = Path(args.dir).expanduser().resolve()
    active_dir = todos_dir / "active"
    if not active_dir.exists():
        emit_error(f"Active todos directory not found: {active_dir}", exit_code=2)

    todo_path = find_todo_by_slug(active_dir, args.slug)
    if todo_path is None:
        emit_error(f"Todo not found for slug/query: {args.slug}", exit_code=2)

    content = todo_path.read_text(encoding="utf-8")
    frontmatter, body, match = parse_frontmatter(content)
    if not match:
        emit_error("Todo file has invalid frontmatter", exit_code=2)

    old_title = frontmatter.get("title", "")
    old_filename = todo_path.name
    changes: list[str] = []
    today = today_str()

    if args.title:
        frontmatter["title"] = args.title.strip()
        body = update_body_title(body, frontmatter["title"])
        changes.append(f"title → {frontmatter['title']}")

    if args.priority:
        if args.priority not in VALID_PRIORITY:
            emit_error(f"Invalid priority: {args.priority}", exit_code=2)
        frontmatter["priority"] = args.priority
        changes.append(f"priority → {args.priority}")

    if args.remove_due:
        frontmatter.pop("due_date", None)
        changes.append("due_date → removed")
    elif args.due:
        if not DATE_RE.match(args.due):
            emit_error(f"Invalid due date format: {args.due}", exit_code=2)
        frontmatter["due_date"] = args.due
        changes.append(f"due_date → {args.due}")

    if args.status:
        if args.status not in {"pending", "in_progress"}:
            emit_error("Status can only be updated to pending or in_progress via update", exit_code=2)
        frontmatter["status"] = args.status
        changes.append(f"status → {args.status}")

    tags = list(frontmatter.get("tags") or [])
    for tag in args.add_tag or []:
        if tag not in tags:
            tags.append(tag)
            changes.append(f"tag added → {tag}")
    for tag in args.remove_tag or []:
        if tag in tags:
            tags.remove(tag)
            changes.append(f"tag removed → {tag}")
    frontmatter["tags"] = tags

    if not changes:
        emit_error("No updates specified", exit_code=2)

    log_lines = [f"Updated: {change}" for change in changes]
    body = append_execution_log(body, today, log_lines)
    new_content = dump_frontmatter(frontmatter) + body

    validation_errors = validate_todo_content(new_content)
    if validation_errors:
        emit_error("Updated content failed validation", validation_errors=validation_errors)

    new_filename = old_filename
    if args.title and frontmatter["title"] != old_title:
        created_part = old_filename.split("_", 1)[0]
        new_slug = slugify(frontmatter["title"])
        new_filename = f"{created_part}_{new_slug}.md"
        counter = 2
        while (active_dir / new_filename).exists() and (active_dir / new_filename) != todo_path:
            new_filename = f"{created_part}_{new_slug}_{counter}.md"
            counter += 1

    new_path = active_dir / new_filename
    new_path.write_text(new_content, encoding="utf-8")
    if new_path != todo_path:
        todo_path.unlink()

    active_readme_path = active_dir / "README.md"
    _, entries = parse_active_readme(active_readme_path)
    updated_entries = []
    for entry in entries:
        if f"]({old_filename})" in entry:
            updated_entries.append(
                make_active_entry(
                    new_filename,
                    frontmatter.get("title", ""),
                    frontmatter.get("priority", "medium"),
                    frontmatter.get("due_date"),
                )
            )
        else:
            updated_entries.append(entry)
    write_active_readme(active_readme_path, updated_entries)

    root_readme_path = todos_dir / "README.md"
    active_count, completed_count, recent = parse_root_readme(root_readme_path)
    recent.insert(0, f'- {today}: Updated "{frontmatter.get("title", "")}"')
    write_root_readme(root_readme_path, count_todos(active_dir), completed_count, recent)

    emit(
        {
            "success": True,
            "operation": "update",
            "title": frontmatter.get("title"),
            "filename": new_filename,
            "path": str(new_path),
            "changes": changes,
            "valid": len(validate_file(new_path)) == 0,
        }
    )


def cmd_complete(args: argparse.Namespace) -> None:
    todos_dir = Path(args.dir).expanduser().resolve()
    active_dir = todos_dir / "active"
    completed_dir = todos_dir / "completed"
    if not active_dir.exists():
        emit_error(f"Active todos directory not found: {active_dir}", exit_code=2)
    completed_dir.mkdir(parents=True, exist_ok=True)

    todo_path = find_todo_by_slug(active_dir, args.slug)
    if todo_path is None:
        emit_error(f"Todo not found for slug/query: {args.slug}", exit_code=2)

    content = todo_path.read_text(encoding="utf-8")
    frontmatter, body, match = parse_frontmatter(content)
    if not match:
        emit_error("Todo file has invalid frontmatter", exit_code=2)

    today = today_str()
    frontmatter["status"] = "done"
    frontmatter["completed_at"] = today
    body = append_execution_log(
        body,
        today,
        ["Todo completed", "Status: done"],
    )
    new_content = dump_frontmatter(frontmatter) + body
    filename = todo_path.name
    title = frontmatter.get("title", filename)

    completed_path = completed_dir / filename
    counter = 2
    while completed_path.exists():
        stem = todo_path.stem
        completed_path = completed_dir / f"{stem}_{counter}.md"
        counter += 1

    completed_path.write_text(new_content, encoding="utf-8")
    todo_path.unlink()

    active_readme_path = active_dir / "README.md"
    _, entries = parse_active_readme(active_readme_path)
    entries = [entry for entry in entries if f"]({filename})" not in entry]
    write_active_readme(active_readme_path, entries)

    root_readme_path = todos_dir / "README.md"
    _, completed_count, recent = parse_root_readme(root_readme_path)
    active_count = count_todos(active_dir)
    completed_count = count_todos(completed_dir)
    recent.insert(0, f'- {today}: Completed "{title}"')
    write_root_readme(root_readme_path, active_count, completed_count, recent)

    emit(
        {
            "success": True,
            "operation": "complete",
            "title": title,
            "completed_at": today,
            "archived_path": str(completed_path),
            "filename": completed_path.name,
        }
    )


def cmd_find(args: argparse.Namespace) -> None:
    todos_dir = Path(args.dir).expanduser().resolve()
    active_dir = todos_dir / "active"
    if not active_dir.exists():
        emit_error(f"Active todos directory not found: {active_dir}", exit_code=2)

    query = args.query.lower().strip()
    matches = []
    for todo in list_active_todos(active_dir):
        haystacks = [
            (todo.get("title") or "").lower(),
            (todo.get("slug") or "").lower(),
            todo.get("filename", "").lower(),
        ]
        if any(query in value for value in haystacks):
            matches.append(todo)

    emit(
        {
            "success": True,
            "operation": "find",
            "query": args.query,
            "count": len(matches),
            "matches": matches,
        }
    )


def cmd_validate(args: argparse.Namespace) -> None:
    path = Path(args.file).expanduser().resolve()
    if not path.exists():
        emit_error(f"File not found: {path}", exit_code=2)

    errors = validate_file(path)
    emit(
        {
            "success": len(errors) == 0,
            "operation": "validate",
            "file": str(path),
            "valid": len(errors) == 0,
            "errors": errors,
        },
        exit_code=0 if not errors else 1,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic todo filesystem engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create .todos directory structure")
    init_parser.add_argument("--dir", required=True, help="Path to .todos directory")

    create_parser = subparsers.add_parser("create", help="Create a new todo")
    create_parser.add_argument("--dir", required=True, help="Path to .todos directory")
    create_parser.add_argument("--title", required=True, help="Todo title")
    create_parser.add_argument(
        "--priority", required=True, choices=sorted(VALID_PRIORITY), help="Priority"
    )
    create_parser.add_argument(
        "--due",
        required=True,
        help="Due date YYYY-MM-DD or 'none'",
    )
    create_parser.add_argument("--details", required=True, help="Task details body text")
    create_parser.add_argument(
        "--check",
        action="append",
        default=[],
        help="Checklist step (repeatable)",
    )
    create_parser.add_argument(
        "--force",
        action="store_true",
        help="Create even if a similar todo exists",
    )

    update_parser = subparsers.add_parser("update", help="Update an active todo")
    update_parser.add_argument("--dir", required=True, help="Path to .todos directory")
    update_parser.add_argument("--slug", required=True, help="Todo slug or title fragment")
    update_parser.add_argument("--title", help="New title")
    update_parser.add_argument("--priority", choices=sorted(VALID_PRIORITY))
    update_parser.add_argument("--due", help="New due date YYYY-MM-DD")
    update_parser.add_argument("--remove-due", action="store_true", help="Remove due date")
    update_parser.add_argument("--status", choices=["pending", "in_progress"])
    update_parser.add_argument("--add-tag", action="append", default=[])
    update_parser.add_argument("--remove-tag", action="append", default=[])

    complete_parser = subparsers.add_parser("complete", help="Complete and archive a todo")
    complete_parser.add_argument("--dir", required=True, help="Path to .todos directory")
    complete_parser.add_argument("--slug", required=True, help="Todo slug or title fragment")

    find_parser = subparsers.add_parser("find", help="Search active todos")
    find_parser.add_argument("--dir", required=True, help="Path to .todos directory")
    find_parser.add_argument("--query", required=True, help="Search query")

    validate_parser = subparsers.add_parser("validate", help="Validate a todo file")
    validate_parser.add_argument("--file", required=True, help="Path to todo .md file")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "init": cmd_init,
        "create": cmd_create,
        "update": cmd_update,
        "complete": cmd_complete,
        "find": cmd_find,
        "validate": cmd_validate,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
