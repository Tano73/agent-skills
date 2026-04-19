# agent-skills

A curated collection of **skills for GitHub Copilot coding agents** — reusable, installable modules that extend the agent's capabilities with domain-specific knowledge and behaviour.

Each skill is a self-contained directory containing a `SKILL.md` prompt file, evaluation cases, and optional helper scripts or reference data.

## Skills

| Skill | Description |
|-------|-------------|
| [ffpa-analyzer](./skills/ffpa-analyzer/) | Function Point analysis using the FFPA methodology (Fast Function Points Analysis — Gartner). Counts and sizes software from source code, specs, user stories, or textual descriptions. |
| [markdown-chapter-splitter](./skills/markdown-chapter-splitter/) | Splits large Markdown files into smaller files, one per chapter. Detects H1 headings and inferred text-based chapter markers automatically. |
| [pandoc-convert](./skills/pandoc-convert/) | Converts documents between formats (Markdown, DOCX, PDF, HTML, EPUB, …) using pandoc. |
| [wbs-generator](./skills/wbs-generator/) | Generates a detailed Work Breakdown Structure (WBS) in Markdown and CSV from ENGenius DESIGN/DEVELOPER documents stored on DocMind. |

## Repository structure

```
agent-skills/
├── skills/
│   └── <skill-name>/
│       ├── SKILL.md          # Skill definition: YAML frontmatter + agent instructions
│       ├── evals/
│       │   └── evals.json    # Evaluation cases for automated testing
│       ├── scripts/          # (optional) Helper scripts invoked by the skill
│       └── references/       # (optional) Reference data or lookup tables
├── sync-skills.sh            # Sync tool: repo skills/ ↔ ~/.agents/skills/
├── AGENTS.md
├── LICENSE
└── README.md
```

## Installation

### End users — via `npx skills`

Install individual skills directly from GitHub:

```bash
npx skills add https://github.com/Tano73/agent-skills --skill ffpa-analyzer
npx skills add https://github.com/Tano73/agent-skills --skill markdown-chapter-splitter
npx skills add https://github.com/Tano73/agent-skills --skill pandoc-convert
npx skills add https://github.com/Tano73/agent-skills --skill wbs-generator
```

Update all installed skills:

```bash
npx skills update
```

### Contributors — via `sync-skills.sh`

Use `sync-skills.sh` to synchronize skills between your local repo checkout and `~/.agents/skills/` during development:

```bash
# Show sync status between repo and ~/.agents/skills/
./sync-skills.sh status

# Interactively sync REPO_ONLY and DIFFERS skills
./sync-skills.sh sync

# Also include skills present only in the install dir
./sync-skills.sh sync --all
```

## License

This project is released under the [MIT License](./LICENSE).
