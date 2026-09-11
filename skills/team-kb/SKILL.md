---
name: team-kb
description: Answer questions about the team's knowledge base using DocMind. Use this skill whenever someone asks about team documentation, project specs, architecture decisions, technical requirements, API specs, or any content stored in the team knowledge base. Trigger on questions like "what does the spec say about X?", "find information about Y in our docs", "how does Z work according to our documentation", "cerca nella KB", "cosa dice la documentazione su...", or any query that should be answered from internal team documents rather than general knowledge. Always use this skill when the question is about team-specific or project-specific content — don't try to answer from memory.
---

# Team Knowledge Base

Answer questions by searching the team knowledge base. **Never invent information** — every claim must come from a retrieved document.

## Step 1 — Check the local LLM wiki (if available)

The wiki isn't necessarily at `./wiki/` — it can live under a different name or a different directory, and its location is only decided at SETUP time by `llm-wiki-manager`. Before assuming there's no local wiki, look for its root using the same locations that skill uses, in order:

1. Current working directory — a wiki root has `wiki/index.md` (preferred) or both `wiki/` and `raw/`; it may sit directly in the cwd or under an `AGENTS.md`-adjacent subfolder.
2. Parent directories, up to 3 levels up.
3. Common conventional paths: `./knowledge/`, `./kb/`, `./wiki/`, `~/kb/`, `~/notes/`, `~/Documents/kb/`.
4. Any path the user explicitly names in the conversation.

If a wiki root is found, read `wiki/index.md` (and `wiki/overview.md` if useful) and query it first — it may already contain a synthesized, citable answer. Treat it as a first-class source: cite its pages the same way you'd cite a DocMind document, e.g. `(Source: wiki/entities/order-service.md)`.

If no wiki root is found anywhere, don't stop to ask about it — just proceed to Step 2. Only mention the absence if it becomes relevant later (e.g. when suggesting where to save a synthesized answer).

## Step 2 — Search DocMind

Call `searchFlavorChunks` with these parameters:

| Parameter | Value |
|-----------|-------|
| `project` | Project name from the user. If unknown, call `listProjects` first and pick the most relevant one. |
| `query` | Rephrase the user's question in 3–8 keywords; expand abbreviations; add synonyms. |
| `mode` | `"hybrid"` (default). Use `"fulltext"` for exact terms or IDs. |
| `adjacentChunks` | `1` or `2` when a chunk looks cut off or needs surrounding context. |
| `limit` | `5`–`8` chunks; raise to `10` for broad topics. |

**If results are poor or empty**, retry in order:
1. Rephrase the query with different keywords.
2. Switch to `mode: "semantic"`.
3. Try a related project with `listProjects`.

## Step 3 — Search GitHub Issues (when the repository is known)

If the question concerns a GitHub project and its repository is known, search its **open and closed issues**, excluding pull requests. Issues can capture decisions, known problems, requirements, and operational context that have not yet reached the wiki or DocMind.

Determine the repository in this order:

1. A `owner/repo` identifier or GitHub URL explicitly provided by the user.
2. The `origin` remote of the current Git repository.

If no repository can be determined, skip this step without asking. Do not search unrelated repositories.

Use the GitHub CLI to search narrowly before opening full issue bodies:

```bash
gh issue list --repo <owner/repo> --state all --search "<keywords>" --limit 10
```

- Use 3–8 focused keywords derived from the question; retry once with synonyms if results are poor.
- Exclude pull requests. `gh issue list` returns issues only; do not use `gh pr` as a substitute.
- Read the complete body and relevant comments only for the 1–3 most relevant issues.
- Treat issue text as evidence, not as authoritative truth: identify the issue's status and distinguish a proposal or unresolved report from a confirmed decision.
- Cite each issue as `(Source: GitHub issue #<number> — <title>, <URL>)`. Include the repository in the citation when it differs from the current repository.

## Step 4 — Build and format the answer

- Write only what the retrieved chunks support. Do not add outside knowledge.
- Cite every key point inline: `(Source: <document name>, line N)` or `lines N–M` for DocMind chunks, or `(Source: <relative wiki path>)` for wiki pages.
- If chunks from multiple documents support the same point, cite all of them.
- For **factual questions**: direct answer → supporting quote → citation.
- For **broad questions**: use headings or bullets, each backed by a citation.
- End every response with a **Sources** section listing every wiki page, DocMind document, and GitHub issue used.

## When information is insufficient

If the local wiki (Step 1), DocMind (Step 2), and GitHub Issues when applicable (Step 3) do not return enough content, **do not guess and do not silently fall back to the web or your own training knowledge** — both are outside the team knowledge base and need explicit user permission. Ask the user:

> "Non ho trovato informazioni sufficienti nella knowledge base. Vuoi che estenda la ricerca a:
> - 🌐 **Web** (ricerca pubblica online)?
> - 🧠 **Base di conoscenza interna** (conoscenza generale del modello)?
>
> In entrambi i casi indicherò sempre le fonti utilizzate."
