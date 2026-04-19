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
│       ├── LICENSE           # (optional) Skill-specific license
│       ├── evals/
│       │   └── evals.json    # Evaluation cases for automated testing
│       ├── scripts/          # (optional) Helper scripts invoked by the skill
│       └── references/       # (optional) Reference data or lookup tables
├── AGENTS.md
└── README.md
```

## Usage

Install any skill into your Copilot agent environment by copying the skill directory into `~/.copilot/skills/`. The agent will discover and load it automatically on next startup.

```bash
cp -r skills/ffpa-analyzer ~/.copilot/skills/
```

## License

This project is released under the [MIT License](./LICENSE).
