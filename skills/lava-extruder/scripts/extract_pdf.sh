#!/usr/bin/env bash
# extract_pdf.sh — Extract text from a PDF file
# Usage: extract_pdf.sh <input.pdf> [output.txt]
#
# Tries pdftotext first, falls back to PyMuPDF (fitz), then OCR via Tesseract.
# Automatically detects scanned/image-only PDFs and attempts OCR.
# Inserts "--- PAGE BREAK ---" markers between pages for chunking.

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

# --- Method 1: pdftotext (poppler-utils) ---
if command -v pdftotext &>/dev/null; then
  echo "Extracting with pdftotext..." >&2
  pdftotext "$INPUT" "$OUTPUT"
  if has_meaningful_text "$OUTPUT"; then
    LINES=$(wc -l < "$OUTPUT")
    echo "Done. Extracted $LINES lines to $OUTPUT" >&2
    exit 0
  else
    echo "Warning: pdftotext produced little/no text. PDF may be scanned/image-only." >&2
  fi
fi

# --- Method 2: PyMuPDF (pip install PyMuPDF) ---
if python3 -c "import fitz" &>/dev/null; then
  echo "Trying PyMuPDF..." >&2
  python3 -c "
import fitz, sys
doc = fitz.open('$INPUT')
with open('$OUTPUT', 'w', encoding='utf-8') as f:
    for i, page in enumerate(doc):
        f.write(page.get_text())
        if i < len(doc) - 1:
            f.write('\n--- PAGE BREAK ---\n')
print(f'Extracted {len(doc)} pages', file=sys.stderr)
"
  if has_meaningful_text "$OUTPUT"; then
    LINES=$(wc -l < "$OUTPUT")
    echo "Done. Extracted $LINES lines to $OUTPUT" >&2
    exit 0
  else
    echo "Warning: PyMuPDF produced little/no text. Attempting OCR fallback..." >&2
  fi
fi

# --- Method 3: OCR via Tesseract + pdftoppm ---
if command -v tesseract &>/dev/null && command -v pdftoppm &>/dev/null; then
  echo "Extracting with OCR (Tesseract)... This may take a while." >&2
  TMPDIR=$(mktemp -d)
  pdftoppm "$INPUT" "$TMPDIR/page" -png
  : > "$OUTPUT"  # truncate output
  PAGE_COUNT=0
  for img in "$TMPDIR"/page-*.png; do
    [[ -f "$img" ]] || continue
    tesseract "$img" - 2>/dev/null >> "$OUTPUT"
    echo -e "\n--- PAGE BREAK ---\n" >> "$OUTPUT"
    PAGE_COUNT=$((PAGE_COUNT + 1))
  done
  rm -rf "$TMPDIR"
  if has_meaningful_text "$OUTPUT"; then
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
echo "  pip install PyMuPDF                                   # PyMuPDF" >&2
echo "  sudo apt-get install -y tesseract-ocr poppler-utils  # OCR fallback" >&2
exit 1
