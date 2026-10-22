#!/usr/bin/env bash
# extract_pdf.sh — Extract text & tables from a PDF file with page anchors
# Usage: extract_pdf.sh <input.pdf> [output.txt]
#
# Extraction pipeline:
# 1. Table-Aware Extraction (via pdfplumber / MarkItDown if available)
# 2. pdftotext (poppler-utils) — high-speed extraction with layout preservation & form-feed page splitting
# 3. PyMuPDF (fitz) — fast python fallback with per-page text & OCR
# 4. OCR via Tesseract + pdftoppm — automatic fallback for scanned/image-only PDFs
#
# Inserts "<!-- page: N -->\n## Page N" markers between pages for chunking & ledger mapping.
# Heals broken partial section numbers (.1\nSection -> .1 Section).

set -euo pipefail

INPUT="${1:?Usage: extract_pdf.sh <input.pdf> [output.txt]}"
OUTPUT="${2:-${INPUT}.extracted.txt}"

if [[ ! -f "$INPUT" ]]; then
  echo "Error: File not found: $INPUT" >&2
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"

# Helper: check if extraction produced meaningful text (>10 non-empty lines)
has_meaningful_text() {
  local file="$1"
  [[ -f "$file" ]] && [[ $(grep -cP '\S' "$file" 2>/dev/null || echo 0) -gt 10 ]]
}

# Helper: post-process to heal broken section numbers (.1\nTitle -> .1 Title)
heal_section_numbers() {
  local file="$1"
  if [[ -f "$file" ]] && command -v python3 &>/dev/null; then
    python3 -c '
import sys, re
target = sys.argv[1]
pattern = re.compile(r"^\.\d+$")
with open(target, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()
out = []
i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    if pattern.match(stripped):
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines):
            out.append(f"{stripped} {lines[j].strip()}\n")
            i = j + 1
            continue
    out.append(line)
    i += 1
with open(target, "w", encoding="utf-8") as f:
    f.writelines(out)
' "$file" 2>/dev/null || true
  fi
}

# --- Method 1: pdfplumber (table-aware with page anchors) ---
if python3 -c "import pdfplumber" &>/dev/null; then
  echo "Extracting PDF with pdfplumber (table-aware & page anchors)..." >&2
  if python3 -c '
import pdfplumber, sys, os
in_f, out_f = sys.argv[1], sys.argv[2]
try:
    with pdfplumber.open(in_f) as pdf:
        pages_text = []
        for i, page in enumerate(pdf.pages, start=1):
            p_text_parts = [f"\n<!-- page: {i} -->\n## Page {i}\n"]
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    col_count = max(len(r) for r in table if r) if table else 0
                    if col_count > 0:
                        rows = []
                        for row in table:
                            clean_row = [str(c or "").replace("\n", " ").strip() for c in row]
                            rows.append("| " + " | ".join(clean_row) + " |")
                        if rows:
                            header = rows[0]
                            sep = "| " + " | ".join(["---"] * col_count) + " |"
                            p_text_parts.append("\n" + "\n".join([header, sep] + rows[1:]) + "\n")
            text = page.extract_text()
            if text:
                p_text_parts.append(text)
            pages_text.append("\n".join(p_text_parts))
        full_text = "\n\n---\n\n".join(pages_text)
        if len(full_text.strip().splitlines()) > 5:
            os.makedirs(os.path.dirname(os.path.abspath(out_f)), exist_ok=True)
            with open(out_f, "w", encoding="utf-8") as f:
                f.write(full_text)
            sys.exit(0)
except Exception as e:
    pass
sys.exit(1)
' "$INPUT" "$OUTPUT" 2>/dev/null; then
    if has_meaningful_text "$OUTPUT"; then
      heal_section_numbers "$OUTPUT"
      LINES=$(wc -l < "$OUTPUT")
      echo "Done. Extracted $LINES lines (with tables & page anchors) to $OUTPUT" >&2
      exit 0
    fi
  fi
fi

# --- Method 2: pdftotext (poppler-utils) with form-feed page splitting ---
if command -v pdftotext &>/dev/null; then
  echo "Extracting with pdftotext..." >&2
  RAW_TMP=$(mktemp)
  pdftotext -layout "$INPUT" "$RAW_TMP" 2>/dev/null || pdftotext "$INPUT" "$RAW_TMP"
  if has_meaningful_text "$RAW_TMP"; then
    python3 -c '
import sys, re
in_tmp, out_f = sys.argv[1], sys.argv[2]
with open(in_tmp, "r", encoding="utf-8", errors="replace") as f:
    content = f.read()
# Form feed character separates pages in pdftotext
pages = content.split("\x0c")
out_pages = []
for i, page_text in enumerate(pages, start=1):
    cleaned = page_text.strip()
    if cleaned or i < len(pages):
        out_pages.append(f"\n<!-- page: {i} -->\n## Page {i}\n\n{cleaned}")
full = "\n\n---\n\n".join(out_pages).strip() + "\n"
with open(out_f, "w", encoding="utf-8") as f:
    f.write(full)
' "$RAW_TMP" "$OUTPUT"
    rm -f "$RAW_TMP"
    heal_section_numbers "$OUTPUT"
    LINES=$(wc -l < "$OUTPUT")
    echo "Done. Extracted $LINES lines to $OUTPUT" >&2
    exit 0
  else
    rm -f "$RAW_TMP"
    echo "Warning: pdftotext produced little/no text. PDF may be scanned/image-only." >&2
  fi
fi

# --- Method 3: PyMuPDF (fitz) with page anchors ---
if python3 -c "import fitz" &>/dev/null; then
  echo "Trying PyMuPDF..." >&2
  if python3 -c '
import fitz, sys
in_f, out_f = sys.argv[1], sys.argv[2]
doc = fitz.open(in_f)
pages_text = []
for i, page in enumerate(doc, start=1):
    txt = page.get_text().strip()
    pages_text.append(f"\n<!-- page: {i} -->\n## Page {i}\n\n{txt}")
full_text = "\n\n---\n\n".join(pages_text).strip() + "\n"
with open(out_f, "w", encoding="utf-8") as f:
    f.write(full_text)
' "$INPUT" "$OUTPUT" 2>/dev/null; then
    if has_meaningful_text "$OUTPUT"; then
      heal_section_numbers "$OUTPUT"
      LINES=$(wc -l < "$OUTPUT")
      echo "Done. Extracted $LINES lines to $OUTPUT" >&2
      exit 0
    else
      echo "Warning: PyMuPDF produced little/no text. Attempting OCR fallback..." >&2
    fi
  fi
fi

# --- Method 4: OCR via Tesseract + pdftoppm ---
if command -v tesseract &>/dev/null && command -v pdftoppm &>/dev/null; then
  echo "Extracting with OCR (Tesseract)... This may take a while." >&2
  TMPDIR=$(mktemp -d)
  pdftoppm "$INPUT" "$TMPDIR/page" -png
  : > "$OUTPUT"
  PAGE_COUNT=0
  for img in $(ls "$TMPDIR"/page-*.png 2>/dev/null | sort -V); do
    [[ -f "$img" ]] || continue
    PAGE_COUNT=$((PAGE_COUNT + 1))
    echo -e "\n<!-- page: $PAGE_COUNT -->\n## Page $PAGE_COUNT\n" >> "$OUTPUT"
    tesseract "$img" - 2>/dev/null >> "$OUTPUT"
    echo -e "\n---\n" >> "$OUTPUT"
  done
  rm -rf "$TMPDIR"
  if has_meaningful_text "$OUTPUT"; then
    heal_section_numbers "$OUTPUT"
    LINES=$(wc -l < "$OUTPUT")
    echo "Done. OCR extracted $PAGE_COUNT pages, $LINES lines to $OUTPUT" >&2
    exit 0
  else
    echo "Warning: OCR produced little/no text. The PDF may contain non-text content." >&2
  fi
fi

# --- Method 5: MarkItDown fallback ---
if python3 -c "import markitdown" &>/dev/null; then
  echo "Trying MarkItDown fallback..." >&2
  if python3 -c '
import sys
from markitdown import MarkItDown
in_f, out_f = sys.argv[1], sys.argv[2]
md = MarkItDown()
res = md.convert(in_f)
if res and res.markdown and len(res.markdown.strip().splitlines()) > 10:
    with open(out_f, "w", encoding="utf-8") as f:
        f.write(res.markdown)
    sys.exit(0)
sys.exit(1)
' "$INPUT" "$OUTPUT" 2>/dev/null; then
    if has_meaningful_text "$OUTPUT"; then
      heal_section_numbers "$OUTPUT"
      LINES=$(wc -l < "$OUTPUT")
      echo "Done. Extracted $LINES lines to $OUTPUT via MarkItDown" >&2
      exit 0
    fi
  fi
fi

echo "Error: No PDF extraction tool produced readable text." >&2
exit 1
