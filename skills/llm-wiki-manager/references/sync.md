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

## Step 2 — Map changed files → wiki pages AND cross-check content

Read the changed paths (the non-wiki signal the script now isolates) and infer
which entity/concept pages are affected (match basenames, service/component
names, and domain nouns against page slugs, titles, tags, descriptions). If
unsure, confirm candidates with a quick search:

```bash
python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_search.py <wiki-root> <terms...>
```

Read only the 1–3 pages you judge affected. Do not open the whole wiki.

**Mandatory cross-check — this is the point of SYNC.** For each changed
implementation/config file, do not just map it to a page: open BOTH the file's
current content AND the wiki page, and compare the durable claims (versions,
tags, paths, flags, topology) against the actual values on disk. A git diff
only shows *what moved in this window* — it cannot tell you whether the wiki
matches the code *in that same commit*, because the wiki edit and the code edit
may have landed together and contradict each other (a real failure mode seen in
practice: a commit bumped a tag to `X` in `values.yaml` while the very wiki
page it touched still claimed "resta `X-1`, non ancora allineati").

Anti-patterns for the cross-check:
- **Never trust a log.md entry as proof of alignment.** Logs record operations
  ("Aggiornato values.yaml"), not page state. Check the page, not the log.
- **Never infer "already documented" from the presence of a value on the page.**
  `26.7.3` on keycloak.md while a sibling line says "values.yaml resta
  `26.6.2-1`" is a contradiction, not a confirmation. Search for the *negative
  claims* the wiki makes about the file ("resta", "non ancora allineati", "per
  costruzione non usato", "da allineare") and verify each against disk.
- **Version/tag bumps are NOT harmless skippable churn when they contradict a
  durable wiki claim** (e.g. a CVE fix) — see Step 3.
- Keep the cross-check contents honest: void a "no durable change" conclusion
  only after opening the actual files, never before.

---

## Step 3 — Update durable knowledge only

For each affected page update the sections that the change genuinely alters:
`## Tech Stack` / `## Key Properties`, `## Key Decisions`, `## Relationships`,
API/config entries that matter, patterns. Rules:

- **Contradictions:** if the change contradicts an existing claim, update the
  claim and note it (contradiction notice or a `sync` indication in the body).
  This is the most common real gap: a commit often edits the wiki page AND the
  code in the same change, so the diff *looks* already-synced — only the Step 2
  content cross-check surfaces the contradiction.
  This is the number-one capture: a commit frequently edits the wiki page AND
  the code in the same change, so the diff alone hides the contradiction —
  only the Step 2 content cross-check surfaces it.
- **New knowledge:** a component/service/pattern that is new to the wiki and
  durably relevant gets a stub page (promotion rule: it appears in a real change
  AND adds lasting value). Extend cross-links.
- **Skip transient detail:** command-line noise, one-off fixes, timing/version
  churn. **Exception:** a version/tag bump is durable when it *contradicts* a
  wiki claim (e.g. a CVE fix the wiki still marks as "non ancora allineati") —
  that is a Contradiction, update the claim. Skip only pure churn with no wiki
  claim to reconcile.
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