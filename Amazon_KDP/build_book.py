#!/usr/bin/env python3
"""
KDP Book Build Script — Markdown to PDF
========================================
Generates a KDP-compliant PDF from a collection of Markdown source files.
Tested with 8.5x11 paperback format (no bleed).

Features:
  - YAML frontmatter stripping
  - FloatBarrier per subsection (prevents image drift between sections)
  - Image size caps (width + height) to prevent KDP margin violations
  - Code block line-wrapping at the Markdown level (before Pandoc)
  - HTML <img> tag normalization
  - Zero-width space removal
  - Internal .md cross-link conversion to bold text
  - Heading normalization for Chapter/Appendix headings
  - Auto-discovery of chapter .md files in each part folder

Usage:
    python build_book_template.py
    Run from the repo root directory.

Requirements:
    - Pandoc  (https://pandoc.org)
    - XeLaTeX via MiKTeX or TeX Live
    - The fonts specified in MAIN_FONT, SANS_FONT, MONO_FONT must be installed

Repo structure expected (adjust PARTS / APPENDICES below as needed):
    /
    ├── Part I - Your First Part/
    │   ├── Chapter 1 - Introduction.md
    │   └── Chapter 2 - Next Topic.md
    ├── Part II - Your Second Part/
    │   └── ...
    ├── Appendices/
    │   ├── AppendixA-Reference.md
    │   └── AppendixB-Glossary.md
    └── build/            ← generated PDF lands here
"""

import os
import re
import sys
import shutil
import tempfile
import subprocess
from urllib.parse import unquote

# ──────────────────────────────────────────────────────────────────────────────
# TOOL PATHS
# Adjust these to match where Pandoc and XeLaTeX are installed on your system.
# On Linux/macOS these are usually just "pandoc" and "xelatex" if they're on PATH.
# ──────────────────────────────────────────────────────────────────────────────
PANDOC_BIN   = r"C:\Program Files\Pandoc\pandoc.exe"          # Windows example
XELATEX_BIN  = r"C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe"  # Windows example
# Linux / macOS examples:
# PANDOC_BIN  = "pandoc"
# XELATEX_BIN = "xelatex"

# ──────────────────────────────────────────────────────────────────────────────
# BOOK METADATA
# ──────────────────────────────────────────────────────────────────────────────
BOOK_TITLE    = "Your Book Title"
BOOK_SUBTITLE = "A Descriptive Subtitle"
BOOK_AUTHOR   = "Author Name"
BOOK_YEAR     = "2025"
PDF_OUTPUT    = "Your_Book_KDP.pdf"    # Output filename inside the /build folder

# ──────────────────────────────────────────────────────────────────────────────
# FONTS
# These must be installed on your system. XeLaTeX embeds them automatically.
# Common alternatives:
#   mainfont: "Georgia", "Times New Roman", "EB Garamond"
#   sansfont: "Arial", "Helvetica Neue", "Open Sans"
#   monofont: "Courier New", "Fira Code", "Source Code Pro"
# ──────────────────────────────────────────────────────────────────────────────
MAIN_FONT = "Cambria"
SANS_FONT = "Calibri"
MONO_FONT = "Consolas"

# ──────────────────────────────────────────────────────────────────────────────
# KDP PAGE GEOMETRY — 8.5x11, no bleed
#
# KDP minimums for 301–500 pages (adjust for your page count / trim size):
#   inner (gutter): 0.625in  |  outer: 0.25in
#   top:            0.25in   |  bottom: 0.25in
#
# The values below include comfortable safety buffers above KDP minimums.
# See: https://kdp.amazon.com/en_US/help/topic/G201834190
# ──────────────────────────────────────────────────────────────────────────────
PAPER_WIDTH   = "8.5in"
PAPER_HEIGHT  = "11in"
INNER_MARGIN  = "1in"      # Gutter (binding side) — increase for thick books
OUTER_MARGIN  = "0.75in"
TOP_MARGIN    = "1in"
BOTTOM_MARGIN = "0.75in"

# ──────────────────────────────────────────────────────────────────────────────
# LATEX HEADER
#
# geometry is NOT loaded here — it is passed exclusively via Pandoc -V flags
# so there is exactly ONE geometry specification in the final LaTeX document.
# ──────────────────────────────────────────────────────────────────────────────
# Adjust the book title in \fancyhead[RE] to match your book.
BOOK_HEADER_TEXT = BOOK_TITLE   # Text shown in the even-page header (e.g. right-align on even pages)

LATEX_HEADER = rf"""
\usepackage{{float}}
\usepackage{{fvextra}}
\usepackage{{booktabs}}
\usepackage{{longtable}}
\usepackage{{fancyhdr}}
\PassOptionsToPackage{{hyphens}}{{url}}
\usepackage{{xurl}}
\usepackage{{placeins}}
\usepackage[width=0.9\linewidth,font=small]{{caption}}

% ── IMAGE CONSTRAINTS ──────────────────────────────────────────────────────
% Width:  cap at 80% of linewidth.
% Height: cap at 35% of textheight to leave room for caption + float spacing.
%         This prevents KDP margin overflow violations caused by tall images.
\makeatletter
\def\maxwidth{{\ifdim\Gin@nat@width>0.8\linewidth 0.8\linewidth\else\Gin@nat@width\fi}}
\def\maxheight{{\ifdim\Gin@nat@height>0.35\textheight 0.35\textheight\else\Gin@nat@height\fi}}
\makeatother
\setkeys{{Gin}}{{width=\maxwidth,height=\maxheight,keepaspectratio}}

% ── FIGURE PLACEMENT ───────────────────────────────────────────────────────
% FloatBarrier at every subsection prevents figures from drifting
% more than one section past where they appear in the source.
\let\Oldsubsection\subsection
\renewcommand{{\subsection}}{{\FloatBarrier\Oldsubsection}}

% ── TEXT & CODE WRAPPING ───────────────────────────────────────────────────
\fvset{{breaklines=true,breakanywhere=true,fontsize=\footnotesize}}
\sloppy
\setlength{{\emergencystretch}}{{3em}}
\tolerance=2000
\hyphenpenalty=100

% ── HEADERS / FOOTERS ─────────────────────────────────────────────────────
% Page numbers on outer edges; book title on even pages, chapter on odd pages.
\pagestyle{{fancy}}
\fancyhf{{}}
\fancyhead[LE,RO]{{\thepage}}
\fancyhead[RE]{{\textit{{{BOOK_HEADER_TEXT}}}}}
\fancyhead[LO]{{\begin{{minipage}}[b]{{0.8\textwidth}}\raggedright\textit{{\leftmark}}\end{{minipage}}}}
\renewcommand{{\headrulewidth}}{{0.4pt}}
\providecommand{{\tightlist}}{{%
  \setlength{{\itemsep}}{{0pt}}\setlength{{\parskip}}{{0pt}}}}
"""

# ──────────────────────────────────────────────────────────────────────────────
# BOOK STRUCTURE
#
# PARTS: Each entry maps a folder on disk to a display title and subtitle.
#   "folder"   — subfolder name relative to the repo root
#   "title"    — Part heading printed in the PDF
#   "subtitle" — Italic subtitle shown on the part-divider page
#
# APPENDICES: List of paths relative to repo root.
#   Set to [] if your book has no appendices.
# ──────────────────────────────────────────────────────────────────────────────
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
    {
        "folder":   "Part III - Advanced Topics",
        "title":    "Part III: Advanced Topics",
        "subtitle": "Deeper dives and specialized material.",
    },
    # Add or remove parts as needed.
]

APPENDICES = [
    "Appendices/AppendixA-Reference.md",
    "Appendices/AppendixB-Glossary.md",
    # Add or remove appendix files as needed. Set to [] if none.
]

# ══════════════════════════════════════════════════════════════════════════════
# PREPROCESSING UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def natural_keys(text):
    """Sort key that handles embedded numbers naturally (e.g. Chapter 2 < Chapter 10)."""
    return [int(c) if c.isdigit() else c.lower()
            for c in re.split(r'(\d+)', text)]


def create_part_divider(title, subtitle):
    """Generate a LaTeX part-divider page in Markdown."""
    return f"\n\\newpage\n\n# {title}\n\n*{subtitle}*\n\n\\newpage\n\n"


def wrap_code_smart(content, max_width=75):
    """
    Pre-wrap long lines inside fenced code blocks at the Markdown level.
    This runs before Pandoc so XeLaTeX never sees lines that overflow the margin.
    No special Unicode characters are inserted — only plain ASCII whitespace.
    """
    lines = content.split('\n')
    result = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            result.append(line)
            continue

        if in_code_block and len(line) > max_width:
            stripped = line.lstrip()
            indent = line[:len(line) - len(stripped)]
            cont_indent = indent + "  "
            chunks, remaining, first_chunk = [], stripped, True

            while remaining:
                avail = max_width - len(indent if first_chunk else cont_indent)
                if avail < 10:
                    avail = 10

                if len(remaining) <= avail:
                    chunks.append((indent if first_chunk else cont_indent) + remaining)
                    break

                # Prefer breaking at natural delimiter characters
                break_at = -1
                for ch in [' ', ',', '|', '/', '.', '-', '\\', ':', ';', '=']:
                    pos = remaining.rfind(ch, 0, avail)
                    if pos > 0:
                        break_at = pos + 1
                        break
                if break_at <= 0:
                    break_at = avail

                chunks.append((indent if first_chunk else cont_indent) + remaining[:break_at].rstrip())
                remaining = remaining[break_at:].lstrip()
                first_chunk = False

            result.append('\n'.join(chunks))
        else:
            result.append(line)

    return '\n'.join(result)


def _is_yaml_block(text):
    """
    Return True only if the text contains genuine YAML metadata (key: value pairs).
    Blocks containing only headings or comments are treated as content, not YAML.
    """
    has_kv_pair = False
    for line in text.strip().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if ':' not in stripped:
            return False
        has_kv_pair = True
    return has_kv_pair


def preprocess_markdown(content):
    """
    Run all preprocessing steps on a single chapter's Markdown content.

    Steps:
      1.  Strip YAML frontmatter (only genuine key:value blocks)
      1b. Remove standalone --- lines (Pandoc misreads them as table separators)
      2.  Convert HTML <img> tags to standard Markdown image syntax
      3.  Normalize image paths (strip leading ../ so they resolve from repo root)
      4.  Remove zero-width spaces (KDP flags these as non-printable markup)
      4b. Replace internal .md cross-links with bold text (meaningless in print)
      5.  Promote misleveled Chapter/Appendix headings to H1
      6.  Wrap long lines in code blocks
    """
    # 1. Strip YAML frontmatter — only genuine YAML blocks
    if content.lstrip().startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3 and _is_yaml_block(parts[1]):
            content = parts[2].lstrip()

    # 1b. Remove standalone decorative --- lines
    content = re.sub(r'^-{3,}\s*$', '', content, flags=re.MULTILINE)

    # 2. Convert HTML <img> to Markdown
    content = re.sub(
        r'<img\s+[^>]*src="([^"]+)"[^>]*>',
        r'![](\1)',
        content)

    # 3. Normalize image paths — strip leading ../ sequences
    def fix_image_path(match):
        alt, raw_path = match.group(1), match.group(2)
        clean = unquote(raw_path)
        clean = re.sub(r'^(\.\./)+', '', clean).lstrip('/')
        return f"![{alt}]({clean})"

    content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', fix_image_path, content)

    # 4. Remove zero-width spaces
    content = content.replace('\u200B', '')

    # 4b. Convert internal .md links to bold text
    content = re.sub(
        r'\[([^\]]+)\]\([^)]*\.md[^)]*\)',
        r'**\1**',
        content)

    # 5. Promote misleveled Chapter / Appendix headings to H1
    content = re.sub(
        r'^#{2,}\s*(Chapter\s+\d+.*)$', r'# \1',
        content, flags=re.MULTILINE | re.IGNORECASE)
    content = re.sub(
        r'^#{2,}\s*(Appendix\s+[A-Z].*)$', r'# \1',
        content, flags=re.MULTILINE | re.IGNORECASE)

    # Ensure a space always follows # markers
    content = re.sub(r'^(#+)(?=[A-Za-z0-9])', r'\1 ', content, flags=re.MULTILINE)

    # 6. Wrap long code-block lines
    return wrap_code_smart(content, max_width=75)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN BUILD
# ══════════════════════════════════════════════════════════════════════════════

def main():
    repo_root  = os.path.abspath(os.getcwd())
    output_dir = os.path.join(repo_root, "build")
    os.makedirs(output_dir, exist_ok=True)
    build_temp = tempfile.mkdtemp(prefix="book_build_")

    print(f"{'='*60}")
    print(f"  {BOOK_TITLE}")
    print(f"  {BOOK_SUBTITLE}")
    print(f"  by {BOOK_AUTHOR}")
    print(f"{'='*60}")
    print(f"\nSource:     {repo_root}")
    print(f"Build Mode: {PAPER_WIDTH[:-2]}x{PAPER_HEIGHT[:-2]} KDP Paperback")
    print(f"Temp:       {build_temp}\n")

    try:
        prepared_files = []
        file_counter = 0

        # ── Process Parts & Chapters ────────────────────────────────────────
        for part in PARTS:
            part_path = os.path.join(repo_root, part["folder"])
            if not os.path.exists(part_path):
                print(f"  [!] WARNING: Folder '{part['folder']}' not found — skipping.")
                continue

            # Part-divider page
            file_counter += 1
            divider_path = os.path.join(build_temp, f"{file_counter:03d}_Divider.md")
            with open(divider_path, 'w', encoding='utf-8') as f:
                f.write(create_part_divider(part["title"], part["subtitle"]))
            prepared_files.append(divider_path)

            # Auto-discover all .md files in this part folder (sorted naturally)
            for root, dirs, files in os.walk(part_path):
                dirs.sort(key=natural_keys)
                for file in sorted(files, key=natural_keys):
                    if file.endswith(".md"):
                        file_counter += 1
                        src_path = os.path.join(root, file)
                        with open(src_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                            content = preprocess_markdown(f.read())
                        content += "\n\n"
                        dest_path = os.path.join(build_temp, f"{file_counter:03d}_{file}")
                        with open(dest_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        prepared_files.append(dest_path)
                        print(f"  + {file}")

        # ── Process Appendices ───────────────────────────────────────────────
        appendices_dir = os.path.join(repo_root, "Appendices")
        if APPENDICES and os.path.exists(appendices_dir):
            file_counter += 1
            app_divider = os.path.join(build_temp, f"{file_counter:03d}_App_Divider.md")
            with open(app_divider, 'w', encoding='utf-8') as f:
                f.write("\n\\newpage\n\n# Appendices\n\n\\newpage\n\n")
            prepared_files.append(app_divider)

            for ap_path in APPENDICES:
                src = os.path.join(repo_root, ap_path)
                if not os.path.exists(src):
                    print(f"  [!] Missing appendix: {ap_path}")
                    continue
                with open(src, 'r', encoding='utf-8-sig', errors='replace') as f:
                    content = preprocess_markdown(f.read()) + "\n\n"
                file_counter += 1
                dest_path = os.path.join(
                    build_temp,
                    f"{file_counter:03d}_{os.path.basename(ap_path)}")
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                prepared_files.append(dest_path)
                print(f"  + {os.path.basename(ap_path)}")

        if not prepared_files:
            print("\n[!] ERROR: No files were processed. Check your PARTS folders exist.")
            return

        print(f"\n  {len(prepared_files)} files ready\n")

        # ── Write LaTeX header and YAML metadata ────────────────────────────
        header_path = os.path.join(build_temp, "header.tex")
        with open(header_path, 'w', encoding='utf-8') as f:
            f.write(LATEX_HEADER)

        meta_path = os.path.join(build_temp, "meta.yaml")
        with open(meta_path, 'w', encoding='utf-8') as f:
            f.write(
                f'title: "{BOOK_TITLE}"\n'
                f'subtitle: "{BOOK_SUBTITLE}"\n'
                f'author: "{BOOK_AUTHOR}"\n'
                f'date: "{BOOK_YEAR}"\n'
                f'rights: "Copyright (c) {BOOK_YEAR} {BOOK_AUTHOR}. All rights reserved."\n'
            )

        # ── Run Pandoc ───────────────────────────────────────────────────────
        output_pdf = os.path.join(output_dir, PDF_OUTPUT)
        print(">> Building PDF via Pandoc + XeLaTeX...")

        cmd = [
            PANDOC_BIN, *prepared_files,
            "-f", "markdown-yaml_metadata_block",
            "--metadata-file", meta_path,
            f"--pdf-engine={XELATEX_BIN}",
            f"--resource-path={repo_root}",
            "-H", header_path,
            "--toc",
            "--top-level-division=chapter",
            # Document class
            "-V", "documentclass=book",
            "-V", "classoption=openany",
            # Page geometry (single authoritative source)
            "-V", f"geometry:paperwidth={PAPER_WIDTH}",
            "-V", f"geometry:paperheight={PAPER_HEIGHT}",
            "-V", f"geometry:inner={INNER_MARGIN}",
            "-V", f"geometry:outer={OUTER_MARGIN}",
            "-V", f"geometry:top={TOP_MARGIN}",
            "-V", f"geometry:bottom={BOTTOM_MARGIN}",
            "-V", "geometry:footskip=0.5in",
            "-V", "geometry:headsep=0.25in",
            "-V", "geometry:headheight=14pt",
            "-V", "geometry:includeheadfoot",
            # Fonts
            "-V", f"mainfont={MAIN_FONT}",
            "-V", f"sansfont={SANS_FONT}",
            "-V", f"monofont={MONO_FONT}",
            # Image DPI
            "--dpi=300",
            "-o", output_pdf,
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding='utf-8', errors='replace')

        if result.returncode != 0:
            print("\n[!] BUILD FAILED. Relevant errors from XeLaTeX log:")
            for line in result.stderr.split('\n'):
                if any(x in line for x in ['Error', 'error', '!', 'Fatal']):
                    print(f"  >> {line.strip()}")
            print(f"\nFull log (first 5000 chars):\n{result.stderr[:5000]}")
        else:
            size = os.path.getsize(output_pdf) / (1024 * 1024)
            print(f"\n{'='*60}")
            print(f"  BUILD COMPLETE: {output_pdf}")
            print(f"  File size: {size:.1f} MB")
            print()
            print("  KDP COMPLIANCE CHECKLIST:")
            print(f"  [x] {PAPER_WIDTH[:-2]}x{PAPER_HEIGHT[:-2]} trim, no bleed")
            print(f"  [x] Inner margin {INNER_MARGIN} (KDP min: 0.625in)")
            print(f"  [x] Outer margin {OUTER_MARGIN} (KDP min: 0.25in)")
            print(f"  [x] Top {TOP_MARGIN} / Bottom {BOTTOM_MARGIN} (KDP min: 0.25in)")
            print(f"  [x] Images capped: 80% width, 35% textheight")
            print(f"  [x] FloatBarrier at subsections (no image drift)")
            print(f"  [x] Captions at 90% linewidth, small font")
            print(f"  [x] Fonts embedded via XeLaTeX")
            print(f"  [x] 300 DPI image rendering")
            print(f"  [x] Zero-width spaces stripped")
            print(f"  [x] Code lines pre-wrapped at 75 chars")
            print(f"  [x] Decorative --- lines stripped")
            print(f"  [x] footskip=0.5in (footer clear of bottom margin)")
            print(f"  [x] URL hyphenation enabled")
            print(f"  [x] geometry loaded once (no double-load conflict)")
            print(f"{'='*60}")

    finally:
        shutil.rmtree(build_temp, ignore_errors=True)
        print("  Temporary workspace cleared.")


if __name__ == "__main__":
    main()
