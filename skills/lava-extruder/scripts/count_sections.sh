#!/usr/bin/env bash
# count_sections.sh — Count structural markers in a text file
# Usage: count_sections.sh <input_file>
#
# Outputs total lines, section count, and a list of all structural
# markers with line numbers. Useful for building a chunking plan.

set -euo pipefail

INPUT="${1:?Usage: count_sections.sh <input_file>}"

if [[ ! -f "$INPUT" ]]; then
  echo "Error: File not found: $INPUT" >&2
  exit 1
fi

TOTAL_LINES=$(wc -l < "$INPUT")
FILENAME=$(basename "$INPUT")

echo "=== File Manifest: $FILENAME ==="
echo "Total lines: $TOTAL_LINES"
echo ""

# Extended structural marker regex:
# - Markdown headings (# through ######)
# - Horizontal rules (---)
# - Chapter/Part markers (various cases)
# - Page break markers from PDF extraction
# - Numbered sections (1. , 1.1 , Section 1)
# - Roman numeral chapters (I. , II. , III. , etc.)
PATTERN="^#{1,6} |^---$|^Chapter |^CHAPTER |^Part |^PART |^--- PAGE BREAK ---$|^Section [0-9]|^SECTION [0-9]|^[0-9]+\.[0-9]* |^[IVXLC]+\.\s"

# Count structural markers
SECTIONS=$(grep -cE "$PATTERN" "$INPUT" 2>/dev/null || echo "0")
echo "Structural markers found: $SECTIONS"
echo ""

# Determine if chunking is needed
if [[ "$TOTAL_LINES" -gt 2000 ]]; then
  CHUNKS=$(( (TOTAL_LINES + 699) / 700 ))
  echo "⚠  File exceeds 2,000 lines — chunked reading required."
  echo "   Recommended chunks: ~$CHUNKS (at ~700 lines each)"
else
  echo "✓  File is under 2,000 lines — single-pass reading is fine."
fi

echo ""
echo "=== Structural Markers ==="
grep -nE "$PATTERN" "$INPUT" 2>/dev/null || echo "(none found)"
