# AGENTS.md

## Project overview

This repository contains a collection of **skills for GitHub Copilot coding agents**. Each skill is a self-contained directory that the agent installs and executes to handle specific domains (function point sizing, document conversion with pandoc, high-fidelity PDF/image → Markdown with MinerU, chapter splitting, WBS generation, LLM-maintained wiki management, team knowledge base queries, skill security auditing, AI model cost routing, personal todo management, etc.).

There are no build steps, no compiled artifacts, and no package manager. The repo is composed of Markdown files, JSON evaluation cases, and occasional Python helper scripts.

## Repository structure

```
agent-skills/
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md          # Skill definition (required)
│       ├── evals/
│       │   └── evals.json    # Evaluation cases (required)
│       ├── scripts/          # Python or shell helper scripts (optional)
│       ├── bin/              # CLI executables / control scripts (optional, alternative to scripts/)
│       └── references/       # Reference data / lookup tables (optional)
├── instructions/             # Reusable agent instruction snippets
│   ├── Karpaty-Code.md       # Behavioral coding guidelines (Think Before Coding, Simplicity First, …)
│   └── team-kb.md            # Team knowledge base search instructions
├── sync-skills.sh            # Sync tool: repo skills/ ↔ ~/.agents/skills/
├── .gitignore                # Ignores skill-creator eval workspaces (`*-workspace/`)
├── AGENTS.md
├── LICENSE
└── README.md
```

Every skill **must** have `SKILL.md` and `evals/evals.json`. Everything else is optional.

Eval runs created by the skill-creator skill live in sibling directories named `<skill-name>-workspace/` (iteration outputs, fixtures, sandbox stubs). Those directories are gitignored via `*-workspace/` and must not be committed.

## SKILL.md anatomy

Each `SKILL.md` starts with a YAML frontmatter block followed by Markdown agent instructions:

```markdown
---
name: skill-name
description: "One-paragraph description used by the agent to decide when to trigger this skill."
---

# Skill Title

## Section
...
```

Rules for `SKILL.md`:
- The `name` field must match the directory name exactly (kebab-case).
- The `description` field is the **trigger text** — the agent reads it to decide whether to invoke the skill. Make it explicit about activation keywords (in any language if the skill is multilingual).
- Body sections are free-form Markdown. Use `##` for top-level sections inside the skill.
- Reference any bundled scripts with absolute paths using `$HOME/.agents/skills/<skill-name>/scripts/<file>` (or `bin/<file>` if the skill uses a `bin/` directory).
- Reference any bundled data files with relative paths like `references/<file>`.

## evals/evals.json anatomy

```json
{
  "skill_name": "skill-name",
  "evals": [
    {
      "id": 0,
      "prompt": "User prompt that should trigger and exercise the skill.",
      "expected_output": "Human-readable description of the expected agent response.",
      "files": [],
      "expectations": [
        "Specific, verifiable assertion about the output."
      ]
    }
  ]
}
```

- `skill_name` must match the directory name.
- `id` values must be unique integers within the array, starting from 0.
- `files` lists any fixture files needed by the eval (paths relative to the eval runner working directory). Use `[]` when no files are needed.
- `expectations` is optional but recommended — list each assertion as a plain-English sentence that an evaluator can check programmatically or manually.
- Cover at least: the happy path, an edge case, and a negative case (input that should *not* trigger the skill or should produce a graceful error).

## Syncing skills

Use `sync-skills.sh` to synchronize skills between the repo and `$HOME/.agents/skills/`:

```bash
./sync-skills.sh status        # show sync state of all skills
./sync-skills.sh sync          # interactive sync (REPO_ONLY + DIFFERS)
./sync-skills.sh sync --all    # also include INSTALL_ONLY skills
```

The script uses SHA-256 checksums to detect differences and `rsync` (with `cp` fallback) for copying.

## Instructions directory

The `instructions/` directory contains **reusable agent instruction snippets** — Markdown files that can be embedded verbatim into an `AGENTS.md`, a system prompt, or a Copilot coding agent configuration. They are not skills and do not have `evals/`.

| File | Purpose |
|------|---------|
| `Karpaty-Code.md` | Behavioral coding guidelines (Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution). Drop into any repo's `AGENTS.md` to reduce common LLM coding mistakes. |
| `team-kb.md` | Search strategy for the team knowledge base in DocMind. Use as the system prompt context for any agent that must answer questions from internal documentation. |

To add a new instruction snippet: create a `.md` file in `instructions/` with a clear `# Title` heading, and document it in the table above and in `README.md`.

## Adding a new skill

1. Create a new directory under `skills/`: `mkdir skills/<skill-name>`
2. Add `SKILL.md` with the required frontmatter and instructions.
3. Add `evals/evals.json` with at least one eval covering the main use case.
4. If the skill needs a helper script, place it in `scripts/` and make it executable.
5. If the skill references lookup tables or normative data, place them in `references/`.
6. Update `README.md` to add a row for the new skill in the Skills table and an `npx skills add …` line in the Installation section.
7. If the skill introduces a new domain or convention for the repo, also refresh the overview / structure notes in `AGENTS.md`.

## Modifying an existing skill

- Changes to `SKILL.md` body sections (instructions, workflow steps, output format) are safe to make directly.
- If you change the `description` frontmatter, verify that existing evals still trigger correctly.
- If you change a helper script interface (arguments, output format), update both the script and the corresponding `SKILL.md` workflow section in the same commit.
- Do **not** rename a skill directory without updating all internal references (`name` frontmatter, `skill_name` in `evals.json`, script paths in `SKILL.md`).

## Testing

There is no automated test runner configured in this repo. Evals are executed manually or via the Copilot skill-creator skill.

To run an eval manually, copy the `prompt` from `evals.json` into the agent chat and verify the response against `expected_output` and each item in `expectations`.

When using skill-creator for a full with-skill / baseline comparison, put results under `<skill-name>-workspace/` next to `skills/` (not inside the skill directory). That path is ignored by git; only keep `evals/evals.json` inside the skill as the durable test definition.

## Code style

- Markdown: use ATX headings (`#`), fenced code blocks with language tags, and pipe tables.
- JSON: 2-space indentation, no trailing commas.
- Python scripts (in `scripts/`): Python 3, follow PEP 8, include a `if __name__ == "__main__":` guard, and print usage to stderr on invalid arguments.
- Commit messages: use conventional commits (`feat:`, `fix:`, `docs:`, `chore:`). Scope to the skill name when the change is skill-specific (e.g. `feat(ffpa-analyzer): add DWH guidelines`).

## Security

- Do not embed credentials, tokens, or personal data in any file.
- `references/` files contain normative/public domain data only — no proprietary client data.
