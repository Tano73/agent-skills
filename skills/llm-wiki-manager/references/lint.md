# LINT — health-checking the wiki

Read this file when the user asks to audit the wiki ("lint", "controlla",
"audit", "health check", "verifica il wiki").

The mechanical checks are scripts — faster, cheaper, and more honest than eyeballing
the tree. Your job is to run them, merge the semantic checks only a human-reasoning
agent can see, present one structured report, and ask which items to fix.

---

## Execution modes

- **Veloce (default)**: everything below except the DocMind-aware categories.
  Zero DocMind calls.
- **Completo (on-demand)**: additionally run the DocMind-aware checks from
  `references/docmind.md`. Triggers: *"lint completo"*, *"lint con docmind"*,
  *"audit"*. Estimate the number of DocMind calls and ask confirmation first.

---

## Mechanical checks (scripts — always)

```bash
SKILL_SCRIPTS=$HOME/.agents/skills/llm-wiki-manager/scripts

# structural/OKF health
python3 $SKILL_SCRIPTS/wiki_lint.py "<wiki-root>"
# index up-to-date check (no writes)
python3 $SKILL_SCRIPTS/wiki_index.py "<wiki-root>" --check
```

`wiki_lint.py` covers: dangling `sources:` / `## Sources` references, broken
relative links, missing `resource`/`source_file` provenance, missing required OKF
`type`, invalid `status`, passed `stale_after`, pages absent from `index.md`,
index drift, orphan pages, pages with no outbound links, and the
`category`/`type` + `resource`/`source_file` conflict aliases. Use `--json` when
you need to process findings programmatically, `--strict` to also fail on low/info
findings.

If `wiki_index.py --check` reports drift, run `--write` to regenerate — do not hand
repair the index.

---

## Semantic checks (agent — the scripts cannot see these)

Walk the pages for issues the scripts cannot prove and merge them into the report:

| Severity | Category | What it catches |
|---|---|---|
| 🔴 | Contradictions | `⚠️ Contradiction` notices not yet resolved |
| 🟠 | Missing Pages | terms mentioned in 2+ pages lacking their own page |
| 🟡 | Stale Content | pages likely outdated (or `stale_after` passed — script) |
| 🟡 | Missing Cross-References | obvious links not yet made |
| 🟢 | Data Gaps | thinly covered areas |
| 🟢 | Suggested Questions | questions the wiki can almost answer |
| 🟡 | Stale Schema | `AGENTS.md` conventions vs actual practice (Karpathy's schema drift) |

---

## Report template

```markdown
# Wiki Lint Report — YYYY-MM-DD

## 🔴 Contradictions
## 🔴 Dangling Source References   ← wiki_lint.py
## 🟠 Missing Provenance           ← wiki_lint.py
## 🟠 Orphan Pages                 ← wiki_lint.py
## 🟠 Missing Pages
## 🟡 Stale Content
## 🟡 Missing Cross-References
## 🟡 Missing Required OKF Field   ← wiki_lint.py
## 🟢 Data Gaps
## 🟢 Suggested Questions
## 🟡 Stale Schema                ← AGENTS.md vs practice
```

(Add the DocMind-aware categories in **completo** mode — see `references/docmind.md`.)

---

## Fix loop

Ask which items to fix; apply in priority order (🔴 before 🟠 before 🟡). After
any fix session, regenerate index and log the lint:

```bash
python3 $SKILL_SCRIPTS/wiki_index.py "<wiki-root>" --write
python3 $SKILL_SCRIPTS/wiki_log.py "<wiki-root>" append \
  --op lint --title "<N> issues addressed" --note "<summary>"
```

If nothing needed fixing, log that too (`"0 issues"`). Cycle-complete: lint is
iteratively cheap because the mechanical half never re-reads what the agent
already knows.