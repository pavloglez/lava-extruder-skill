#!/usr/bin/env bash
# extract_pdf.sh — Extract text & tables from a PDF file
# Usage: extract_pdf.sh <input.pdf> [output.txt]
#
# Extraction pipeline:
# 1. Table-Aware Extraction (via MarkItDown or pdfplumber if available)
# 2. pdftotext (poppler-utils) — high-speed extraction with layout preservation
# 3. PyMuPDF (fitz) — fast python fallback
# 4. OCR via Tesseract + pdftoppm — automatic fallback for scanned/image-only PDFs
#
# Inserts "--- PAGE BREAK ---" markers between pages for chunking.
# Heals broken partial section numbers (.1\nSection -> .1 Section).

set -euo pipefail

INPUT="${1:?Usage: extract_pdf.sh <input.pdf> [output.txt]}"
OUTPUT="${2:-${INPUT}.extracted.txt}"

if [[ ! -f "$INPUT" ]]; then
  echo "Error: File not found: $INPUT" >&2
  exit 1
fi

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
with open(target, "r", encoding="utf-8", errors="ignore") as f:
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

# --- Method 1: MarkItDown / pdfplumber (Table & form layout preservation) ---
if python3 -c "import markitdown" &>/dev/null; then
  echo "Extracting PDF with markitdown (structured tables & text)..." >&2
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
      echo "Done. Extracted $LINES lines (with tables) to $OUTPUT" >&2
      exit 0
    fi
  fi
elif python3 -c "import pdfplumber" &>/dev/null; then
  echo "Extracting PDF with pdfplumber (table-aware)..." >&2
  if python3 -c '
import pdfplumber, sys
in_f, out_f = sys.argv[1], sys.argv[2]
with pdfplumber.open(in_f) as pdf:
    pages_text = []
    for i, page in enumerate(pdf.pages):
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
                        pages_text.append("\n" + "\n".join([header, sep] + rows[1:]) + "\n")
        text = page.extract_text()
        if text:
            pages_text.append(text)
        if i < len(pdf.pages) - 1:
            pages_text.append("\n--- PAGE BREAK ---\n")
    full_text = "\n".join(pages_text)
    if len(full_text.strip().splitlines()) > 10:
        with open(out_f, "w", encoding="utf-8") as f:
            f.write(full_text)
        sys.exit(0)
    sys.exit(1)
' "$INPUT" "$OUTPUT" 2>/dev/null; then
    if has_meaningful_text "$OUTPUT"; then
      heal_section_numbers "$OUTPUT"
      LINES=$(wc -l < "$OUTPUT")
      echo "Done. Extracted $LINES lines to $OUTPUT" >&2
      exit 0
    fi
  fi
fi

# --- Method 2: pdftotext (poppler-utils) ---
if command -v pdftotext &>/dev/null; then
  echo "Extracting with pdftotext..." >&2
  pdftotext -layout "$INPUT" "$OUTPUT" 2>/dev/null || pdftotext "$INPUT" "$OUTPUT"
  if has_meaningful_text "$OUTPUT"; then
    heal_section_numbers "$OUTPUT"
    LINES=$(wc -l < "$OUTPUT")
    echo "Done. Extracted $LINES lines to $OUTPUT" >&2
    exit 0
  else
    echo "Warning: pdftotext produced little/no text. PDF may be scanned/image-only." >&2
  fi
fi

# --- Method 3: PyMuPDF (pip install PyMuPDF) ---
if python3 -c "import fitz" &>/dev/null; then
  echo "Trying PyMuPDF..." >&2
  python3 -c '
import fitz, sys
in_f, out_f = sys.argv[1], sys.argv[2]
doc = fitz.open(in_f)
with open(out_f, "w", encoding="utf-8") as f:
    for i, page in enumerate(doc):
        f.write(page.get_text())
        if i < len(doc) - 1:
            f.write("\n--- PAGE BREAK ---\n")
print(f"Extracted {len(doc)} pages", file=sys.stderr)
' "$INPUT" "$OUTPUT"
  if has_meaningful_text "$OUTPUT"; then
    heal_section_numbers "$OUTPUT"
    LINES=$(wc -l < "$OUTPUT")
    echo "Done. Extracted $LINES lines to $OUTPUT" >&2
    exit 0
  else
    echo "Warning: PyMuPDF produced little/no text. Attempting OCR fallback..." >&2
  fi
fi

# --- Method 4: OCR via Tesseract + pdftoppm ---
if command -v tesseract &>/dev/null && command -v pdftoppm &>/dev/null; then
  echo "Extracting with OCR (Tesseract)... This may take a while." >&2
  TMPDIR=$(mktemp -d)
  pdftoppm "$INPUT" "$TMPDIR/page" -png
  : > "$OUTPUT"
  PAGE_COUNT=0
  for img in "$TMPDIR"/page-*.png; do
    [[ -f "$img" ]] || continue
    tesseract "$img" - 2>/dev/null >> "$OUTPUT"
    echo -e "\n--- PAGE BREAK ---\n" >> "$OUTPUT"
    PAGE_COUNT=$((PAGE_COUNT + 1))
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

# --- No method succeeded ---
echo "Error: No PDF extraction tool produced readable text." >&2
echo "Install one or more of the following:" >&2
echo "  sudo apt-get install -y poppler-utils                # pdftotext" >&2
echo "  pip install markitdown                              # Table & Markdown support" >&2
echo "  pip install PyMuPDF                                 # PyMuPDF" >&2
echo "  sudo apt-get install -y tesseract-ocr poppler-utils  # OCR fallback" >&2
exit 1
