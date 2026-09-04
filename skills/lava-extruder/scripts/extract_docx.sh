#!/usr/bin/env bash
# extract_docx.sh — Extract text from DOCX, ODT, or RTF files
# Usage: extract_docx.sh <input_file> [output.md]
#
# Tries pandoc first, falls back to LibreOffice headless conversion.
# Output is structured markdown.

set -euo pipefail

INPUT="${1:?Usage: extract_docx.sh <input_file> [output.md]}"
OUTPUT="${2:-${INPUT}.extracted.md}"

if [[ ! -f "$INPUT" ]]; then
  echo "Error: File not found: $INPUT" >&2
  exit 1
fi

# Detect format from extension
EXT="${INPUT##*.}"
EXT="${EXT,,}"  # lowercase

case "$EXT" in
  docx|odt|rtf)
    ;;
  *)
    echo "Error: Unsupported format '.$EXT'. Supported: .docx, .odt, .rtf" >&2
    exit 1
    ;;
esac

# --- Method 1: pandoc ---
if command -v pandoc &>/dev/null; then
  echo "Extracting .$EXT with pandoc..." >&2
  pandoc "$INPUT" -t markdown --wrap=none -o "$OUTPUT"
  LINES=$(wc -l < "$OUTPUT")
  echo "Done. Extracted $LINES lines to $OUTPUT" >&2
  exit 0
fi

# --- Method 2: libreoffice (headless conversion) ---
if command -v libreoffice &>/dev/null; then
  echo "pandoc not found, falling back to LibreOffice headless..." >&2
  TMPDIR=$(mktemp -d)
  libreoffice --headless --convert-to txt:"Text" --outdir "$TMPDIR" "$INPUT" >&2
  BASENAME=$(basename "${INPUT%.*}")
  if [[ -f "$TMPDIR/$BASENAME.txt" ]]; then
    mv "$TMPDIR/$BASENAME.txt" "$OUTPUT"
    LINES=$(wc -l < "$OUTPUT")
    echo "Done. Extracted $LINES lines to $OUTPUT" >&2
  else
    echo "Error: LibreOffice conversion produced no output." >&2
    rm -rf "$TMPDIR"
    exit 1
  fi
  rm -rf "$TMPDIR"
  exit 0
fi

# --- Neither available ---
echo "Error: No document extraction tool found." >&2
echo "Install one of the following:" >&2
echo "  sudo apt-get install -y pandoc       # pandoc (recommended)" >&2
echo "  sudo apt-get install -y libreoffice  # LibreOffice fallback" >&2
exit 1
