---
description: "Generates sync-skills.sh: a reusable shell script that shows sync status and performs interactive bidirectional synchronization between the repo skills/ directory and $HOME/.agents/skills/, using SHA-256 checksums."
mode: agent
tools: ["editFiles", "runCommands", "codebase"]
---

# Skill Sync Script Generator

You are a senior shell scripting expert with deep knowledge of bash, POSIX compatibility, and developer tooling. You write clean, well-commented, portable shell scripts.

## Task

Generate the file `sync-skills.sh` at the root of the current repository.

The script synchronizes agent skills between:
- **Repo source**: `<repo-root>/skills/` (auto-detected via `git rev-parse --show-toplevel`)
- **Install target**: `$HOME/.agents/skills/`

Scope is limited to the skill subdirectories found inside `skills/` — do not touch anything else in the install directory.

---

## Script interface

```
Usage: ./sync-skills.sh [status|sync] [-h|--help]
```

- `status` *(default when no argument is given)* — print the sync state of every skill, then exit with code `1` if any skill is out of sync, `0` if all are in sync.
- `sync` — interactive bidirectional sync; for each out-of-sync skill the user is prompted to choose the copy direction.
- `-h` / `--help` — print usage and exit `0`.

---

## status mode — required output

For each skill subdirectory in `<repo>/skills/`, print one line:

```
  ✓ IN SYNC        ffpa-analyzer
  ≠ DIFFERS        markdown-chapter-splitter
  → REPO ONLY      new-skill
  ← INSTALL ONLY   old-skill
```

After the list, print a summary:
```
─────────────────────────────────────────
  4 skills checked · 1 in sync · 2 differ · 1 repo-only · 0 install-only
```

Use ANSI colors when the terminal supports them (`tput colors` ≥ 8):
- ✓ green, ≠ yellow, → cyan, ← magenta, errors red.

---

## sync mode — required behaviour

1. Run the status check first to build the list of skills needing attention.
2. For each skill that is **not** IN SYNC, in order:
   a. Print a short diff summary (`diff -rq "<repo_skill_dir>" "<install_skill_dir>"` — or note that the skill is missing on one side).
   b. Prompt the user:
      ```
      [p] push  repo → install
      [u] pull  install → repo
      [s] skip
      Choice [p/u/s]:
      ```
   c. Execute the chosen action:
      - **push/pull**: use `rsync -a --delete` if available, otherwise `rm -rf <dst> && cp -r <src> <dst>`.
      - **skip**: do nothing, note it in the final summary.
3. Print a final summary of all actions taken.

---

## Technical requirements

- **Checksum**: compute a single SHA-256 fingerprint per skill directory by hashing all file contents (sorted by relative path). Use `sha256sum` on Linux and `shasum -a 256` on macOS (auto-detect with `command -v`).
- **Repo root**: detect automatically with `git rev-parse --show-toplevel`; abort with a clear error if not inside a git repo.
- **Install dir**: create `$HOME/.agents/skills/` if it does not exist (`mkdir -p`).
- **Compatibility**: target `bash` 3.2+ and `zsh` (shebang `#!/usr/bin/env bash`).
- **Executable**: the file must be created with execute permission (`chmod +x sync-skills.sh`).
- **Exit codes**: `0` = success/all in sync, `1` = differences found (status mode) or sync completed with skips, `2` = fatal error.

---

## Output file

Create `<repo-root>/sync-skills.sh` with:
1. Shebang `#!/usr/bin/env bash`
2. A header comment block with: script name, purpose, usage, and author placeholder
3. Inline comments for every non-obvious block of logic
4. `set -euo pipefail` at the top for safe error handling

---

## Validation steps

After writing the file:
1. Run `chmod +x sync-skills.sh` to make it executable.
2. Run `./sync-skills.sh --help` and confirm it prints usage without errors.
3. Run `./sync-skills.sh status` and confirm it lists all skills from the `skills/` directory.

Report the output of each command so the user can verify correctness.
