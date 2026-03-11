# 📘 Book Publishing Build Scripts

## KDP Paperback PDF + Google Play EPUB Pipeline
### Two-script toolkit for self-publishing across Amazon KDP and Google Play Books
#### Built for real-world publishing pain: margins, image scaling, code overflow, XHTML compliance, and corrupt image repair

---

## 🗂️ SCRIPTS IN THIS REPO

| Script | Purpose | Output |
|---|---|---|
| `build_book_template.py` | Compiles Markdown → print-ready PDF for Amazon KDP | `build/Your_Book_KDP.pdf` |
| `epub_google_play_fix.py` | Validates and auto-fixes EPUB for Google Play Books | `Your_Book_googleplay.epub` |

---

## 🎯 START HERE

### What these scripts do

**`build_book_template.py`** — PDF pipeline:
- Collects Markdown chapters from your book's folder structure
- Preprocesses Markdown to prevent common KDP/PDF formatting failures
- Builds a single print-ready PDF using **Pandoc + XeLaTeX**
- Outputs your final PDF to `./build/`

**`epub_google_play_fix.py`** — EPUB compliance fixer:
- Extracts and inspects your existing `.epub` file
- Checks all Google Play Books publishing requirements
- Auto-fixes the issues it can; clearly reports what needs manual attention
- Repacks a clean, compliant EPUB ready for upload

---

## 📦 SCRIPT 1 — KDP Paperback PDF

### Dependencies
- **Python 3.8+**
- **Pandoc** — https://pandoc.org
- **XeLaTeX** (via MiKTeX, TeX Live, or MacTeX)

### Configuration
Open `build_book_template.py` and set the configuration section at the top:

```python
# Tool paths
PANDOC_BIN   = r"C:\Program Files\Pandoc\pandoc.exe"       # or "pandoc" on Linux/macOS
XELATEX_BIN  = r"C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe"  # or "xelatex"

# Book metadata
BOOK_TITLE    = "Your Book Title"
BOOK_SUBTITLE = "A Descriptive Subtitle"
BOOK_AUTHOR   = "Author Name"
BOOK_YEAR     = "2025"
PDF_OUTPUT    = "Your_Book_KDP.pdf"

# Page size — 8.5x11 with KDP-safe margins (default)
PAPER_WIDTH   = "8.5in"
PAPER_HEIGHT  = "11in"

# Define your parts/chapters
PARTS = [...]
APPENDICES = [...]
```

### Running the PDF build

```bash
python3 build_book_template.py
```

Windows:
```powershell
py build_book_template.py
```

Expected output:
```
Build Mode: 8.5x11 KDP Paperback
+ Chapter 1 - Getting Started.md
...
>> Building PDF via Pandoc + XeLaTeX...
BUILD COMPLETE: build/Your_Book_KDP.pdf
```

---

## 🗂️ BOOK STRUCTURE

### Folder layout

```text
/
├── Part I - Introduction/
│   ├── Chapter 1 - Getting Started.md
│   └── Chapter 2 - Core Concepts.md
├── Part II - Core Topics/
│   └── Chapter 3 - Topic A.md
├── Appendices/
│   ├── AppendixA-Reference.md
│   └── AppendixB-Glossary.md
├── images/
│   └── diagram.png
├── build/                        ← KDP PDF appears here
├── build_book_template.py
└── epub_google_play_fix.py
```

### Defining parts in the script

```python
PARTS = [
    {
        "folder":   "Part I - Introduction",
        "title":    "Part I: Introduction",
        "subtitle": "Overview and foundational concepts.",
    },
    {
        "folder":   "Part II - Core Topics",
        "title":    "Part II: Core Topics",
        "subtitle": "The main body of the book.",
    },
    # Add or remove parts as needed
]

APPENDICES = [
    "Appendices/AppendixA-Reference.md",
    "Appendices/AppendixB-Glossary.md",
]
```

---

## 🧠 WHAT THE PDF SCRIPT DOES (UNDER THE HOOD)

### Stage 1 — Preprocess Markdown
The `preprocess_markdown()` function runs before Pandoc and handles:

1. **YAML Frontmatter Stripping** — Strips genuine YAML blocks so Pandoc doesn't get confused. Removes decorative `---` dividers that Pandoc misinterprets as table separators.
2. **HTML `<img>` → Markdown image conversion** — `<img src="images/foo.png">` becomes `![](images/foo.png)`
3. **Image path normalization** — URL-decodes `%20` → space, strips leading `../` segments
4. **Zero-width space removal** — Strips `\u200B` characters (KDP flags these)
5. **Internal `.md` link conversion** — Cross-chapter links are replaced with bold text (meaningless in print)
6. **Heading normalization** — Promotes misleveled headings to H1 for correct TOC generation
7. **Code block hard-wrapping** — Wraps lines >75 chars to prevent code overflowing the right margin

---

## 📦 SCRIPT 2 — Google Play Books EPUB Fixer

### Dependencies

```bash
pip install Pillow lxml
```

Both are optional but strongly recommended:
- **Pillow** — repairs corrupt PNG/JPEG image files properly
- **lxml** — more robust XML parsing than Python stdlib

### Usage

```bash
# Check-only mode — see all issues without changing anything
python epub_google_play_fix.py your_book.epub --check-only

# Fix mode — auto-fixes all issues it can, outputs a new file
python epub_google_play_fix.py your_book.epub

# Custom output name
python epub_google_play_fix.py your_book.epub -o your_book_googleplay.epub
```

### What it checks and fixes

| Check | Auto-Fix |
|---|---|
| `<br>`, `<img>`, `<hr>` not self-closed (XHTML requires `<br/>`) | ✅ |
| Manifest `media-type` mismatches | ✅ |
| Files on disk missing from OPF manifest | ✅ |
| Manifest entries pointing to missing files | ⚠ Reports only |
| Corrupt PNG/JPEG images | ✅ via Pillow |
| Missing OPF metadata (title, author, language, identifier) | ✅ |
| `mimetype` file wrong, missing, or has BOM | ✅ |
| Missing UTF-8 encoding declaration in XHTML | ✅ |
| Missing XHTML namespace on `<html>` tag | ✅ |
| CSS wrong `@charset` declaration | ✅ |
| Broken spine references | ✅ |
| Duplicate IDs across chapters | ⚠ Reports only |
| Filenames with spaces or non-ASCII characters | ⚠ Reports only |
| No cover image declared | ⚠ Reports only |

### Understanding the output

```
── Manifest & Files ──────────────────────────────────
  ✗ ERROR:   Image file is corrupt or wrong format: media/file22.png
  ✔ FIXED:   Re-saved media/file22.png as valid PNG

── XHTML Content ─────────────────────────────────────
  ✔ FIXED:   Fixed void tags in ch004.xhtml

════════════════════════════════════════════════════════════
  Errors:   0
  Warnings: 0
  Fixed:    2
════════════════════════════════════════════════════════════

✅ Fixed EPUB: your_book_googleplay.epub
```

- `✔ FIXED` means the issue was resolved automatically in the output file
- `✗ ERROR` with no corresponding `✔ FIXED` means manual intervention is needed
- `⚠ WARNING` items are non-blocking but worth reviewing

### After running the fixer

1. Upload `The_Computer_Handbook_googleplay.epub` to Google Play Books Partner Center
2. For extra pre-upload validation, run epubcheck:
```bash
java -jar epubcheck.jar your_book_googleplay.epub
```
epubcheck download: https://github.com/w3c/epubcheck/releases

---

## ⚙️ PDF CONFIGURATION REFERENCE

### Page geometry

Defaults are **8.5×11 in (US Letter)** with margins that meet KDP minimums for 301–500 page books.

| Variable | Default | KDP Minimum |
|---|---|---|
| `INNER_MARGIN` (gutter) | `1in` | 0.625in |
| `OUTER_MARGIN` | `0.75in` | 0.25in |
| `TOP_MARGIN` | `1in` | 0.25in |
| `BOTTOM_MARGIN` | `0.75in` | 0.25in |

KDP margin requirements vary by page count and trim size. Always verify at:
https://kdp.amazon.com/en_US/help/topic/G201834190

### Fonts

| Variable | Default | Notes |
|---|---|---|
| `MAIN_FONT` | `Cambria` | Body text — try `Georgia`, `EB Garamond` |
| `SANS_FONT` | `Calibri` | Headings — try `Arial`, `Open Sans` |
| `MONO_FONT` | `Consolas` | Code blocks — try `Fira Code`, `Courier New` |

Fonts must be installed on your system. XeLaTeX embeds them automatically.

---

## 🖼️ IMAGES

Pandoc runs with `--resource-path=<repo_root>`, so image paths resolve from the repo root.

### Recommended patterns
```markdown
![Alt text](images/diagram.png)
![Alt text](Part I - Computer Fundamentals/images/picture.png)
```

### Avoid
- Absolute paths like `/images/foo.png`
- Deep relative paths like `../../../images/foo.png`

### Image size limits (PDF)
The script caps images to prevent KDP margin violations:
- **Width:** max 80% of text width
- **Height:** max 35% of text height (~3.2in on 8.5×11)

---

## 🧯 TROUBLESHOOTING

### PDF Build

**`pandoc: command not found`**
Pandoc is not installed or not on PATH. Reinstall from https://pandoc.org.

**`xelatex not found` / LaTeX package errors**
TeX distribution missing. Install MiKTeX / TeX Live / MacTeX.

**`[!] WARNING: Folder not found`**
The `"folder"` value in `PARTS` doesn't match the actual folder name on disk. Folder names are case-sensitive on Linux/macOS.

**KDP preview: "Text/Image outside margins"**
- Image too large — lower the `maxheight`/`maxwidth` percentages in `LATEX_HEADER`
- Table too wide — simplify or convert to a list
- Long unbroken string (URL, hash) — manually break it in Markdown

### EPUB Fixer

**`Exception in Manifest & Files`**
Run `pip install lxml` then retry. The stdlib XML parser can fail on malformed OPF files.

**Image replaced with blank placeholder**
`file22.png` (or another image) was too corrupt for Pillow to recover. Open the source image in any image editor, re-export it as PNG, and replace the placeholder in the fixed EPUB manually.

**Still failing on Google Play after running the fixer**
Run epubcheck for a full diagnostic report:
```bash
java -jar epubcheck.jar your_book_googleplay.epub
```
Paste the output here for help interpreting the results.

---

## 📦 BUILD ARTIFACTS

| Path | Description |
|---|---|
| `build/Your_Book_KDP.pdf` | Amazon KDP print-ready PDF |
| `your_book_googleplay.epub` | Google Play Books compliant EPUB |

---

## 🧪 ADVANCED NOTES

### Why XeLaTeX?
XeLaTeX handles Unicode and system fonts far more reliably than pdfLaTeX — important for books with special characters or modern font choices.

### Deterministic chapter ordering
Files are sorted using natural ordering (`Chapter 2` before `Chapter 10`). To lock order unconditionally, use numeric prefixes: `001_Intro.md`, `010_Core.md`.

### Changing trim size (e.g., 6×9)
Update `PAPER_WIDTH`, `PAPER_HEIGHT`, and the margin variables. Verify KDP's margin requirements for that trim size before uploading.

### geometry is loaded once
`geometry` is passed exclusively through Pandoc's `-V` flags — not in `LATEX_HEADER`. This prevents the double-loading conflict that causes cryptic LaTeX errors.

---

## ⚖️ PUBLISHING DISCLAIMER

These scripts produce output files. You are responsible for:
- Verifying layout in KDP Previewer before publishing
- Reviewing the fixed EPUB in a reader (e.g., Calibre, Apple Books) before uploading
- Ensuring you have rights to all included content (text and images)
- Complying with Amazon KDP and Google Play Books publishing requirements

---

## 🙏 CREDITS

### Toolchain
- **Pandoc** — Markdown-to-LaTeX-to-PDF conversion
- **XeLaTeX** — Unicode-friendly LaTeX engine
- **Pillow** — Python image processing for EPUB image repair
- **lxml** — Fast, robust XML/XHTML parsing

### LaTeX packages used
`geometry`, `graphicx`, `fancyhdr`, `longtable`, `booktabs`, `fvextra`, `float`, `placeins`, `caption`, `xurl`

---

## ✅ TL;DR

### Build the KDP PDF
```bash
python3 build_book_template.py
# → build/Your_Book_KDP.pdf
```

### Fix the EPUB for Google Play
```bash
pip install Pillow lxml
python epub_google_play_fix.py your_book.epub
# → your_book_googleplay.epub
```

### Then upload
- `Your_Book_KDP.pdf` → Amazon KDP
- `your_book_googleplay.epub` → Google Play Books Partner Center
