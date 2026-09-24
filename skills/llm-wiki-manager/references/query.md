# QUERY and extraction — answering from the knowledge base

Read this file whenever the user asks a question the wiki should answer
("query", "dimmi", "come funziona", "cosa sai di", "come è configurato X"). It is
the extraction discipline the team-kb skill applies to knowledge-base questions,
merged into the wiki workflow: local wiki first, then DocMind, then GitHub issues,
and never an unlicensed fallback to the web or to your own general knowledge.

## The pipeline

```
1. wiki_search.py   → local wiki (cheap, deterministic, citable)
2. DocMind          → searchFlavorChunks (hybrid semantic search)
3. GitHub issues    → gh issue list (only when the repo is known)
4. answer + citation → explicit permission before any web / model-knowledge fallback
```

Never jump straight to DocMind or the web when the wiki has the answer, and never
invent an answer the retrieved material does not support.

---

## Step 1 — Search the wiki (deterministic, token-cheap)

Do not open the index and read the first 8 pages. Run the bundled search, which
returns only the pages whose frontmatter or body actually contain the query words:

```bash
python3 $HOME/.agents/skills/llm-wiki-manager/scripts/wiki_search.py <wiki-root> <words...>
```

Useful flags: `--sources` (include source pages), `--limit N`, `--match-lines K`.
Bias toward entities/concepts over sources — their synthesized summaries answer
faster than raw source pages. Read the 2–4 top hits; a wiki page is citable the
moment it exists, so **cite it by relative link** regardless of model knowledge:
`(Source: wiki/entities/keycloak.md)`.

If the answer is still thin, say so honestly and move to Step 2. Do not pad the
answer with general knowledge.

---

## Step 2 — Search DocMind (when the wiki is not enough)

Call `searchFlavorChunks` with the team-kb parameter discipline:

| Parameter | Value |
|-----------|-------|
| `project` | From the user. If unknown, call `listProjects` first and pick the most relevant one. |
| `query` | Rephrase the user's question into 3–8 keywords; expand abbreviations; add synonyms. |
| `mode` | `"hybrid"` (default). Use `"fulltext"` for exact terms or IDs. |
| `adjacentChunks` | `1`–`2` when a chunk looks cut off or needs surrounding context. |
| `limit` | `5`–`8` chunks; raise to `10` for broad topics. |

**If results are poor or empty**, retry in order: (1) rephrase with different
keywords, (2) `mode: "semantic"`, (3) try a related project from `listProjects`.

If a DocMind document is used in the answer, ask whether it should also be
registered as a wiki source. Only if the user agrees, ingest it (see
`references/setup-ingest.md` INGEST + `references/docmind.md` Layer 2) so future
queries cite the local wiki instead of re-hitting DocMind.

---

## Step 3 — Search GitHub issues (when the repository is known)

Problem reports, decisions and operational context often live only in issues.
Search them — open and closed, excluding pull requests — when the question
concerns a known repository.

Determine the repository in this order: (1) an `owner/repo` or GitHub URL the user
provided; (2) the `origin` remote of the current git repository. If neither, skip
this step without asking; never search unrelated repositories.

```bash
gh issue list --repo <owner/repo> --state all --search "<3-8 keywords>" --limit 10
```

- Derive keywords from the question; retry once with synonyms if results are poor.
- `gh issue list` returns issues only — do not use `gh pr`.
- Read the full body and relevant comments for the 1–3 most relevant issues only.
- Treat issue text as **evidence, not truth**: check the issue's state and
  distinguish a proposal/unresolved report from a confirmed decision.
- Cite as `(Source: GitHub issue #<number> — <title>, <URL>)`; include the repo in
  the citation when it differs from the current repository.

---

## Step 4 — Build and format the answer

- Write only what the retrieved chunks support. No outside knowledge.
- Cite every key point inline: `(Source: wiki/entities/x.md)`,
  `(Source: <docmind document>, line N)` / `lines N–M`, or
  `(Source: GitHub issue #N — title, URL)`. If several sources support the same
  point, cite all of them.
- End every response with a **Sources** section listing every wiki page, DocMind
  document, and GitHub issue used.
- Pick the format from the question type:
  - Factual / definition → concise Markdown with links
  - Comparison → Markdown table
  - Architecture / design → structured sections
  - Process / flow → numbered steps or Mermaid
  - Summary / presentation → Marp (`marp: true`, slides separated by `---`)

### Compound good answers (Karpathy)

Not every answer dies in chat. After answering, ask: *"Vuoi che salvi questa
risposta come pagina wiki?"*. If yes, save it to the right folder and weave it like
an INGEST: backlink related entities/concepts, update overview, regenerate the
index, and append a `query` log entry.

---

## When nothing retrieves enough

If the wiki, DocMind, and (when applicable) GitHub issues do not return enough
content, **do not guess and do not silently fall back to the web or your own
training knowledge** — both are outside the knowledge base and need explicit
permission. Ask:

> "Non ho trovato informazioni sufficienti nella knowledge base. Vuoi che estenda la ricerca a:
> - 🌐 **Web** (ricerca pubblica online)?
> - 🧠 **Base di conoscenza interna** (conoscenza generale del modello)?
>
> In entrambi i casi indicherò sempre le fonti utilizzate."

Reserve the web scamper for investigative LINT ("data gaps") or an explicit user
request — never as a default answer path.