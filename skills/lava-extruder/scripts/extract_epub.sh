#!/usr/bin/env bash
# extract_epub.sh — Extract text from an EPUB file
# Usage: extract_epub.sh <input.epub> [output.md]
#
# Tries pandoc first, falls back to python ebooklib.
# Output is structured markdown with chapter headings.

set -euo pipefail

INPUT="${1:?Usage: extract_epub.sh <input.epub> [output.md]}"
OUTPUT="${2:-${INPUT}.extracted.md}"

if [[ ! -f "$INPUT" ]]; then
  echo "Error: File not found: $INPUT" >&2
  exit 1
fi

# --- Method 1: pandoc ---
if command -v pandoc &>/dev/null; then
  echo "Extracting with pandoc..." >&2
  pandoc "$INPUT" -t markdown --wrap=none -o "$OUTPUT"
  LINES=$(wc -l < "$OUTPUT")
  echo "Done. Extracted $LINES lines to $OUTPUT" >&2
  exit 0
fi

# --- Method 2: ebooklib (pip install EbookLib) ---
if python3 -c "import ebooklib" &>/dev/null; then
  echo "pandoc not found, falling back to ebooklib..." >&2
  python3 << 'PYEOF'
import ebooklib
from ebooklib import epub
from html.parser import HTMLParser
import sys, os

class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
    def handle_data(self, data):
        self.result.append(data)
    def get_text(self):
        return ''.join(self.result)

input_path = sys.argv[1]
output_path = sys.argv[2]

book = epub.read_epub(input_path)
chapter_count = 0

with open(output_path, 'w', encoding='utf-8') as f:
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        extractor = TextExtractor()
        extractor.feed(item.get_content().decode('utf-8', errors='ignore'))
        text = extractor.get_text().strip()
        if text:
            chapter_count += 1
            f.write(f'# {item.get_name()}\n\n')
            f.write(text)
            f.write('\n\n---\n\n')

print(f'Done. Extracted {chapter_count} chapters to {output_path}', file=sys.stderr)
PYEOF
  exit 0
fi

# --- Neither available ---
echo "Error: No EPUB extraction tool found." >&2
echo "Install one of the following:" >&2
echo "  sudo apt-get install -y pandoc   # pandoc" >&2
echo "  pip install EbookLib             # python fallback" >&2
exit 1
