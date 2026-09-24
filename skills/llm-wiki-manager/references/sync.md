# SYNC — keeping the wiki current with implementation changes

Read this file when running the SYNC operation: after an implementation/PR
merged, after a behavior/config/API change, or on request ("sync", "sincronizza
il wiki", "aggiorna il wiki ai cambi"). SYNC turns the wiki update from
on-demand (INGEST/QUERY) into a **push step** of the implementation loop, so the
wiki reflects what the code actually does — not what it did when it was ingested.

**Scope guard:** SYNC extracts **durable knowledge** (Key Decisions, Tech Stack,
Relationships, API surface / config that matters, patterns). It never records
one-off implementation detail. Apply the 6-month test: *"will this still matter
in 6 months?"* — yes → wiki, no → leave it in the code.

---

## The project hook (make it automatic)

For the wiki to stay current, SYNC must be a standard step, not another manual
habit. Add this clause to the **project's `AGENTS.md`** (or the wiki-root
`AGENTS.md` if the wiki covers the whole project):

```markdown
## Wiki sync (llm-wiki-manager)

Dopo ogni implementazione o merge che cambia comportamento, API, configurazione,
tech stack o decisioni tecniche, esegui l'operazione SYNC della skill
`llm-wiki-manager`: raccogli i cambi con `wiki_sync.py`, aggiorna le pagine wiki
toccate (solo conoscenza durabile), rigenera l'index, aggiorna il marker e il log.
```

The agent then runs SYNC as the closing step of the work that made the change.

---

## Step 1 — Gather the change (deterministic)

```bash
python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_sync.py <wiki-root>
```

The script reports, since the last marker (`<wiki-root>/wiki/.sync-marker`):
commits and changed file paths, **excluding** `raw/`, `wiki/`, `.walden/`, `docs/`
and `.github/` — what's left is the implementation signal. Flags:

> **Gitignore the marker.** `wiki/.sync-marker` changes on every sync and should
> not be committed to the project repo (add `wiki/.sync-marker` to the repo's
> `.gitignore`), otherwise each sync produces a pointless git change.

| Flag | Effect |
|---|---|
| `--since <ref\|date\|N>` | override the marker (git ref, ISO date, or N = `HEAD~N`) |
| `--write-marker` | record HEAD as the last processed commit |
| `--json` | machine-readable output |
| `--max-commits N` | cap the commit list |

**First run / no marker:** the script defaults to `HEAD~5` and warns. The right
first move is to establish a baseline: run with `--write-marker` and **stop** —
no page edits yet. Subsequent runs then report only genuine implementation
changes.

**No git repository / no commits:** the script says so and exits 1. Do not fake a
diff — fall back to manual INGEST or just say SYNC is not applicable here.

---

## Step 2 — Map changed files → wiki pages

Read the changed paths and infer which entity/concept pages are affected (match
basenames, service/component names, and domain nouns against page slugs, titles,
tags, descriptions). If unsure, confirm candidates with a quick search:

```bash
python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_search.py <wiki-root> <terms...>
```

Read only the 1–3 pages you judge affected. Do not open the whole wiki.

---

## Step 3 — Update durable knowledge only

For each affected page update the sections that the change genuinely alters:
`## Tech Stack` / `## Key Properties`, `## Key Decisions`, `## Relationships`,
API/config entries that matter, patterns. Rules:

- **Contradictions:** if the change contradicts an existing claim, update the
  claim and note it (contradiction notice or a `sync` indication in the body).
- **New knowledge:** a component/service/pattern that is new to the wiki and
  durably relevant gets a stub page (promotion rule: it appears in a real change
  AND adds lasting value). Extend cross-links.
- **Skip transient detail:** command-line noise, one-off fixes, timing/version
  churn. When in doubt, leave it out.
- **No change needed:** if nothing durable changed, do not force edits.

---

## Step 4 — The confirmed-write gate

- Pages **without** `verified:` → update directly, then bump `updated` (and
  `generated` under the actor convention in `references/okf.md`).
- Pages with `verified: human:` → **propose the exact diff and wait for explicit
  confirmation**. Never overwrite human-reviewed content silently. If the change
  touches both kinds, do the unverified ones, then present the verified diff.
- If the topic exists only as raw source / not in the wiki, apply the normal
  INGEST rules instead.

---

## Step 5 — Bookkeeping (always, via scripts)

```bash
# 1. overview, if the knowledge map changed
# 2. regenerated catalog
python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_index.py <wiki-root> --write

# 3. record HEAD as the new baseline LAST (after the pages are written)
python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_sync.py <wiki-root> --write-marker

# 4. history entry
python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_log.py <wiki-root> append \
  --op sync --title "<topic>" --note "<what changed / none-durable>"
```

Order matters: the marker is updated **after** the pages land, so a crash between
edits and marker leaves the change visible on the next run. Even a no-op sync
still advances the marker and logs `"no durable changes"`.

---

## Step 6 — Report

List: pages created / updated / skipped (and why), the marker SHA, the log entry.
Optionally run LINT (`references/lint.md`) to catch dangling links or orphans
introduced by the edits.

**Expected output:** affected pages updated (durable changes only) + verified
diffs awaiting confirmation + regenerated index + advanced marker + one `sync`
log entry.