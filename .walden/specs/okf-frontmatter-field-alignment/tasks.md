---
walden_schema_version: v1alpha1
status: approved
approved_at: 2026-09-22T12:18:37Z
last_modified: 2026-09-22T12:22:09Z
approved_fingerprint: sha256:7a61aa824b5c635ea2e3f142bd86fbed3efe62eb7ce263fdc81aaffdcf3a5775
source_design_approved_at: 2026-09-22T10:48:02Z
source_design_fingerprint: sha256:5971dca497fea72eb9ae48d38130362de127acff42f218ef7dcfedf4ace48aac
---

# Implementation Plan

- [x] 1. Update SKILL.md frontmatter conventions to document the OKF-aligned field names
  - [x] 1.1 Document `type` (with `category` as a recognized legacy alias) in the shared page frontmatter convention
    - Requirements: `R1.AC1`, `R1.AC4`
    - Design: Architecture (SKILL.md conventions, R1)
    - Verification:
      - command: ["sh", "-c", "grep -F 'type: entity | concept | source | overview' skills/llm-wiki-manager/SKILL.md"]
        expect_output: "type: entity | concept | source | overview"
        covers: ["R1.AC1"]
      - command: ["sh", "-c", "grep -F 'legacy alias: category' skills/llm-wiki-manager/SKILL.md"]
        expect_output: "legacy alias: category"
        covers: ["R1.AC4"]
  - [x] 1.2 Document `resource` (with `source_file` as a recognized legacy alias) in the source page frontmatter convention
    - Requirements: `R2.AC1`
    - Design: Architecture (SKILL.md conventions, R2)
    - Verification:
      - command: ["sh", "-c", "grep -F 'resource: raw/<filename>' skills/llm-wiki-manager/SKILL.md"]
        expect_output: "resource: raw/<filename>"
        covers: ["R2.AC1"]
      - command: ["sh", "-c", "grep -F 'legacy alias: source_file' skills/llm-wiki-manager/SKILL.md"]
        expect_output: "legacy alias: source_file"
        covers: ["R2.AC1"]

- [x] 2. Implement alias-aware provenance resolution and field_conflict checks in wiki_lint.py
  - [x] 2.1 Add `RESOURCE_RE` and resource/source_file fallback resolution for source page provenance
    - Requirements: `R2.AC2`, `R2.AC3`
    - Design: Architecture (wiki_lint.py, R2); Verification Plan
    - Verification:
      - command: ["python3", "skills/llm-wiki-manager/scripts/test_frontmatter_aliases.py", "resource_only"]
        expect_output: "PASS: resource_only"
        covers: ["R2.AC2"]
      - command: ["python3", "skills/llm-wiki-manager/scripts/test_frontmatter_aliases.py", "source_file_only"]
        expect_output: "PASS: source_file_only"
        covers: ["R2.AC2"]
      - command: ["python3", "skills/llm-wiki-manager/scripts/test_frontmatter_aliases.py", "neither_resource_nor_source_file"]
        expect_output: "PASS: neither_resource_nor_source_file"
        covers: ["R2.AC3"]
  - [x] 2.2 Add `field_conflict` reporting when `resource` and `source_file` differ
    - Requirements: `R2.AC4`
    - Design: Architecture (wiki_lint.py, R2); Verification Plan
    - Verification:
      - command: ["python3", "skills/llm-wiki-manager/scripts/test_frontmatter_aliases.py", "resource_source_file_conflict"]
        expect_output: "PASS: resource_source_file_conflict"
        covers: ["R2.AC4"]
  - [x] 2.3 Add `field_conflict` reporting when `category` and `type` differ, and confirm legacy `category`-only pages are unaffected
    - Requirements: `R1.AC2`, `R1.AC3`
    - Design: Architecture (wiki_lint.py, R1); Verification Plan
    - Verification:
      - command: ["python3", "skills/llm-wiki-manager/scripts/test_frontmatter_aliases.py", "category_type_conflict"]
        expect_output: "PASS: category_type_conflict"
        covers: ["R1.AC3"]
      - command: ["python3", "skills/llm-wiki-manager/scripts/test_frontmatter_aliases.py", "category_only_unaffected"]
        expect_output: "PASS: category_only_unaffected"
        covers: ["R1.AC2"]

- [x] 3. Confirm no migration is required for existing wikis (NFR1)
  - [x] 3.1 Run the full alias/conflict test suite against legacy-only fixtures as a combined regression check
    - Requirements: `NFR1`
    - Design: Verification Plan; Requirement Coverage
    - Verification:
      - command: ["python3", "skills/llm-wiki-manager/scripts/test_frontmatter_aliases.py", "all"]
        expect_output: "ALL TESTS PASSED"
        covers: ["NFR1"]

