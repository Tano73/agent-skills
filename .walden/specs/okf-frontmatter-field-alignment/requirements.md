---
walden_schema_version: v1alpha1
status: approved
approved_at: 2026-09-22T10:44:20Z
last_modified: 2026-09-22T10:44:20Z
approved_fingerprint: sha256:b455680da6e9ff31d70418b381e2c9057a22f90c8d85e3757a43fc1632f47744
---

# Requirements Document

## Introduction

Following the feasibility study on adopting the Open Knowledge Format (OKF v0.1), the
`llm-wiki-manager` skill will partially align its documented wiki page frontmatter field
names to the OKF equivalents, **but only where the rename preserves 100% of existing
information** (a straight name swap with no field split, merge, or dropped semantics).

In scope: renaming the `category` field to `type`, and the `source_file` field
(source pages only) to `resource`. Both renames keep the same value semantics — no
new allowed values, no restructuring.

Out of scope (per the OKF feasibility study, lossy or without an OKF equivalent):
`created`/`updated` → `timestamp`, `sources`, and `docmind_mirror`.

<!-- assumed: field VALUES are unchanged; only field NAMES are renamed (source: user scope "solo allineamento dei nomi dove non c'è perdita informativa") -->

## Requirements

### R1 Rename `category` to `type` in page frontmatter

**User Story:** As a maintainer of an llm-wiki, I want wiki pages to use the OKF-aligned
`type` field name instead of `category`, so that the wiki's frontmatter vocabulary is
closer to the emerging OKF standard without losing any existing classification information.

#### Acceptance Criteria

1. `R1.AC1` WHEN the skill creates a new entity, concept, source, or overview page, the system SHALL write its classification using the `type` frontmatter field instead of `category`.
   - Acceptance check: a newly created page's frontmatter contains `type: <value>` and does not contain a `category:` key.
2. `R1.AC2` WHEN the skill reads a page whose frontmatter uses the legacy `category` field, the system SHALL treat its value identically to an equivalent `type` field for all classification-dependent behavior (lint, index generation, page-type routing).
   - Acceptance check: an existing page with `category: entity` (no `type` field) is still recognized as an entity page by every check that previously relied on `category`.
3. `R1.AC3` WHERE a page's frontmatter contains both `category` and `type` with different values, the system SHALL flag it as an inconsistency rather than silently preferring one field.
   - Acceptance check: a page with `category: entity` and `type: concept` produces a reported inconsistency instead of being silently classified as one or the other.
4. `R1.AC4` WHEN the skill's documentation (`SKILL.md`) describes the frontmatter convention for pages, the system SHALL document `type` as the current field name and `category` as a supported legacy alias.
   - Acceptance check: `SKILL.md`'s frontmatter/page-convention sections reference `type` as the field to write and mention `category` only as a recognized legacy alias.

### R2 Rename `source_file` to `resource` in source page frontmatter

**User Story:** As a maintainer of an llm-wiki, I want source pages to use the
OKF-aligned `resource` field name instead of `source_file`, so that provenance
references follow the same naming convention as the emerging OKF standard.

#### Acceptance Criteria

1. `R2.AC1` WHEN the skill creates a new source page, the system SHALL record the provenance path using the `resource` frontmatter field instead of `source_file`.
   - Acceptance check: a newly created source page's frontmatter contains `resource: raw/<filename>` and does not contain a `source_file:` key.
2. `R2.AC2` WHEN a mechanical check (e.g. `wiki_lint.py`) validates a source page's provenance field, the system SHALL accept either `resource` or the legacy `source_file` field as the provenance path.
   - Acceptance check: running the lint check against an existing source page that has only `source_file` (no `resource`) does not report a missing-provenance issue.
3. `R2.AC3` IF a source page has neither `resource` nor `source_file`, THEN the system SHALL report it as missing provenance, as it does today.
   - Acceptance check: a source page with neither field still produces the existing "missing provenance" finding, unchanged in wording and severity.
4. `R2.AC4` WHERE a source page's frontmatter contains both `resource` and `source_file` with different path values, the system SHALL flag it as an inconsistency rather than silently preferring one field.
   - Acceptance check: a page with differing `resource` and `source_file` paths produces a reported inconsistency instead of validating against only one of them.

## Non-Functional Requirements

- `NFR1` The rename SHALL NOT require any change to existing wiki content on disk;
  wikis created before this change continue to validate and function without manual
  migration.

## Constraints And Dependencies

- `C1` Changes are limited to `skills/llm-wiki-manager/SKILL.md` (documented
  convention) and `skills/llm-wiki-manager/scripts/wiki_lint.py` (mechanical check for
  the `resource`/`source_file` alias, per R2.AC2–R2.AC4). No change to page templates'
  other fields (`title`, `tags`, `created`, `updated`, `sources`, `docmind_mirror`).
- `C2` This feature depends on the OKF v0.1 feasibility study's field mapping
  (`category`→`type`, `source_file`→`resource` as the only lossless renames).

## Out Of Scope

- Renaming or restructuring `created`/`updated` into a single OKF `timestamp` field
  (lossy: two fields collapse to one).
- Introducing OKF's `description` field (not part of a name-alignment; would be new
  content, not a rename).
- Any representation change for `sources` or `docmind_mirror` (no OKF equivalent).
- Bulk migration/rewrite of already-ingested wiki pages to the new field names.
- Adoption of OKF bundle/directory conventions (entities/concepts/sources folder
  structure is unaffected).
