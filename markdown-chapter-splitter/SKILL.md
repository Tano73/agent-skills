---
name: markdown-chapter-splitter
description: Split large Markdown (.md) files into smaller Markdown files, one per chapter. Use this skill whenever the user wants to split, chunk, divide, or reorganize a Markdown file by chapters or headings, especially for books, manuals, long notes, or documentation. Trigger even when the user says "one file per chapter", "split this markdown", or "separa i capitoli" without explicitly naming a skill. When Markdown H1 chapters are missing or unreliable, use this skill to infer chapter starts from text patterns like `CHAPTER 5`, `Chapter One. Title`, `Chapter 3. Title`, or numbered chapter title pairs instead of degrading to generic H2 splitting.
---

# Markdown Chapter Splitter

Use this skill to turn one large Markdown file into a sibling folder of smaller `.md`
files, with one file per top-level chapter.

## Default behavior

- Treat only level-1 headings (`# Heading`) as chapter boundaries.
- Keep nested sections (`##`, `###`, and deeper) inside the same chapter file.
- Write output in a sibling folder named `<input-stem>/` (same name as the file without extension) unless the user
  explicitly asks for a different path.
- If the source contains content before the first `#` chapter (frontmatter, title
  page, preface, introduction), save it as `00-preface.md`.
- Generate chapter filenames from the chapter title, sanitized for filesystem safety
  and prefixed with chapter order, for example:
  - `01-introduction.md`
  - `02-system-design.md`
- Preserve the original chapter heading as the first heading in each chapter file.
- Ignore `#` lines inside fenced code blocks so code samples do not create false
  chapter splits.
- If no reliable H1 chapters are found, or only one H1 chapter is found, try the
  bundled text-chapter heuristic before giving up on chapter splitting.
- The heuristic should recognize common book-style chapter markers such as:
  - `CHAPTER 5` followed by a title on the next line
  - `Chapter One. Crunching Knowledge`
  - `Chapter 3. Mapping to Relational Databases`
  - `## CHAPTER 1 Layered Architecture`
  - `## 1` followed by `## WHAT IS DESIGN AND ARCHITECTURE?`
- The heuristic should prefer real chapter starts over table-of-contents entries.

## When to ask before running

Ask the user instead of assuming if:

- the input file path is missing or ambiguous
- they want split points based on `##` or another heading level
- they want a custom output directory or naming scheme
- they want frontmatter copied into every chapter file instead of a separate preface
  file
- they explicitly do not want automatic text-based chapter inference

## Workflow

1. Resolve the input `.md` file path and confirm it exists.
2. Set the output directory:
   - default: `<same-directory>/<input-stem>/` (directory named after the file stem, no `-chapters` suffix)
   - custom: only if the user explicitly asked for one
3. Run the bundled splitter script in default mode first:

   ```bash
   python3 "$HOME/.copilot/skills/markdown-chapter-splitter/scripts/split_markdown_by_chapter.py" "<input_file>" --output-dir "<output_dir>"
   ```

   If the user did not request a custom directory, omit `--output-dir`.

4. Read the script output carefully:
   - If it reports `Split mode used: TEXT_CHAPTER`, accept that result. The script
     found a reliable numbered chapter sequence in the text and already split on the
     inferred chapter boundaries.
   - If it reports `Split mode used: H1`, accept that result.
   - If it reports that no reliable H1 or text-chapter sequence was found, explain
     that the file does not expose reliable chapter boundaries and do not degrade to
     generic `##` splitting automatically.
   - If the script found exactly one H1 chapter and the user wants to keep that as a
     single output file, rerun with `--allow-single-section`.
   - Only use `--heading-level 2` when the user explicitly asks for section-based
     splitting by `##` instead of real chapter detection.

5. Read the final script output and report:
   - output directory path
   - split mode used (`H1` or `TEXT_CHAPTER`, plus `H2` only when the user explicitly
     requested section-based splitting)
   - number of section files created
   - whether a `00-preface.md` file was created
   - how many H1 and H2 headings the script detected
   - how many text chapter candidates the script detected

## Expected result

The result should be a folder containing:

- zero or one `00-preface.md`
- one `.md` file for each chosen split section (`#` by default, inferred text
  chapters when reliable, `##` only when the user explicitly asks for section-based
  splitting)
- numerically ordered filenames to preserve the original chapter order

## Examples

**Example 1:**
Input: "Dividi `/tmp/architecture.md` in un file per capitolo."
Output: The agent creates `/tmp/architecture/`, writes `00-preface.md` if
needed, then `01-...md`, `02-...md`, and reports the generated files.

**Example 2:**
Input: "Split `/work/book.md` into one Markdown file per chapter."
Output: The agent uses the bundled script, keeps `##` sections inside each chapter
file, and reports the destination directory.

**Example 3:**
Input: "Dividi `/tmp/manual.md` in un file per capitolo."
Output: If the script finds 0 or 1 H1 chapters and no reliable text-based chapter
sequence, the agent explains that the file does not expose real chapter boundaries
and does not fall back automatically to every `##` subsection.

**Example 4:**
Input: "Split `/tmp/oreilly-book.md` into one file per chapter."
Output: If the file contains plain text chapter markers like `CHAPTER 5` and
`Events: A Basis for Collaboration`, or lines like `Chapter One. Crunching
Knowledge`, the script automatically uses `TEXT_CHAPTER` mode instead of falling back
to every `##` subsection.

## Notes

- Prefer the bundled script over manual editing so the split stays deterministic.
- Prefer inferred numbered chapter starts over generic H2 splitting when the text
  clearly exposes chapter boundaries.
- Do not degrade from H1 or inferred text chapters to generic H2 splitting unless the
  user explicitly asked for section-based splitting.
- Do not delete the original file.
- If the output directory already exists, it is acceptable to overwrite files with
  the same generated names, but do not remove unrelated files.
