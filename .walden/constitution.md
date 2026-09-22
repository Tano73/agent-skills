# Project Constitution

This file captures stable project-wide context that applies across all features. It is optional and does not participate in the approval workflow.

## Project Summary

Repository of "agent skills" for GitHub Copilot CLI: each skill is a folder under `skills/<name>/` with `SKILL.md` (instructions), `references/`, `scripts/`, `evals/`. Synced to local machines via `sync-skills.sh`.

## Tech Stack

Markdown + YAML frontmatter as the primary content format. Supporting Python scripts (e.g. `wiki_lint.py` in `llm-wiki-manager`). No compiled application language at the core of the repo.

## Conventions

kebab-case file names; each skill's `SKILL.md` is its behavioral contract; the frontmatter conventions for wiki pages are defined inside `llm-wiki-manager`'s `SKILL.md`.

## Sanity Checks

```bash
python3 skills/llm-wiki-manager/scripts/wiki_lint.py <wiki-root>
```

No broader automated test suite is known in this repo beyond the mechanical checks above.

## Key Files

- `skills/llm-wiki-manager/SKILL.md` — operating manual and page/frontmatter conventions
- `skills/llm-wiki-manager/scripts/wiki_lint.py` — mechanical validation script
- `skills/llm-wiki-manager/references/` — on-demand reference docs (Karpathy pattern, DocMind integration)

## Hard Rules

- Never modify or delete existing files in a user's `raw/` directory (wiki content rule, not repo-level, but binding on any skill change that touches ingest behavior).
