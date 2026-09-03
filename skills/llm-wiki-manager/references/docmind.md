# DocMind Integration

Optional enhancement for `llm-wiki-manager`. If DocMind MCP tools are **not** available, operate in local-only mode with no degradation — skip this file entirely.

Read this file when the user asks for SPEC-DRAFT, SPEC-COMPOUND, PROMOTE, DocMind ingest/search, or a full ("completo") LINT that includes DocMind-aware checks.

---

## Layer 1 — Ingest from DocMind

INGEST also accepts:
- A DocMind `uniqueName` → `getFlavorByName(uniqueName)` to fetch the document
- A search query on a DocMind project → `searchFlavorChunks(project, query, mode=hybrid)`

When ingesting from DocMind, derive a candidate `raw/<slug>.md` filename from the DocMind `uniqueName` (converted to kebab-case), then apply the normal versioning check before writing anything. Proceed using the resolved raw file (for example `raw/<slug>.md` if reused or created, or `raw/<slug>-v2.md` if versioned) and set `source_file` in the source page frontmatter to that exact path.

During **SETUP step 5b** (DocMind pre-scan): search for documents related to the seed entities/concepts. For each relevant document, perform the mechanical ingest pre-pass only (fetch, versioning check, create `wiki/sources/<slug>.md`). **Do not** run INGEST's user discussion step during SETUP. Skip 5b entirely if DocMind is unavailable.

---

## Layer 2 — Query with semantic search

In enhanced mode, QUERY uses `searchFlavorChunks(project, question, mode=hybrid)` to identify relevant pages, in addition to or instead of reading `wiki/index.md`.

If a DocMind document from **any** project is fetched and used in the answer, ask the user whether it should also be registered as a source in the wiki. Only if the user agrees, treat it as an ingested source: apply the versioning check, create `wiki/sources/<source-slug>.md`, set `source_file` to that exact raw path, and add it to `wiki/index.md`.

---

## Layer 3 — Mirror to DocMind (advanced)

Wiki pages can be synced to DocMind as flavors using `uploadDocument` or `updateDocument`. The local filesystem remains the primary store; DocMind is a remote mirror for cross-wiki search and sharing. Prefer the PROMOTE workflow (Layer 5) for intentional publication.

---

## Optional section: `## Related Specs` (entity/concept)

Entity and concept pages may include an optional `## Related Specs` section listing DocMind specs that touch that element. This is the "work in progress / done" dimension of the wiki; update it on every `spec_transition`.

**Format of each entry:**

```markdown
- [<uniqueName>](docmind://specs/<uniqueName>) — <displayName> — `<SPEC_STATUS>`
```

**Example:**

```markdown
## Related Specs
- [pw-saml-partner-x](docmind://specs/pw-saml-partner-x) — SAML SP-Initiated SSO con Partner X — `SPEC_DONE`
- [pw-mfa-rollout](docmind://specs/pw-mfa-rollout) — MFA per utenti interni — `SPEC_REVIEW`
```

**Rules:**

- Only entity and concept pages (never source).
- Absent section = no related specs.
- `SPEC_DONE` is sticky: do not remove the entry; it is historical trail.
- Update status on every `spec_transition` that touches a cited spec.

---

## Variant: Spec source page (`wiki/sources/spec-<uniqueName>.md`)

When a DocMind spec reaches `SPEC_DONE`, snapshot its final content to `raw/spec-<uniqueName>.md` (immutable) and create the matching source page:

```markdown
---
title: "Spec: <displayName>"
category: source
tags: [spec, <spec.tags...>]
source_file: raw/spec-<uniqueName>.md
created: YYYY-MM-DD
updated: YYYY-MM-DD
docmind_spec:
  project: <project>
  uniqueName: <uniqueName>
  finalStatus: SPEC_DONE
  acTotal: <N>
---

# Spec: <displayName>

**Source**: DocMind spec `<uniqueName>` (final status: `SPEC_DONE`)
**Snapshot**: `raw/spec-<uniqueName>.md` (immutabile)
**Final AC**: <N>/<N> ✓

## Summary
<paragrafo da spec.description>

## Key Takeaways
1. ...
2. ...

## Entities Mentioned
- [...](../entities/...)

## Concepts Referenced
- [...](../concepts/...)
```

**Snapshot policy:**

- Spec **not DONE** → no source page. Only a backlink in `## Related Specs` on related entity/concept pages.
- Spec **DONE** → snapshot in `raw/spec-<uniqueName>.md` + source page. Both are immutable thereafter.
- Spec **re-opened** after DONE: do **not** modify the original source page. Create a versioned snapshot `raw/spec-<uniqueName>-v2.md` via the standard versioning check, and add a notice to the original source page:

  ```markdown
  > ⚠️ **Spec re-opened** [YYYY-MM-DD]: la spec è tornata in stato `<newStatus>`.
  > Snapshot precedente: `raw/spec-<uniqueName>.md`.
  > Nuovo snapshot al prossimo DONE: `raw/spec-<uniqueName>-v2.md`.
  ```

  On the next DONE, create a distinct source page `wiki/sources/spec-<uniqueName>-v2.md`.

---

## Layer 4 — Spec Workflow Integration

DocMind specs are work items with a formal lifecycle (DRAFT → REVIEW → APPROVED → IMPLEMENTING → DONE). They live on DocMind but intersect the wiki at creation, lifecycle, and compounding at DONE.

### 4a. SPEC-DRAFT — Spec creation from wiki context

*Triggers: "crea una spec", "nuova feature", "draft a spec", "crea draft per <task>"*

1. Identify relevant wiki entity/concept pages for the task.
2. Compose a draft markdown spec from those pages (include relative links to `wiki/...`).
3. Agree initial acceptance criteria with the user (3–7 criteria).
4. `stageDraft(content=<markdown>, kind="spec")` → obtain `draftId`.
5. `spec_create(project, uniqueName, displayName, description, contentRef=draftId, acceptanceCriteria, priority, tags, blockedBy?)`.
6. **Wiki compounding**: add or update `## Related Specs` on every entity/concept touched by the spec.
7. Append to `log.md`: `## [YYYY-MM-DD] spec-created | <uniqueName> — <displayName>`.

**Critical rule**: the spec body must **not** include long-lived architectural decisions. Those stay in the wiki. The spec links the wiki; it does not copy it.

**Expected output**: 1 DocMind spec in `SPEC_DRAFT` + N wiki pages updated in `## Related Specs` + log entry.

### 4b. Spec lifecycle: separation of concerns

| Information type | Where it lives |
|---|---|
| AC refinement | DocMind `spec_update_ac` |
| Implementation plan | DocMind `spec_update_plan` |
| Status transitions | DocMind `spec_transition` (exit criteria enforced) |
| Ephemeral progress note | DocMind `spec_add_notes` |
| Architectural decision from review | Wiki `## Key Decisions` on the related entity — **never** in the spec body |
| Bug / troubleshooting during implementation | Wiki `## Problems & Solutions` — **never** as `spec_add_notes` |
| Emergent general pattern | New or updated wiki concept page — **never** in the spec |
| Live status / AC progress | DocMind only — **never** in the wiki |

**Backlink sync**: on every `spec_transition`, update the status in `## Related Specs` on citing entity/concept pages (local, low cost).

### 4c. SPEC-COMPOUND — DONE → wiki

*Trigger*: `spec_transition` → `SPEC_DONE`. Propose the operation automatically; **require explicit user confirmation** before writing anything under `raw/` or `wiki/`. Manual fallback: *"esegui spec-compound per <uniqueName>"*.

Show the list of files that will be created/modified and wait for an explicit yes.

Steps (after confirmation):

1. `getFlavorByName(<uniqueName>)` → fetch final spec content.
2. Save snapshot to `raw/spec-<uniqueName>.md` (immutable). Apply the standard versioning check.
3. Create `wiki/sources/spec-<uniqueName>.md` using the Spec source page template above.
4. Update related entities:
   - `## Related Specs` → status `SPEC_DONE`.
   - `## Tech Stack / Key Properties` if the spec added system capabilities.
5. Update concept pages if general patterns emerged.
6. Update `wiki/index.md` (Sources table) + `wiki/log.md` (`## [YYYY-MM-DD] spec-done | <uniqueName> — <displayName>`).
7. Propose `PROMOTE` if the knowledge is clearly cross-project (Layer 5).

**Expected output**: 1 raw snapshot, 1 source page, N entity/concept updates, index + log updated.

### 4d. Related Specs convention

See `## Related Specs` above. All Layer 4 workflows depend on it.

---

## Layer 5 — PROMOTE to DocMind

A stable, generally valuable wiki page can be published to DocMind as a team-searchable flavor. This is the opposite of INGEST: mature personal knowledge becomes team knowledge.

### 5a. Promotion threshold

Promote if **at least one** of:

- Page stable for **≥2 weeks** (no substantial body edits).
- Cited by **≥2 distinct DONE specs** (grep `wiki/sources/spec-*.md`).
- Clearly **cross-project** content (generalized pattern, guideline, architectural decision that applies in multiple contexts).

Full LINT reports "Promotion Candidates" for pages that meet the threshold but lack `docmind_mirror` frontmatter.

### 5b. PROMOTE workflow

*Triggers: "promuovi", "pubblica su DocMind", "promote <slug>"*

**User confirmation required** before `uploadDocument` / `updateDocument`: show a preview of the generalized content and wait for an explicit yes.

1. Compose a team-grade version of the page (remove project-specific references if needed, generalize language).
2. `stageFile(content=<markdown>)` or `stageDraft(content=<markdown>)` → `draftId`.
3. `uploadDocument(project=<promote_target>, uniqueName=<slug>, contentRef=draftId, tags=[...])` — `promote_target` comes from `## DocMind Binding` in the wiki's `AGENTS.md`.
4. Add to the wiki page frontmatter:

   ```yaml
   docmind_mirror:
     project: <promote_target>
     uniqueName: <slug>
     lastPushedAt: YYYY-MM-DD
   ```

5. Append to `wiki/log.md`: `## [YYYY-MM-DD] promote | <wiki-path> → <promote_target>/<uniqueName>`.

If `uploadDocument` fails, do **not** write `docmind_mirror`. Report the error for a manual retry.

### 5c. Mirror maintenance

Pages with `docmind_mirror` are active DocMind mirrors. On substantial local edits:

- Propose `updateDocument(project, uniqueName, contentRef)` to refresh the mirror.
- Never sync automatically without user confirmation.
- After `updateDocument`, set `docmind_mirror.lastPushedAt` to today.

Full LINT reports "Mirror Drift" for pages with `docmind_mirror` modified after `lastPushedAt`.

---

## DocMind-aware LINT categories

Run these only in **completo** mode (after estimating call volume and getting user confirmation):

### 🔴 Invalid Spec Backlinks
`uniqueName` values in `## Related Specs` not found by `spec_list(project)` — deleted spec, typo, or wrong project.

### 🟠 Spec Status Drift
Status in `## Related Specs` differs from current DocMind status — fix: update local status.

### 🟠 Missing SPEC_DONE Compounding
Spec is `SPEC_DONE` on DocMind but `wiki/sources/spec-<uniqueName>.md` / `raw/spec-<uniqueName>.md` are missing — fix: run SPEC-COMPOUND retroactively.

### 🟡 Stale Spec Snapshot
`raw/spec-<uniqueName>.md` exists but the DocMind flavor changed after the snapshot — may mean re-open or manual DocMind edit: report, do not auto-resolve.

### 🟡 Promotion Candidates
Pages meeting the Layer 5a threshold without `docmind_mirror` — suggest PROMOTE.

### 🟡 Mirror Drift
Pages with `docmind_mirror` substantially modified after `lastPushedAt` — suggest `updateDocument`.

If DocMind is unavailable during a full LINT: run all local checks plus any DocMind-aware checks that succeeded, and report which checks were skipped.

---

## DocMind quality standards

- **Spec backlinks** (`## Related Specs`): must use valid DocMind `uniqueName` values. Full LINT verifies via `spec_list(project)`.
- **Long-lived architectural decisions** → wiki `## Key Decisions`, **never** in the DocMind spec body. The spec links the decision; it does not contain it.
- **Feature status / AC progress** → DocMind only. Wiki keeps a static backlink in `## Related Specs`, updated on `spec_transition`.
- **Bugs / troubleshooting / patterns** from implementing a spec → wiki (`## Problems & Solutions` or a new concept page), **never** as `spec_add_notes` (DocMind notes are ephemeral).
- **Immutable DONE snapshots**: once `raw/spec-<uniqueName>.md` and `wiki/sources/spec-<uniqueName>.md` exist, do not modify them. On re-open, create `-v2`, `-v3` beside the originals.
