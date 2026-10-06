#!/usr/bin/env bash
# extract_docx.sh — Extract text from DOCX, ODT, or RTF files
# Usage: extract_docx.sh <input_file> [output.md]
#
# Pipeline:
# 1. pandoc (if available)
# 2. mammoth (Python library for clean semantic DOCX to Markdown)
# 3. python-docx (Python library fallback for DOCX)
# 4. LibreOffice headless conversion (handles DOCX, ODT, RTF)

set -euo pipefail

INPUT="${1:?Usage: extract_docx.sh <input_file> [output.md]}"
OUTPUT="${2:-${INPUT}.extracted.md}"

if [[ ! -f "$INPUT" ]]; then
  echo "Error: File not found: $INPUT" >&2
  exit 1
fi

EXT="${INPUT##*.}"
EXT="${EXT,,}"

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
  if pandoc "$INPUT" -t markdown --wrap=none -o "$OUTPUT" 2>/dev/null; then
    LINES=$(wc -l < "$OUTPUT" 2>/dev/null || echo 0)
    if [[ "$LINES" -gt 5 ]]; then
      echo "Done. Extracted $LINES lines to $OUTPUT" >&2
      exit 0
    fi
  fi
fi

# --- Method 2: mammoth (DOCX only, clean semantic markdown) ---
if [[ "$EXT" == "docx" ]] && python3 -c "import mammoth" &>/dev/null; then
  echo "Extracting .docx with mammoth..." >&2
  if python3 -c '
import mammoth, sys, re
in_f, out_f = sys.argv[1], sys.argv[2]
with open(in_f, "rb") as docx_file:
    result = mammoth.convert_to_html(docx_file)
    html = result.value
    # Convert simple html to markdown
    try:
        import markdownify
        md = markdownify.markdownify(html, heading_style="ATX")
    except ImportError:
        # Fallback strip
        md = re.sub(r"<h([1-6])>(.*?)</h\1>", r"\n\n# \2\n\n", html)
        md = re.sub(r"<p>(.*?)</p>", r"\n\n\1\n", md)
        md = re.sub(r"<[^>]+>", "", md)
    with open(out_f, "w", encoding="utf-8") as f:
        f.write(md.strip() + "\n")
sys.exit(0)
' "$INPUT" "$OUTPUT" 2>/dev/null; then
    LINES=$(wc -l < "$OUTPUT" 2>/dev/null || echo 0)
    if [[ "$LINES" -gt 5 ]]; then
      echo "Done. Extracted $LINES lines to $OUTPUT via mammoth" >&2
      exit 0
    fi
  fi
fi

# --- Method 3: python-docx (DOCX only) ---
if [[ "$EXT" == "docx" ]] && python3 -c "import docx" &>/dev/null; then
  echo "Extracting .docx with python-docx..." >&2
  if python3 -c '
import docx, sys
in_f, out_f = sys.argv[1], sys.argv[2]
doc = docx.Document(in_f)
md_lines = []
for p in doc.paragraphs:
    t = p.text.strip()
    if not t:
        continue
    if p.style.name.startswith("Heading 1"):
        md_lines.append(f"# {t}")
    elif p.style.name.startswith("Heading 2"):
        md_lines.append(f"## {t}")
    elif p.style.name.startswith("Heading 3"):
        md_lines.append(f"### {t}")
    else:
        md_lines.append(t)

for table in doc.tables:
    rows = []
    for r in table.rows:
        rows.append([c.text.strip().replace("\n", " ") for c in r.cells])
    if rows:
        header = rows[0]
        md_lines.append("\n| " + " | ".join(header) + " |")
        md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        for r in rows[1:]:
            md_lines.append("| " + " | ".join(r) + " |")
        md_lines.append("")

with open(out_f, "w", encoding="utf-8") as f:
    f.write("\n\n".join(md_lines) + "\n")
' "$INPUT" "$OUTPUT" 2>/dev/null; then
    LINES=$(wc -l < "$OUTPUT" 2>/dev/null || echo 0)
    if [[ "$LINES" -gt 5 ]]; then
      echo "Done. Extracted $LINES lines to $OUTPUT via python-docx" >&2
      exit 0
    fi
  fi
fi

# --- Method 4: libreoffice (headless conversion) ---
if command -v libreoffice &>/dev/null; then
  echo "Extracting .$EXT with LibreOffice headless..." >&2
  TMPDIR=$(mktemp -d)
  if libreoffice --headless --convert-to txt:"Text" --outdir "$TMPDIR" "$INPUT" &>/dev/null; then
    BASENAME=$(basename "${INPUT%.*}")
    if [[ -f "$TMPDIR/$BASENAME.txt" ]]; then
      mv "$TMPDIR/$BASENAME.txt" "$OUTPUT"
      LINES=$(wc -l < "$OUTPUT" 2>/dev/null || echo 0)
      rm -rf "$TMPDIR"
      echo "Done. Extracted $LINES lines to $OUTPUT via LibreOffice" >&2
      exit 0
    fi
  fi
  rm -rf "$TMPDIR"
fi

# --- None succeeded ---
echo "Error: No document extraction tool found or extraction failed for .$EXT" >&2
echo "Install one of the following:" >&2
echo "  sudo apt-get install -y pandoc       # pandoc (recommended)" >&2
echo "  pip install mammoth                  # mammoth (for .docx)" >&2
echo "  sudo apt-get install -y libreoffice  # LibreOffice fallback" >&2
exit 1
