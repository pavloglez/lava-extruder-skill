#!/usr/bin/env bash
# extract_image.sh — Extract text & metadata from images via OCR
# Usage: extract_image.sh <input_image> [output.md]
#
# Supported: .png, .jpg, .jpeg, .webp, .tiff, .bmp
# Uses:
# - Tesseract OCR for text extraction (whiteboards, screenshots, diagrams)
# - Exiftool / ImageMagick / file for dimension and timestamp metadata

set -euo pipefail

INPUT="${1:?Usage: extract_image.sh <input_image> [output.md]}"
OUTPUT="${2:-${INPUT}.extracted.md}"

if [[ ! -f "$INPUT" ]]; then
  echo "Error: File not found: $INPUT" >&2
  exit 1
fi

BASENAME=$(basename "$INPUT")
TITLE="${BASENAME%.*}"

echo "Extracting image: $BASENAME..." >&2

# 1. Metadata extraction
META=""
if command -v exiftool &>/dev/null; then
  IMAGE_SIZE=$(exiftool -s3 -ImageSize "$INPUT" 2>/dev/null || true)
  CREATE_DATE=$(exiftool -s3 -CreateDate "$INPUT" 2>/dev/null || exiftool -s3 -DateTimeOriginal "$INPUT" 2>/dev/null || true)
  [[ -n "$IMAGE_SIZE" ]] && META+="- **Dimensions:** ${IMAGE_SIZE}\n"
  [[ -n "$CREATE_DATE" ]] && META+="- **Created:** ${CREATE_DATE}\n"
elif command -v identify &>/dev/null; then
  DIMS=$(identify -format "%wx%h" "$INPUT" 2>/dev/null || true)
  [[ -n "$DIMS" ]] && META+="- **Dimensions:** ${DIMS}\n"
fi

FILE_TYPE=$(file -b --mime-type "$INPUT" 2>/dev/null || echo "image")
META+="- **MIME Type:** ${FILE_TYPE}\n"

# 2. OCR Text Extraction via Tesseract
OCR_TEXT=""
if command -v tesseract &>/dev/null; then
  echo "Running Tesseract OCR on $BASENAME..." >&2
  TMP_OCR=$(mktemp)
  tesseract "$INPUT" "$TMP_OCR" 2>/dev/null || true
  if [[ -f "${TMP_OCR}.txt" ]]; then
    OCR_TEXT=$(cat "${TMP_OCR}.txt" | sed '/^[[:space:]]*$/d' || true)
    rm -f "${TMP_OCR}.txt"
  fi
  rm -f "$TMP_OCR"
else
  echo "Notice: Tesseract is not installed. To extract text from images: sudo apt-get install -y tesseract-ocr" >&2
fi

# 3. Assemble Markdown
{
  echo "# Image: ${TITLE}"
  echo ""
  echo -e "$META"
  echo "---"
  echo ""
  echo "## Extracted Text (OCR)"
  echo ""
  if [[ -n "${OCR_TEXT// /}" ]]; then
    echo "$OCR_TEXT"
  else
    echo "*(No text detected via OCR or OCR tool not installed)*"
  fi
} > "$OUTPUT"

LINES=$(wc -l < "$OUTPUT")
echo "Done. Extracted $LINES lines to $OUTPUT" >&2
