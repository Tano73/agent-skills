# agent-skills

A curated collection of **skills for GitHub Copilot coding agents** — reusable, installable modules that extend the agent's capabilities with domain-specific knowledge and behaviour.

Each skill is a self-contained directory containing a `SKILL.md` prompt file, evaluation cases, and optional helper scripts or reference data.

## Skills

| Skill | Description |
|-------|-------------|
| [ffpa-analyzer](./skills/ffpa-analyzer/) | Function Point analysis using the FFPA methodology (Fast Function Points Analysis — Gartner). Counts and sizes software from source code, specs, user stories, or textual descriptions. |
| [markdown-chapter-splitter](./skills/markdown-chapter-splitter/) | Splits large Markdown files into smaller files, one per chapter. Detects H1 headings and inferred text-based chapter markers automatically. |
| [pandoc-convert](./skills/pandoc-convert/) | Converts documents between formats (Markdown, DOCX, PDF, HTML, EPUB, …) using pandoc. |
| [wbs-generator](./skills/wbs-generator/) | Generates a detailed Work Breakdown Structure (WBS) in Markdown and CSV from ENGenius DESIGN/DEVELOPER documents stored on DocMind. Includes a CSV syntax validator (`scripts/validate_wbs_csv.py`) that checks structure, valid complexity codes, numeric fields, and formula consistency; the skill loops until the CSV passes validation before uploading. |
| [llm-wiki-manager](./skills/llm-wiki-manager/) | Manages an LLM-maintained personal knowledge base (llm-wiki) as a growing collection of structured Markdown files. Supports setup, document ingestion, knowledge queries, and wiki health checks. |
| [skill-security-auditor](./skills/skill-security-auditor/) | Audits skill definitions (`SKILL.md` and bundled scripts) for malicious, deceptive, or dangerous content before installation. Triggers on any safety review request for a skill. |
| [smart-router](./skills/smart-router/) | Routes tasks to the most cost-effective AI model by scoring task complexity with a cheap analyzer model, then executing with the best-fit tier (`cheap`, `balanced`, `heavy`, `frontier`, `code-mid`, `code-heavy`). Supports multi-client configuration (Cursor, Claude Code, Codex CLI, …). |
| [team-kb](./skills/team-kb/) | Answers questions from the team's knowledge base stored in DocMind. Searches team documentation, project specs, architecture decisions, technical requirements, and API specs. |
| [todo-manager](./skills/todo-manager/) | Manages personal todo items in a `Todos/` directory on the filesystem: create, update, and complete tasks. Includes a `validate_todo.py` script that checks frontmatter fields, date formats, and required Markdown sections. |

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
npx skills add https://github.com/Tano73/agent-skills --skill llm-wiki-manager
npx skills add https://github.com/Tano73/agent-skills --skill skill-security-auditor
npx skills add https://github.com/Tano73/agent-skills --skill smart-router
npx skills add https://github.com/Tano73/agent-skills --skill team-kb
npx skills add https://github.com/Tano73/agent-skills --skill todo-manager
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
