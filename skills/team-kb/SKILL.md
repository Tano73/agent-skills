---
name: team-kb
description: Answer questions about the team's knowledge base using DocMind. Use this skill whenever someone asks about team documentation, project specs, architecture decisions, technical requirements, API specs, or any content stored in the team knowledge base. Trigger on questions like "what does the spec say about X?", "find information about Y in our docs", "how does Z work according to our documentation", "cerca nella KB", "cosa dice la documentazione su...", or any query that should be answered from internal team documents rather than general knowledge. Always use this skill when the question is about team-specific or project-specific content — don't try to answer from memory.
---

# Team Knowledge Base

Answer questions by searching the team knowledge base in DocMind, then synthesizing a response that is firmly anchored to the retrieved text.

## How to answer a question

### 1. Identify the search strategy

Think about what the user is asking:
- Is the question about a specific project? Check `listProjects` to find the right project name if unclear.
- Is it a conceptual question? Use `mode: "hybrid"` (combines semantic + keyword).
- Does it contain exact technical terms, method names, or IDs? Use `mode: "fulltext"`.
- When in doubt, use `mode: "hybrid"` — it has automatic fallback and works best for most queries.

### 2. Search DocMind

Call `searchFlavorChunks` with a focused query. Key parameters:
- `project`: the project name (required). If the user doesn't specify a project, try the most relevant one or search across a couple of candidate projects in parallel.
- `query`: rephrase the user's question as a clear search query; expand abbreviations and include synonyms.
- `mode`: `"hybrid"` as default, `"fulltext"` for exact terms.
- `adjacentChunks`: set to `1` or `2` to get surrounding context when a chunk alone is not enough to form a complete answer.
- `limit`: 5–8 chunks is usually enough; increase to 10 if the topic spans multiple documents.

If the first search returns 0 results or poor results:
- Try rephrasing with different keywords.
- Try `mode: "semantic"` if `"fulltext"` returned nothing.
- Try a sibling project if the first one had no relevant content.

### 3. Build the answer

Synthesize the response from the retrieved chunks:
- **Ground every claim** in the retrieved text. Don't add information that isn't in the search results.
- **Cite the source** inline for each key point, using the format:  
  `(Source: <displayName or uniqueName>, line <N>)` for a single line, or  
  `(Source: <displayName or uniqueName>, lines <N>–<M>)` for a range — both forms are correct
- If multiple chunks from different documents support the same point, list all sources.
- If a chunk is only partially relevant, say so — don't overstate what the document covers.
- If the search returns nothing useful, be honest: tell the user you didn't find relevant content in the knowledge base and suggest they check the project or refine the query.

### 4. Format the response

Structure answers to be scannable:
- For factual/lookup questions: a direct answer followed by the supporting quote and citation.
- For broader conceptual questions: use headings or bullet points, each backed by a citation.
- Always end with a "Sources" section listing the unique document names used.

## Example

**User:** How does authentication work in the ETG project?

**Steps:**
1. Search `project: "ETG"`, `query: "authentication access management"`, `mode: "hybrid"`, `limit: 6`.
2. If weak results, also try `project: "Keycloak"` since auth might live there.
3. Synthesize answer from the returned chunks with inline citations.

**Response format:**
```
Authentication in ETG uses Keycloak-based OAuth2 flows with role-based access control...

> "Il sistema adotta un meccanismo di autenticazione basato su token JWT emessi da Keycloak..."
(Source: SF-GROOT-ETG-V1_7-cap04, lines 12–18)

**Sources:**
- SF-GROOT-ETG-V1_7-cap04 — "04 - 4 Requisiti di sviluppo – Gestione Accessi"
```

## Available projects

The following projects are available in DocMind (use `listProjects` if you need a fresh list):

| Project | Description |
|---------|-------------|
| Agentic | Agentic/AI-related docs (33 docs) |
| AMR | AMR project (2 docs) |
| Apache-Airflow | Airflow (15 docs) |
| demo | Demo content (1 doc) |
| Engingeering | Engineering docs (97 docs) |
| ETG | ETG project specs (45 docs) |
| FPA | FPA (1 doc) |
| gatesender | Gatesender (22 docs) |
| Karpathy-LLM-Wiki | LLM Wiki (1 doc) |
| Keycloak | Keycloak docs (20 docs) |
| NIPAM | NIPAM project (14 docs) |
| NPRESS | NPRESS (17 docs) |
| OBG-BATCH-FILEGW | OBG Batch/File Gateway (67 docs) |
| OBG-GUP_HXX | OBG GUP HXX (2 docs) |
| RETELIT | Retelit (4 docs) |
| VendorsHub | VendorsHub (23 docs) |

## Tips

- **Be precise about project scoping.** A vague search across the wrong project gives noise. If unsure, ask the user which project they mean.
- **Prefer shorter, focused queries** over long sentences — `searchFlavorChunks` works better with 3–8 keywords than with a full question.
- **Use `adjacentChunks`** when a chunk is cut off mid-sentence or clearly needs surrounding context to make sense.
- **Never invent content.** If you can't find it in the KB, say so clearly.
