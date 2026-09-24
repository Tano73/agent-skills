# OKF v0.2 Contract — the wiki's structural standard

Read this file when you create or edit wiki pages, regenerate `wiki/index.md`,
or need to configure a new wiki. It defines the storage contract: the wiki root
is an **OKF v0.2 bundle** (Open Knowledge Format — Google), and Karpathy's LLM-wiki
pattern is how we use that bundle. Every deterministic helper (`wiki_index.py`,
`wiki_lint.py`, `wiki_log.py`) assumes exactly this contract; follow it to the
letter so the scripts and the agent never disagree.

The normative reference is the OKF v0.2 spec doc (KnowledgeBase project, uniqueName
`spec`). This file is the same contract tuned to the wiki's page taxonomy.

---

## Bundle structure

The wiki root is the bundle. Only two filenames are reserved anywhere in the tree:

| Filename | Meaning | Maintained by |
| --- | --- | --- |
| `index.md` | progressive-disclosure catalog | `wiki_index.py` (never by hand) |
| `log.md` | chronological update history | `wiki_log.py` (never by hand) |

The `AGENTS.md` at the wiki root is the **schema layer** of the pattern: it records
this skill's conventions adapted to the wiki's domain (page taxonomy, naming rules,
DocMind binding). It co-evolves with the wiki — propose a concrete update when a
convention stops fitting, and confirm with the user.

```
<wiki-root>/           = OKF bundle
├── AGENTS.md          schema (Karpathy's "schema" layer — the operating manual)
├── raw/               source documents, IMMUTABLE  ("raw sources" layer)
│   └── assets/
└── wiki/              agent-written knowledge       ("wiki" layer)
    ├── index.md       reserved: catalog (script-generated)
    ├── log.md         reserved: history (script-maintained)
    ├── overview.md    concept: evolving synthesis
    ├── entities/      concepts of type `entity`
    ├── concepts/      concepts of type `concept`
    └── sources/       concepts of type `source` (one per ingested document)
```

Folders classify pages. A page's folder and its `type` must agree (`entities/` →
`type: entity`, `concepts/` → `type: concept`, `sources/` → `type: source`,
`wiki/overview.md` → `type: overview`).

---

## Frontmatter contract

Every `.md` page is an OKF concept document: a YAML frontmatter block plus a
markdown body. **`type` is the only REQUIRED field** — a page carrying just `type`
is fully conformant (OKF §4.1, §11). The rest are recommended or deliberate-optional.

### Recommended (write on every page)

```yaml
---
type: entity | concept | source | overview
title: "Display Name"            # readonly fallback: derived from the filename
description: "One-line summary"  # used by index.md generation and search snippets
tags: [tag1, tag2]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: stable                   # draft | stable | deprecated (absent => stable)
---
```

For **source pages** add the provenance field that binds the page to its asset:

```yaml
resource: raw/<filename>         # canonical URI of the underlying raw source
```

### Deliberate-optional families (OKF §5, §10 — use only where they add value)

These are documented in the OKF spec and recognized by the scripts; do not pad
every page with them.

- **Provenance — `sources`**: a list of slugs whose wiki source pages the concept
  derives from (`sources: [kubernetes-operators]`). The mappied lineage edge is
  also expressed with normal markdown links under `## Sources` (OKF §5.1 prefers
  links for bundle-internal derivation). The `sources:` list is a machine-checkable
  shortcut for the same edge. Optional per-page.
- **Trust — `generated` / `verified`**: record who wrote and who confirmed the
  content. Use the actor convention below. `verified` by a `human:` actor marks the
  content as the OKF **human-reviewed** trust tier; write it after a human approves
  an INGEST discussion, saves a QUERY answer, or confirms a PROMOTE preview.

  ```yaml
  generated: { by: agent/llm-wiki-manager, at: 2026-09-24T10:00:00Z }
  verified:  { by: human:danilo, at: 2026-09-24T12:00:00Z }   # or a list of events
  ```
- **Lifecycle — `stale_after`**: an ISO instant after which the content should be
  re-checked. `wiki_lint.py` honors it and flags pages past it. Absent ⇒ content is
  expected fresh.
- **DocMind extensions** (only for pages bound to DocMind): `docmind_mirror`
  (PROMOTE), `docmind_spec` (SPEC-COMPOUND snapshots). Producer-defined keys are
  legal under OKF and must be preserved on round-trip.

### Legacy aliases (OKF v0.1 era) — recognized on read, never written

| Current | Legacy | Behavior |
| --- | --- | --- |
| `type` | `category` | both accepted; `wiki_lint.py` flags a `field_conflict` if both are present with different values |
| `resource` | `source_file` | both accepted as provenance; differing values are flagged |

Wikis created before the alignment keep working with no migration (NFR1). Never
write the legacy names for new content.

### Actor convention (OKF §7)

- Agents and tools: `agent/llm-wiki-manager` (this skill).
- People: `human:<id>`.
- Automated processes: `process:<id>`.

Consumers classify trust by the `human:` prefix — always use it for human-confirmed
content.

---

## Trust and lifecycle semantics

- **Trust tiers** (derived from `verified`, OKF §5.3): no `verified` ⇒ *unverified*;
  verified only by `process:`/`agent:` ⇒ *machine-confirmed*; verified by `human:`
  ⇒ *human-reviewed*. Absence is meaningful but never rejected.
- **`generated.at` vs `verified.at`** are independent: a page can change without
  re-confirmation, and be re-confirmed without changing. Bump `generated.at` on any
  meaningful edit; leave `verified` unless a human re-checks against sources.

---

## Cross-linking (OKF §6)

- Use **relative markdown links only**: `[Keycloak](../entities/keycloak.md)`.
- Never Obsidian wikilinks `[[foo]]` and never absolute filesystem paths.
- A link from page A to page B asserts a relationship; the kind is conveyed by
  surrounding prose, not the link.
- Broken links are tolerated structurally (OKF §6.1): a target that does not exist
  yet represents not-yet-written knowledge. `wiki_lint.py` still reports them so
  the agent can decide whether the gap is intentional.

---

## Page templates

### Entity page — `wiki/entities/<slug>.md`

```markdown
---
type: entity
title: "Entity Name"
description: "One-line definition"
tags: [tag1, tag2]
status: stable
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Entity Name

Brief definition and purpose.

## Tech Stack / Key Properties

## Relationships

## Key Decisions

## Problems & Solutions

## Sources
- [Source Page](../sources/<source-slug>.md)
```

### Concept page — `wiki/concepts/<slug>.md`

```markdown
---
type: concept
title: "Concept Name"
description: "One-line definition"
tags: [tag1, tag2]
status: stable
created: YYYY-MM-DD
updated: YYYY-MM-DD
---

# Concept Name

Definition and relevance.

## Where Applied

## Trade-offs & Considerations

## Sources & Examples
- [Source Page](../sources/<source-slug>.md)
```

### Source page — `wiki/sources/<source-slug>.md`

`<source-slug>` matches the raw filename (same slug, minus extension).

```markdown
---
type: source
title: "Source Title"
description: "One-line summary"
resource: raw/<filename>
tags: [tag1, tag2]
status: stable
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

---

## Index format (`wiki/index.md`)

Generated by `wiki_index.py` from page frontmatter and body `## Sources` links.
Do not edit it by hand — re-run the script after any page change.

```markdown
# Index

_Generated by `wiki_index.py`. Do not edit by hand — re-run the script after any change to wiki pages._

## Overview
* [Overview](overview.md) — evolving synthesis of the wiki's knowledge

## Entities (N)
| Page | Description | Sources | Updated |
|---|---|---|---|
| [Keycloak](entities/keycloak.md) | Identity and access management server. | 2 | 2026-09-21 |

## Concepts (N) ...
## Sources (N) ...
```

The **Sources** column counts the source pages linked from the page's `## Sources`
body section — a deterministic signal, not an author-maintained number.

---

## Log format (`wiki/log.md`)

Maintained by `wiki_log.py`. OKF §9 format: date-grouped headings, newest
first, entries as bullets headed by a bold action word.

```markdown
# Update Log

## 2026-09-24
* **ingest**: Kubernetes Operators — Extracted the CRD / controller-loop pattern
* **query**: OIDC vs SAML — Comparison table saved to wiki/concepts/oidc-vs-saml.md

## 2026-09-20
* **setup**: Knowledge wiki — Initial structure
```

- Date headings MUST be ISO `YYYY-MM-DD` (OKF §9).
- Action words: `setup`, `ingest`, `query`, `lint`, `spec-created`, `spec-done`,
  `promote`.
- The agent states what happened; `wiki_log.py` owns the ordering. Recent entries
  are readable via `wiki_log.py <root> tail -n 5` (nearest equivalent of
  Karpathy's `grep '^## \[' log.md | tail -5` tip).

---

## Conformance summary (OKF §11, tuned)

A wiki is conformant when: (1) every non-reserved page has parseable frontmatter;
(2) every page carries a non-empty `type`; (3) the reserved `index.md`/`log.md`
match the formats above. Everything else — missing recommended fields, unknown
`type` values, unknown extra keys, broken links, missing index files — must never
cause a consumer to reject the bundle. `wiki_lint.py` reports these as findings
(severity varies) so the agent can choose to fix or consciously accept them.