---
walden_schema_version: v1alpha1
status: approved
approved_at: 2026-09-22T10:48:02Z
last_modified: 2026-09-22T10:48:02Z
approved_fingerprint: sha256:5971dca497fea72eb9ae48d38130362de127acff42f218ef7dcfedf4ace48aac
source_requirements_approved_at: 2026-09-22T10:44:20Z
source_requirements_fingerprint: sha256:b455680da6e9ff31d70418b381e2c9057a22f90c8d85e3757a43fc1632f47744
---

# Feature Design

## Architecture

Two independent surfaces change, both additive (no removal of existing behavior):

1. **`SKILL.md` conventions (R1, R2 — documentation only)**
   - Frontmatter templates for entity/concept/overview pages document `type` as the
     field to write (values unchanged: `entity | concept | source | overview`), with
     `category` documented as a recognized legacy alias, not a removed field.
   - The source page frontmatter template documents `resource` as the field to write
     (same value shape as today: `raw/<filename>`), with `source_file` documented as a
     recognized legacy alias.
   - No change to any other documented field (`title`, `tags`, `created`, `updated`,
     `sources`, `docmind_mirror`).

2. **`wiki_lint.py` (R2, and R1's conflict check — mechanical)**
   - `wiki_lint.py` is the only piece of code that parses page frontmatter today, and
     it already parses `source_file` via `SOURCE_FILE_RE` + `meta.get("source_file")`.
     It does **not** parse `category` at all (page classification comes from the
     `entities/ | concepts/ | sources/` folder, not the frontmatter value).
   - Add a `RESOURCE_RE` regex mirroring `SOURCE_FILE_RE`. Provenance resolution for a
     source page becomes: prefer `resource`, fall back to `source_file`, else report
     `missing_provenance` (unchanged wording/severity). If both are present and their
     resolved values differ, report a new `field_conflict` issue instead of silently
     preferring one (R2.AC4).
   - Add the same conflict pattern for `category` vs `type` on every content page
     (entity/concept/source/overview): if both frontmatter keys are present with
     different values, report `field_conflict` (R1.AC3). This reuses the already
     in-memory `meta` dict from `parse_frontmatter` — no new parsing infrastructure.
   - `type`-only or `category`-only pages continue to be classified purely by their
     folder, exactly as before: R1.AC2 ("legacy `category` is recognized identically
     to `type`") is satisfied structurally, because no mechanical check ever branches
     on that field's value in the first place.

<!-- assumed: implement R1.AC3's conflict check as a wiki_lint.py mechanical check,
     mirroring R2.AC4, instead of leaving it as agent-only guidance in SKILL.md
     (source: symmetry with the existing source_file/resource pattern already coded
     in wiki_lint.py; a deterministic check is preferable to a prose-only rule and
     matches the "system SHALL flag it" wording of R1.AC3). -->

## Options Considered

**Chosen:** additive alias support (write new name, read/accept both names, flag only
genuine conflicts) in both `SKILL.md` and `wiki_lint.py`.

**Alternative considered:** a hard cut — document and check only `type`/`resource`,
treating `category`/`source_file` as unrecognized/deprecated. Rejected: it would
violate the approved `NFR1` (no change to existing wiki content required) and the
user's explicit backward-compatibility decision, since every already-ingested page
still uses the legacy names.

## Simplicity And Elegance Review

No new parsing library, data model, or file format is introduced. The change reuses
the existing `parse_frontmatter()` dict and the existing regex-per-field pattern
(`SOURCE_FILE_RE` → `RESOURCE_RE`), applying the identical shape to `category`/`type`.
The conflict check is a single generic comparison (`old_value present and new_value
present and old_value != new_value`) applied to two field pairs, not a bespoke rule
per pair.

## Failure Modes And Tradeoffs

- **Ambiguous frontmatter during transition** (both old and new field present with
  different values): surfaced as a new `field_conflict` finding (medium severity)
  instead of silently picking one value — avoids masking a real authoring mistake.
- **`parse_frontmatter`'s naive `key: value` line split** (pre-existing limitation,
  e.g. a value containing an unquoted colon) is unchanged and out of scope for this
  feature; it affects `category`/`type`/`resource`/`source_file` identically to how
  it already affects every other field today.
- **Tradeoff accepted:** `SKILL.md` now documents two names per concept (current +
  legacy alias) instead of one, adding minor documentation verbosity, in exchange for
  zero required migration of existing wikis (per `NFR1`).

## Verification Plan

- Script-level checks against small fixture wiki trees (temp directories), run via
  `wiki_lint.py --json` and asserted on the emitted `issues` list:
  - Source page with only `source_file` → no `missing_provenance` issue (R2.AC2).
  - Source page with only `resource` → no `missing_provenance` issue (R2.AC1/AC2).
  - Source page with neither → `missing_provenance` issue, unchanged (R2.AC3).
  - Source page with both `resource` and `source_file` pointing to different paths →
    a `field_conflict` issue is reported (R2.AC4).
  - Content page with both `category` and `type` set to different values → a
    `field_conflict` issue is reported (R1.AC3).
  - Content page with only legacy `category` (no `type`) lints clean of any new
    finding caused by this feature (R1.AC2 — classification is unaffected).
- Documentation checks against `SKILL.md`: the source page template contains
  `resource:` and mentions `source_file` as a legacy alias (R2 doc side); the
  entity/concept/overview templates or surrounding prose contain `type:` and mention
  `category` as a legacy alias (R1.AC4).

## Requirement Coverage

| Requirement | Covered By |
| --- | --- |
| `R1` | `SKILL.md` template updates (AC1, AC4) plus the new `wiki_lint.py` `field_conflict` check (AC3) and the structural non-branching guarantee (AC2). |
| `R2` | `SKILL.md` source page template update (AC1) plus `wiki_lint.py`'s `RESOURCE_RE`/fallback and `field_conflict` check (AC2–AC4). |
| `R1.AC1` | `SKILL.md` page templates write `type:` for new pages. |
| `R1.AC2` | Structural: no mechanical check in `wiki_lint.py` ever branches on `category`/`type` value, so a legacy-only page is unaffected. |
| `R1.AC3` | New `field_conflict` check in `wiki_lint.py` comparing `category` vs `type` when both present. |
| `R1.AC4` | `SKILL.md` documents `type` as current and `category` as legacy alias. |
| `R2.AC1` | `SKILL.md` source page template writes `resource:` for new source pages. |
| `R2.AC2` | `wiki_lint.py`'s new `RESOURCE_RE` + fallback to `source_file` in provenance resolution. |
| `R2.AC3` | Existing `missing_provenance` check, now gated on "neither field present." |
| `R2.AC4` | New `field_conflict` check in `wiki_lint.py` comparing `resource` vs `source_file` when both present and differing. |
| `NFR1` | No migration step in any task; both old and new field names accepted by `wiki_lint.py` and described in `SKILL.md`; verified by the "legacy-only" fixture cases above. |
| `C1` | Only `SKILL.md` and `wiki_lint.py` are touched; other fields (`title`, `tags`, `created`, `updated`, `sources`, `docmind_mirror`) are untouched in both files. |
| `C2` | Field mapping (`category`→`type`, `source_file`→`resource`) matches the OKF v0.1 feasibility study's lossless-rename set exactly; no other field from that study is renamed. |
