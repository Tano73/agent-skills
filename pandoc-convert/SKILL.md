---
name: pandoc-convert
description: Convert documents between formats using pandoc. Use this skill whenever the user wants to convert, transform, or export a document from one format to another — for example Markdown to Word, HTML to PDF, Word to Markdown, EPUB to HTML, RST to DOCX, or any other format-to-format conversion. Trigger this skill any time the user mentions "convert", "export", "trasforma", "converti", or references two different document formats together, even if they don't explicitly mention pandoc.
---

# Pandoc Document Converter

This skill converts documents between formats using pandoc. Pandoc supports a wide range of formats including Markdown, HTML, DOCX, EPUB, PDF, RST, LaTeX, ODT, and many more.

## Workflow

1. **Identify the input**: locate the source file the user wants to convert. If the path is unclear or the file doesn't exist, ask the user to confirm before proceeding.

2. **Identify the output format**: if the user hasn't specified a target format, always ask before converting. Don't guess. Example: "In quale formato vuoi convertire il file?" or "What output format do you want?".

3. **Determine the output file name**: derive it from the input file name with the appropriate extension (e.g. `report.md` → `report.docx`). Ask the user if they'd prefer a different name or location.

4. **Run pandoc**: execute the conversion:
   ```bash
   pandoc "<input_file>" -o "<output_file>"
   ```
   Pandoc usually auto-detects formats from file extensions, so you rarely need `--from` or `--to` unless the extension is ambiguous.

5. **Confirm success**: tell the user the output file path and confirm it was created. If the conversion fails, show the pandoc error and suggest a fix (e.g. missing LaTeX engine for PDF, unsupported format combination).

## Common format pairs and tips

| Input → Output | Notes |
|----------------|-------|
| `.md` → `.docx` | Works out of the box |
| `.md` → `.pdf` | Requires a LaTeX engine (`pdflatex`, `xelatex`) or `--pdf-engine=wkhtmltopdf` |
| `.docx` → `.md` | Good for extracting content from Word docs |
| `.html` → `.docx` | Pandoc handles most HTML well |
| `.rst` → `.html` | Common for Python docs |
| `.md` → `.epub` | Works out of the box |
| `.md` → `.html` | Use `--standalone` (`-s`) to get a full HTML page |

For PDF output, if a LaTeX engine is not available, suggest `--pdf-engine=wkhtmltopdf` or converting to HTML first.

## Checking available formats

If the user asks what formats are supported:
```bash
pandoc --list-input-formats
pandoc --list-output-formats
```

## Error handling

- **Missing input file**: confirm the path with the user.
- **Unsupported conversion**: explain the limitation and suggest an intermediate step (e.g. DOCX → Markdown → PDF).
- **PDF engine missing**: inform the user and suggest installing `texlive` or using `wkhtmltopdf`.
- **Encoding issues**: try adding `--from=markdown+smart` or specifying the encoding explicitly.
