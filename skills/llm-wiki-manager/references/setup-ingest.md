# SETUP and INGEST — the two write workflows

Read this file when you are creating a new wiki (SETUP) or adding a source to an
existing one (INGEST). Both are heavy write operations: they touch many files, so
the bookkeeping (index, log) is delegated to scripts and only the reasoning that
needs a human stays in your hands.

The **raw/ immutability rule** and the **confirmation gates** below apply to every
step of both workflows.

---

## SETUP

*Triggers: "setup", "inizializza", "crea wiki", "crea una nuova wiki"*

**Goal:** a structurally complete, well-linked knowledge graph from day one — not
empty folders. The wiki is an OKF bundle (see `references/okf.md`) maintained by
Karpathy's LLM-wiki pattern (see `references/llm-wiki-karpathy.md`).

1. **Determine the wiki root** (smart-default logic):
   a. cwd already has a project `AGENTS.md` → propose `./knowledge/` as the wiki
      root (avoids colliding with the project's operating manual).
   b. cwd has no `AGENTS.md` → propose the cwd itself.
   c. **Always confirm the proposed root** before proceeding. Accept overrides
      (`docs/wiki/`, `kb/`, …). Create the directory if it does not exist yet.
2. Check `<wiki-root>/AGENTS.md` does not already exist — if it does, warn and
   stop. (An `AGENTS.md` in a parent project directory is fine.)
3. **Domain interview**: ask (or infer) the key technologies, systems and patterns.
   Map entities vs concepts. This determines which folders and seeds to build.
4. Create the tree: `raw/`, `raw/assets/`, `wiki/entities/`, `wiki/concepts/`,
   `wiki/sources/`.
5. Create `wiki/log.md` (via `wiki_log.py init`), `wiki/overview.md` (placeholder),
   and `AGENTS.md` with this skill's conventions adapted to the wiki's domain
   (page taxonomy, naming, DocMind binding if DocMind is used).
6. **DocMind pre-scan** (only if DocMind tools are available): follow
   `references/docmind.md` Layer 1 SETUP 5b. Skip if unavailable.
7. **Generate seed pages** for top-level entities and concepts. Use the templates
   in `references/okf.md`. Only reference source slugs that already exist on disk.
8. **Concept discovery pass**: promote terms appearing in 2+ seed pages, or under
   `## Key Decisions` / `## Relationships` / `## Patterns in Use`, into stub pages.
9. **Weaving pass**: every entity links to ≥1 entity and ≥1 concept; every concept
   links to ≥1 entity and ≥1 related concept when one exists; no naked mentions of
   pages that exist.
10. **Regenerate the index** (never hand-write it):
    ```bash
    python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_index.py <wiki-root> --write
    ```
11. Update `wiki/overview.md` with the real knowledge map (not a placeholder).
12. **Log the operation**:
    ```bash
    python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_log.py <wiki-root> append \
      --op setup --title "<wiki-name>" --note "Initial structure"
    ```
13. **Structural check** (see `references/lint.md`):
    ```bash
    python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_lint.py <wiki-root>
    ```
    Fix high/medium findings before offering a commit.
14. **Git versioning — propose, do not commit silently**:
    a. Detect parent repo: `git -C <wiki-root> rev-parse --is-inside-work-tree 2>/dev/null`
    b. Show the user the exact commands you would run (parent-repo commit vs
       `git init` at the wiki root) and the proposed message.
    c. **Wait for explicit confirmation** before `git init` / `git add` /
       `git commit`. If the user declines, leave the files unversioned and say so.
    d. If git is not installed, report and skip.
15. Report: list all pages created; note stubs that need a future INGEST.

---

## INGEST

*Triggers: file path under `raw/`, pasted content, "ingest", "aggiungi",
"processa", "leggi questo"*

**Goal:** extract durable knowledge and weave it into the wiki so future sessions
never need to re-read the original. Be thorough and explicitly flag contradictions
with existing pages.

### Step 1 — Put the source in `raw/` (immutable)

- Already under `raw/` → read it.
- Local path outside `raw/` → propose copying into `raw/<filename>`, wait for
  confirmation, then run the versioning check.
- Pasted content → propose `raw/<slug>.md`, confirm, then run the versioning check.
- DocMind uniqueName / search → see `references/docmind.md` Layer 1.

**Before writing anything to `raw/`**, run the deterministic versioning check —
never compare content by eye:

```bash
# existing local file:
python3 $HOME/.agents/skills/llm-wiki-manager/scripts/raw_check.py <wiki-root> <file-path>

# pasted content:
printf '%s' "<content>" | python3 $HOME/.agents/skills/llm-wiki-manager/scripts/raw_check.py <wiki-root> <slug>.md --stdin
```

| Decision | Meaning | Action |
| --- | --- | --- |
| `create` | no raw file has this name | write it as `raw/<name>` and proceed |
| `identical` | raw file exists with identical content | **on a direct INGEST stop** (nothing to do); during SETUP 5b / QUERY auto-ingest reuse it and continue |
| `version` | raw file exists with different content | ask whether to save as `raw/<name-vN>`; on no, stop without overwriting |
| `duplicate` | same content already lives under another raw name | reuse that file; do not create a second copy |

**Never modify or delete an existing file in `raw/`.** Once a file is in `raw/` it
is immutable; new versions live beside it as `<slug>-vN.md`.

### Step 2 — Discuss the content with the user

Agree on 3–5 key takeaways, which entities/concepts are touched, and any
contradictions with existing pages. This human checkpoint is where `verified:` trust
is earned (see `references/okf.md`).

### Step 3 — Create the source page

`wiki/sources/<source-slug>.md`, same slug as the raw file, using the source page
template in `references/okf.md` (`type: source`, `resource: raw/<filename>`).

### Step 4 — Weave the knowledge (the compounding step)

- Update touched entity pages; create missing ones; backlink the source under
  `## Sources`; flag contradictions with the notice format in `references/okf.md`.
- Update touched concept pages; create missing ones.
- Update `wiki/overview.md` with what changed in the knowledge map.

### Step 5 — Bookkeeping via scripts (never by hand)

```bash
# regenerate the catalog
python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_index.py <wiki-root> --write

# append the history entry
python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_log.py <wiki-root> append \
  --op ingest --title "<source title>" --note "<one-line learning>"
```

### Step 6 — Report

List every page created or modified. Do not run LINT automatically — offer it.

**Expected output:** a source page + N touched entity/concept pages + regenerated
index + one log entry.