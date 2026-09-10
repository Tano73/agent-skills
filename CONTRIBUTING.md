# Contributing to agent-skills

Thank you for your interest in contributing to **agent-skills**! This document provides guidelines and instructions to help you get started.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Skill Structure](#skill-structure)
- [Creating a New Skill](#creating-a-new-skill)
- [Modifying an Existing Skill](#modifying-an-existing-skill)
- [Evaluation Cases](#evaluation-cases)
- [Commit Convention](#commit-convention)
- [Development Workflow](#development-workflow)
- [Documentation](#documentation)
- [Security](#security)
- [License](#license)

## Code of Conduct

Please be respectful and constructive in all interactions. We are building tools to help developers, and we welcome contributions from everyone.

## Getting Started

### Prerequisites

- **Git** — for version control
- **Python 3** — if your skill includes helper scripts
- **A GitHub account** — to fork and submit pull requests

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/<your-username>/agent-skills.git
cd agent-skills
git remote add upstream https://github.com/Tano73/agent-skills.git
```

## Skill Structure

Every skill lives in `skills/<skill-name>/` and **must** contain:

```
skills/<skill-name>/
├── SKILL.md          # REQUIRED: skill definition with YAML frontmatter
├── evals/
│   └── evals.json    # REQUIRED: evaluation cases for automated testing
├── scripts/          # OPTIONAL: helper scripts invoked by the skill
├── bin/              # OPTIONAL: CLI executables / control scripts
└── references/       # OPTIONAL: reference data or lookup tables
```

### SKILL.md

The `SKILL.md` file is the core of every skill. It uses YAML frontmatter followed by Markdown instructions:

```markdown
---
name: skill-name
description: "One-paragraph description used by the agent to decide when to trigger this skill."
---

# Skill Title

## Overview

Description of what the skill does and when to use it.

## Workflow

Step-by-step instructions for the agent.
```

**Rules:**
- The `name` field **must** match the directory name exactly (kebab-case).
- The `description` field is the **trigger text** — the agent reads it to decide whether to invoke the skill. Make it explicit about activation keywords in Italian and English.
- Use ATX headings (`#`, `##`), fenced code blocks with language tags, and pipe tables.
- Reference bundled scripts with absolute paths: `$HOME/.agents/skills/<skill-name>/scripts/<file>`
- Reference data files with relative paths: `references/<file>`

### evals/evals.json

Evaluation cases test your skill against expected behavior. See [Evaluation Cases](#evaluation-cases) for the full format.

## Creating a New Skill

1. **Create the directory:**
   ```bash
   mkdir skills/<skill-name>
   mkdir skills/<skill-name>/evals
   ```

2. **Write `SKILL.md`** following the structure above.

3. **Create `evals/evals.json`** with at least one eval covering the main use case.

4. **Add helper scripts** (if needed) in `scripts/` and make them executable:
   ```bash
   chmod +x skills/<skill-name>/scripts/<script>.py
   ```

5. **Add reference data** (if needed) in `references/`.

6. **Update `README.md`:**
   - Add a row for the new skill in the Skills table.
   - Add an `npx skills add …` line in the Installation section.

7. **Update `AGENTS.md`** if your skill introduces a new domain or convention.

### Naming Conventions

- Directory names: **kebab-case** (e.g., `my-new-skill`)
- Script files: **snake_case** (e.g., `my_helper.py`)
- Reference files: descriptive names (e.g., `lookup_table.json`)

## Modifying an Existing Skill

- Changes to `SKILL.md` body sections (instructions, workflow, output format) are safe to make directly.
- If you change the `description` frontmatter, verify that existing evals still trigger correctly.
- If you change a helper script interface (arguments, output format), update both the script and the corresponding `SKILL.md` workflow section in the same commit.
- **Do not** rename a skill directory without updating all internal references (`name` frontmatter, `skill_name` in `evals.json`, script paths in `SKILL.md`).

## Evaluation Cases

The `evals/evals.json` file follows this structure:

```json
{
  "skill_name": "skill-name",
  "evals": [
    {
      "id": 0,
      "prompt": "User prompt that should trigger the skill.",
      "expected_output": "Human-readable description of the expected agent response.",
      "files": [],
      "expectations": [
        "Specific, verifiable assertion about the output."
      ]
    }
  ]
}
```

**Rules:**
- `skill_name` must match the directory name.
- `id` values must be unique integers, starting from 0.
- `files` lists any fixture files needed (paths relative to the eval runner working directory). Use `[]` when no files are needed.
- `expectations` should include verifiable assertions (programmatic or manual).
- Cover at least:
  - **Happy path** — the main use case working correctly
  - **Edge case** — unusual but valid input
  - **Negative case** — input that should *not* trigger the skill or should produce a graceful error

### Example Eval

```json
{
  "id": 0,
  "prompt": "Convert this PDF to Markdown",
  "expected_output": "The agent converts the PDF to Markdown using MinerU, preserving layout and tables.",
  "files": ["sample.pdf"],
  "expectations": [
    "Output is a valid Markdown file",
    "Tables are preserved",
    "Images are extracted to a separate directory"
  ]
}
```

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>
```

**Types:**
- `feat` — new feature or skill
- `fix` — bug fix
- `docs` — documentation changes
- `chore` — maintenance tasks, dependencies
- `refactor` — code restructuring without behavior change
- `test` — adding or updating tests
- `ci` — CI/CD changes

**Scope:** Use the skill name when the change is skill-specific.

**Examples:**
```
feat(ffpa-analyzer): add DWH guidelines
fix(todo-manager): handle empty todo list
docs(readme): update installation instructions
chore: update sync-skills.sh checksums
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feat/my-new-skill
```

### 2. Develop Your Skill

- Write `SKILL.md` and `evals/evals.json`
- Add any helper scripts in `scripts/`
- Test locally using `sync-skills.sh`:
  ```bash
  ./sync-skills.sh status    # check sync state
  ./sync-skills.sh sync      # push to ~/.agents/skills/
  ```

### 3. Test Your Skill

- Use the agent to verify the skill triggers correctly on your prompts
- Run through each eval case manually or with the skill-creator skill
- Verify that negative cases do *not* trigger the skill

### 4. Update Documentation

- Update `README.md` with the new skill entry
- Update `AGENTS.md` if introducing new conventions

### 5. Commit and Push

```bash
git add .
git commit -m "feat(my-skill): add new skill description"
git push origin feat/my-new-skill
```

### 6. Open a Pull Request

- Provide a clear title and description
- Reference any related issues
- Ensure all evals pass

## Documentation

### README.md

When adding a new skill, update:

1. **Skills table** — add a row with the skill name (linked) and description
2. **Installation section** — add an `npx skills add …` command
3. **Repository structure** — update if the new skill introduces a new directory pattern

### AGENTS.md

Update `AGENTS.md` if your skill:
- Introduces a new domain or convention
- Requires changes to agent behavior across the project
- Adds new reference data or lookup tables

### Code Style

Follow the conventions in `AGENTS.md`:
- **Markdown:** ATX headings, fenced code blocks with language tags, pipe tables
- **JSON:** 2-space indentation, no trailing commas
- **Python scripts:** Python 3, PEP 8, `if __name__ == "__main__":` guard, print usage to stderr on invalid arguments
- **Commit messages:** Conventional commits with skill name as scope

## Security

- **Never** embed credentials, tokens, or personal data in any file.
- `references/` files must contain normative/public domain data only — no proprietary client data.
- Review your skill for potential security issues before submitting.
- If you discover a security vulnerability, please report it privately via email rather than opening a public issue.

## License

This project is released under the [MIT License](./LICENSE). By contributing, you agree that your contributions will be licensed under the same license.

---

## Questions?

If you have questions about contributing, feel free to open an issue or reach out to the maintainers. We're happy to help!
