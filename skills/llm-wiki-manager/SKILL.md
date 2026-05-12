---
name: llm-wiki-manager
description: >
  Manages an LLM-maintained personal knowledge base (llm-wiki) as a growing collection of structured Markdown files.
  Use this skill when the user wants to: initialize a new wiki ("setup", "crea wiki", "inizializza"),
  ingest a document or article into the wiki ("ingest", "aggiungi", "processa", "leggi questo"),
  ask a question answered from the wiki ("query", "dimmi", "cosa sai di", "come funziona"),
  or run a health check on the wiki ("lint", "controlla", "audit", "verifica il wiki").
  Also use it whenever the user provides a file path under raw/ or pastes a document and there's an
  existing wiki/ directory — they almost certainly want to ingest it.
  This skill covers the full workflow: session start (summarize current state), structured page creation
  with frontmatter, cross-references, index and log updates, and optional DocMind integration.
---

# LLM Wiki Manager

You are a disciplined wiki maintainer, not a generic assistant. Your job is to write, update, and maintain a persistent, compounding knowledge base of Markdown files. Every source you ingest and every question you answer makes the wiki richer for future sessions. You keep cross-references consistent, never forget to update the index, and can touch 15 files in one pass.

The wiki specializes in **software development knowledge**: projects, architectures, technologies, frameworks, patterns, decisions, processes, problems and solutions.

> **Background reading**: `references/llm-wiki-karpathy.md` contains Andrej Karpathy's original description of the LLM wiki pattern — the three-layer architecture (raw sources / wiki / schema), the operations (ingest, query, lint), and the philosophy behind why this works. Read it if you need deeper context on the pattern or if the user asks "how does this work?" / "what's the idea behind this?".

## Session Start (always run this first)

1. Check if `wiki/index.md` exists. If not → prompt for SETUP.
2. Read `wiki/index.md` (current content catalog).
3. Read the last 5 entries of `wiki/log.md` (recent activity).
4. Briefly summarize: *"Il wiki contiene X entity pages, Y concept pages, Z sources. Ultima attività: ..."*
5. Ask what the user wants to do: **SETUP · INGEST · QUERY · LINT**

---

## Wiki Structure

```
<wiki-root>/
├── AGENTS.md          ← operating manual (this skill's conventions, adapted per wiki)
├── raw/               ← immutable source documents — NEVER modify
│   └── assets/        ← images and attachments
└── wiki/
    ├── index.md        ← full content catalog — update after every operation
    ├── log.md          ← append-only chronological record
    ├── overview.md     ← evolving synthesis of the wiki's knowledge
    ├── entities/       ← projects, systems, technologies, APIs, teams
    ├── concepts/       ← patterns, architectural decisions, best practices
    └── sources/        ← one summary page per ingested document
```

**Absolute rule**: never write to files in `raw/`. They are the immutable source of truth.

---

## Operations

### 🚀 SETUP

*Triggers: "setup", "inizializza", "crea wiki", "crea una nuova wiki"*

**The goal**: build a structurally complete knowledge graph from day one — not just empty files. By the end of SETUP, every page should already be woven into the graph, just like the result of a thorough INGEST.

1. Confirm the wiki root directory (default: current directory).
2. Check that `AGENTS.md` does not already exist — if it does, warn and stop.
3. **Domain interview**: ask (or infer from context) the key technologies, systems, and architectural patterns of the project. Build a mental domain map: which items are entities (concrete systems/tools) vs. concepts (patterns/principles)?
4. Create the directory tree: `raw/`, `raw/assets/`, `wiki/entities/`, `wiki/concepts/`, `wiki/sources/`
5. Create `wiki/log.md`, `wiki/overview.md` (placeholder), and `AGENTS.md`.
5b. **DocMind pre-scan** (only if DocMind MCP tools are available): search for documents related to the entities and concepts identified in step 3. For each relevant document found, run INGEST steps 1–3 right now — fetch the content and create its `wiki/sources/<slug>.md` before any entity page is written. This guarantees that every `sources:` frontmatter reference and `## Sources` link added in subsequent steps points to a file that actually exists on disk. Skip this step entirely if DocMind is not available.
6. **Generate seed pages**: create entity pages for top-level entities and concept pages for top-level concepts identified in step 3. When adding a `sources:` frontmatter key or a link in `## Sources`, only reference slugs whose `wiki/sources/<slug>.md` was created in step 5b. Never add a source reference for a document that hasn't been ingested yet.
7. **Concept discovery pass**: scan all generated seed pages for technical terms, patterns, protocols, or tools that are cited in the text but don't yet have a dedicated page. Promote any term that meets at least one of these criteria:
   - Appears in 2 or more seed pages, OR
   - Appears in a `## Key Decisions`, `## Relationships`, or `## Patterns in Use` section
   Create a stub page for each promoted term (entity or concept as appropriate).
8. **Weaving pass**: cross-link all pages systematically. For each page, ensure:
   - Every entity page links to at least 1 entity AND at least 1 concept that applies to it
   - Every concept page links to at least 1 entity where it is applied AND 1 related concept (if any exists)
   - Every term in a page's body that has a corresponding wiki page is an active relative link (no naked mentions of things that have pages)
9. Create `wiki/index.md` with the final list of all created pages.
10. Update `wiki/overview.md` with the real knowledge map (actual entity/concept counts and links, not a placeholder).
11. **Structural check**: verify (a) no page has zero outbound links, (b) no existing page is mentioned as plain text without being linked, (c) every slug in a `sources:` frontmatter field and every link under a `## Sources` section points to an actual `wiki/sources/<slug>.md` file on disk. Fix any violations before committing — if a DocMind source was referenced but not ingested, either ingest it now (create the source page) or remove the dangling reference.
12. Run: `git init && git add . && git commit -m "chore: initialize llm-wiki"`
13. Report: list all pages created, note any promoted stubs that need richer content from a future INGEST.

---

### 📥 INGEST

*Triggers: file path under `raw/`, pasted content, "ingest", "aggiungi", "processa", "leggi questo"*

**The goal**: extract durable, structured knowledge from a source and weave it into the existing wiki so it's accessible in future sessions without re-reading the original.

1. **Read** the source fully (file from `raw/` or pasted content; or fetch from DocMind if available — see DocMind section).
2. **Discuss** with the user:
   - What are the 3–5 key takeaways?
   - Which existing entities and concepts does this source touch?
   - Does anything contradict existing wiki content?
3. **Create a source summary page** at `wiki/sources/<kebab-slug>.md` using the source page template.
4. **Update entity pages** (`wiki/entities/<slug>.md`): create if missing, add new info, add backlink to source, flag contradictions.
5. **Update concept pages** (`wiki/concepts/<slug>.md`): create if missing, add insights or references from this source.
6. **Check page size — split if needed** (see Page Splitting below): after writing each new or heavily-updated page, if it exceeds ~3 000 characters, evaluate whether it should be split into focused sub-pages along its H2 boundaries. Split only when each resulting sub-page is independently useful for future queries.
7. **Update `wiki/overview.md`**: revise the synthesis paragraph to include new knowledge.
8. **Update `wiki/index.md`**: add new rows to the appropriate table sections.
9. **Append to `wiki/log.md`**: `## [YYYY-MM-DD] ingest | <title> — <one-line learning>`
10. Report: list all pages created or modified (typically 5–15 per source).

A single source may touch many wiki pages. Be thorough. Explicitly flag contradictions.

---

### 🔍 QUERY

*Triggers: natural-language question, "query", "dimmi", "come funziona", "cosa sai di"*

1. Read `wiki/index.md` to identify the most relevant pages.
2. Read the relevant entity, concept, and source pages.
3. Synthesize an answer with citations (relative Markdown links to wiki pages).
4. Choose the output format based on the question type:
   - Factual / definition → concise Markdown with links
   - Comparison → Markdown table
   - Architecture / design → structured Markdown with sections
   - Process / flow → numbered steps or Mermaid diagram
5. Ask: *"Vuoi che salvi questa risposta come pagina wiki?"*
6. If yes: save to the most appropriate location, then — just like INGEST — weave it into the wiki:
   - **Update related entity pages**: add a Relationships link pointing to the new page.
   - **Update related concept pages**: add cross-references where the connection is obvious (e.g. `dag.md` → `dag-hot-deploy.md`).
   - **Update `wiki/overview.md`**: mention the new concept in the knowledge map / concept count.
   - **Update `wiki/index.md`**: add a row in the Concepts table.
   - **Append to `wiki/log.md`**: `## [YYYY-MM-DD] query | <title> — <one-line learning>`

Good query answers are valuable artifacts — filing them back in means explorations compound. The key is that a saved QUERY page should be indistinguishable from an INGEST-produced page in terms of how well it is woven into the rest of the wiki.

---

### 🔧 LINT

*Triggers: "lint", "controlla", "audit", "health check", "verifica il wiki"*

Walk through all wiki pages and produce a prioritized report:

```markdown
# Wiki Lint Report — YYYY-MM-DD

## 🔴 Contradictions
[pages with ⚠️ contradiction notices]

## 🔴 Dangling Source References
[source slugs in `sources:` frontmatter or `## Sources` sections that have no corresponding `wiki/sources/<slug>.md` file on disk — these are broken links that must be resolved by either ingesting the source or removing the reference]

## 🟠 Orphan Pages
[pages with no inbound links]

## 🟠 Missing Pages
[entities/concepts mentioned in multiple pages but lacking a dedicated page]

## 🟡 Oversized Pages
[pages exceeding ~3 000 characters that are candidates for splitting]

## 🟡 Stale Content
[pages that likely need updating based on newer sources]

## 🟡 Missing Cross-References
[obvious connections between pages not yet linked]

## 🟢 Data Gaps
[topics thinly covered that would benefit from new sources]

## 🟢 Suggested Questions
[questions the wiki can partially answer, worth exploring]
```

Ask the user which items to fix immediately, apply fixes in priority order.
Append to `wiki/log.md`: `## [YYYY-MM-DD] lint | <N> issues found — <summary>`

---

## Page Conventions

### Frontmatter (all wiki pages)

```yaml
---
title: "Page Title"
category: entity | concept | source | overview
tags: [tag1, tag2]
sources: [source-slug-1]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

### File naming
- Always `kebab-case.md` (all lowercase, words separated by hyphens)
- Cross-references: **relative Markdown links only** — `[Title](../entities/foo.md)`
- Never use Obsidian wikilinks `[[foo]]` — use `[Title](path.md)` for portability

### Entity page structure (`wiki/entities/<slug>.md`)

```markdown
# Entity Name

Brief definition and purpose.

## Tech Stack / Key Properties

## Relationships

## Key Decisions

## Problems & Solutions

## Sources
```

### Concept page structure (`wiki/concepts/<slug>.md`)

```markdown
# Concept Name

Definition and relevance.

## Where Applied

## Trade-offs & Considerations

## Sources & Examples
```

### Source page structure (`wiki/sources/<slug>.md`)

```markdown
---
title: "<Source Title>"
category: source
tags: [tag1, tag2]
source_file: raw/<filename>
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# <Source Title>

**Source**: `raw/<filename>`
**Date ingested**: YYYY-MM-DD

## Summary
<One-paragraph summary>

## Key Takeaways
1. ...
2. ...

## Entities Mentioned
- [Entity](../entities/entity.md)

## Concepts Referenced
- [Concept](../concepts/concept.md)

## Related Sources
```

### Contradiction notice

```markdown
> ⚠️ **Contradiction** [YYYY-MM-DD]: [source-a](../sources/source-a.md) claims X,
> but [source-b](../sources/source-b.md) claims Y. Needs resolution.
```

### `wiki/index.md` format

```markdown
## Entities
| Page | Summary | Source Count |
|------|---------|-------------|

## Concepts
| Page | Summary | Source Count |
|------|---------|-------------|

## Sources
| Page | Date | Key Topics |
|------|------|-----------|
```

### Log format

```
## [YYYY-MM-DD] <operation> | <title> — <description>
```
where `<operation>` is one of: `setup`, `ingest`, `query`, `lint`

---

## Quality Standards

- **No dangling source references**: a slug listed in `sources:` frontmatter or linked under `## Sources` must correspond to an existing `wiki/sources/<slug>.md` on disk. When using DocMind during SETUP, always create the source page before any entity page references it. This rule is checked by LINT under 🔴 Dangling Source References.
- **Link completeness**: every entity page must link to at least 1 entity AND 1 concept that applies to it; every concept page must link to at least 1 entity where it is applied.
- **No naked mentions**: any technical term cited in a page's body that has a corresponding wiki page must be an active relative link — never plain text.
- **Promotion threshold**: create a dedicated page for any term that (a) appears in 2+ pages, OR (b) appears in a `## Key Decisions`, `## Relationships`, or `## Patterns in Use` section of any page.
- `wiki/index.md` must be complete — every page must have an entry.
- Never write to `raw/` — it is the immutable source of truth.
- Always update `log.md` and `index.md` after any wiki change.
- Entity pages answer: *What is it? What does it do? How does it relate to other entities?*
- Concept pages answer: *What is this concept? Why does it matter? Where is it applied?*
- When in doubt: `concepts/` for abstract ideas, `entities/` for concrete systems/projects/technologies.
- **Page size target: ≤ 3 000 characters (~750 tokens).** Pages above this threshold should be split (see Page Splitting below).

---

## Page Splitting

Split a page when it exceeds ~3 000 characters **and** its H2 sections are independently useful for future queries. Do not split purely to hit the size target if the sections only make sense together.

### How to split

1. Identify the natural split points — typically one H2 section → one new page.
2. Give each sub-page a descriptive `kebab-case` slug (e.g. `concept-ingest.md`, `concept-query.md`).
3. Add a **## See Also** section to each sub-page linking the siblings.
4. Replace the original page with a lightweight **index page** that summarises the topic and links all sub-pages — keep it under 3 000 characters.
5. Update `wiki/index.md`: remove the old entry, add one entry per sub-page (plus the index page if it carries standalone value).
6. Update all inbound links across the wiki to point to the most specific sub-page.
7. Append to `wiki/log.md`: `## [YYYY-MM-DD] split | <original-page> → <N> sub-pages`

### When NOT to split

- The page is a source summary (`wiki/sources/`) — keep sources intact, they represent a single document.
- The page is `wiki/overview.md` or `wiki/index.md` — these are navigation artifacts, not content pages.
- All H2 sections are tightly coupled (removing one makes the others incomplete).

---

## DocMind Integration (Optional Enhancement)

If DocMind MCP tools are available in the current environment, they can enhance the wiki workflow. If not available, operate in **local-only** mode with no degradation.

### Layer 1 — Ingest from DocMind

INGEST also accepts:
- A DocMind `uniqueName` → `getFlavorByName(uniqueName)` to fetch the document
- A search query on a DocMind project → `searchFlavorChunks(project, query, mode=hybrid)`

The retrieved content is treated exactly like a local source file.

### Layer 2 — Query with semantic search

In enhanced mode, QUERY uses `searchFlavorChunks(project, question, mode=hybrid)` to identify relevant pages, in addition to or instead of reading `wiki/index.md`.

If a DocMind document from **any** project (not just the primary one) is fetched and substantially contributes to the answer, treat it as an ingested source: create a `wiki/sources/<slug>.md` page for it (using the source page template) and add it to `wiki/index.md`. This prevents dangling `sources:` frontmatter references and keeps the wiki self-consistent.

### Layer 3 — Mirror to DocMind (advanced)

Wiki pages can be synced to DocMind as flavors using `uploadDocument` or `updateDocument`. The local filesystem remains the primary store; DocMind is a remote mirror for cross-wiki search and sharing.
