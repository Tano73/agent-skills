---
name: team-kb
description: Answer questions about the team's knowledge base using DocMind. Use this skill whenever someone asks about team documentation, project specs, architecture decisions, technical requirements, API specs, or any content stored in the team knowledge base. Trigger on questions like "what does the spec say about X?", "find information about Y in our docs", "how does Z work according to our documentation", "cerca nella KB", "cosa dice la documentazione su...", or any query that should be answered from internal team documents rather than general knowledge. Always use this skill when the question is about team-specific or project-specific content — don't try to answer from memory.
---

# Team Knowledge Base

Answer questions by searching the team knowledge base. **Never invent information** — every claim must come from a retrieved document.

## Step 1 — Check the local LLM wiki (if available)

If the `llm-wiki-manager` skill is available **and** a `wiki/` directory exists in the workspace, query it first. It may already contain a synthesized answer.

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

## Step 3 — Build and format the answer

- Write only what the retrieved chunks support. Do not add outside knowledge.
- Cite every key point inline: `(Source: <document name>, line N)` or `lines N–M`.
- If chunks from multiple documents support the same point, cite all of them.
- For **factual questions**: direct answer → supporting quote → citation.
- For **broad questions**: use headings or bullets, each backed by a citation.
- End every response with a **Sources** section listing all document names used.

## When information is insufficient

If no search attempt returns enough content, **do not guess**. Ask the user:

> "Non ho trovato informazioni sufficienti nella knowledge base. Vuoi che estenda la ricerca a:
> - 🌐 **Web** (ricerca pubblica online)?
> - 🧠 **Base di conoscenza interna** (conoscenza generale del modello)?
>
> In entrambi i casi indicherò sempre le fonti utilizzate."
