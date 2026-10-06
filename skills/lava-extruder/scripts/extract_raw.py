#!/usr/bin/env python3
"""
extract_raw.py — Universal Document Extractor for Lava Extruder (Karpathy RAG).
Usage: extract_raw.py <input_file> [output_file]

Universal dispatcher that converts any raw source document in /raw to structured Markdown.
Supported Formats:
- Presentations: .pptx
- Spreadsheets: .xlsx, .xls, .csv, .tsv
- Documents: .pdf, .epub, .docx, .odt, .rtf
- Notebooks: .ipynb
- Web Pages: .html, .htm
- Archives: .zip
- Emails: .msg, .eml
- Audio: .mp3, .wav, .m4a, .mp4, .ogg, .flac
- Images: .png, .jpg, .jpeg, .webp, .tiff, .bmp
- Plain Text: .md, .txt, .json, .yaml, .yml

Architecture:
1. Checks if 'markitdown' is installed and attempts universal conversion.
2. If markitdown is absent or fails, routes to specialized, local-first modular scripts.
3. Automatically sets output to '<input_file>.extracted.md'.
"""

import sys
import os
import shutil
import subprocess
import mimetypes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def format_csv_as_markdown(input_path: str, output_path: str) -> bool:
    """Format CSV / TSV into an aligned Markdown table."""
    import csv
    delimiter = "\t" if input_path.lower().endswith(".tsv") else ","
    rows = []
    try:
        with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for r in reader:
                if any(c.strip() for c in r):
                    rows.append([c.strip().replace("\n", " ") for c in r])
        if not rows:
            return False

        col_count = max(len(r) for r in rows)
        padded = [r + [""] * (col_count - len(r)) for r in rows]
        col_widths = [max(len(str(r[i])) for r in padded) for i in range(col_count)]
        col_widths = [max(w, 3) for w in col_widths]

        lines = [f"# {os.path.splitext(os.path.basename(input_path))[0]}\n"]
        header = padded[0]
        lines.append("| " + " | ".join(header[i].ljust(col_widths[i]) for i in range(col_count)) + " |")
        lines.append("| " + " | ".join("-" * col_widths[i] for i in range(col_count)) + " |")
        for r in padded[1:]:
            lines.append("| " + " | ".join(r[i].ljust(col_widths[i]) for i in range(col_count)) + " |")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return True
    except Exception:
        return False


def try_markitdown(input_path: str, output_path: str) -> bool:
    """Attempt extraction using the markitdown library if installed."""
    try:
        import markitdown
        md = markitdown.MarkItDown()
        result = md.convert(input_path)
        if result and result.markdown and len(result.markdown.strip().splitlines()) > 3:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.markdown.strip() + "\n")
            lines = len(result.markdown.strip().splitlines())
            print(f"Extracted {lines} lines to {output_path} via MarkItDown", file=sys.stderr)
            return True
    except Exception:
        pass
    return False


def run_script(script_name: str, input_path: str, output_path: str) -> bool:
    """Execute a local specialized script in the scripts/ directory."""
    script_path = os.path.join(SCRIPT_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"Error: Required script not found: {script_path}", file=sys.stderr)
        return False

    if script_name.endswith(".py"):
        cmd = [sys.executable, script_path, input_path, output_path]
    else:
        cmd = ["bash", script_path, input_path, output_path]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            if proc.stderr:
                print(proc.stderr.strip(), file=sys.stderr)
            return True
        else:
            if proc.stderr:
                print(proc.stderr.strip(), file=sys.stderr)
            return False
    except Exception as e:
        print(f"Execution error running {script_name}: {e}", file=sys.stderr)
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_raw.py <input_file> [output_file]", file=sys.stderr)
        sys.exit(1)

    input_path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(input_path)[1].lower()
    default_output = f"{input_path}.extracted.md"
    output_path = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else default_output

    print(f"Universal Extractor processing: {os.path.basename(input_path)} ({ext})", file=sys.stderr)

    # 1. Plain text formats that can be formatted or copied directly
    if ext in (".csv", ".tsv"):
        if format_csv_as_markdown(input_path, output_path):
            lines = len(open(output_path).readlines())
            print(f"Done. Extracted {lines} lines to {output_path} (CSV table)", file=sys.stderr)
            sys.exit(0)

    if ext in (".md", ".txt", ".json", ".yaml", ".yml"):
        shutil.copyfile(input_path, output_path)
        lines = len(open(output_path, "r", encoding="utf-8", errors="ignore").readlines())
        print(f"Done. Copied {lines} lines to {output_path} (direct read)", file=sys.stderr)
        sys.exit(0)

    # 2. Try MarkItDown first if installed
    if try_markitdown(input_path, output_path):
        sys.exit(0)

    # 3. Route to specialized local modular converters
    success = False

    if ext == ".pdf":
        success = run_script("extract_pdf.sh", input_path, output_path)
    elif ext == ".epub":
        success = run_script("extract_epub.py", input_path, output_path)
    elif ext in (".docx", ".odt", ".rtf"):
        success = run_script("extract_docx.sh", input_path, output_path)
    elif ext == ".pptx":
        success = run_script("extract_pptx.py", input_path, output_path)
    elif ext in (".xlsx", ".xls"):
        success = run_script("extract_xlsx.py", input_path, output_path)
    elif ext == ".ipynb":
        success = run_script("extract_ipynb.py", input_path, output_path)
    elif ext in (".html", ".htm"):
        success = run_script("extract_html.py", input_path, output_path)
    elif ext == ".zip":
        success = run_script("extract_zip.py", input_path, output_path)
    elif ext in (".eml", ".msg"):
        success = run_script("extract_email.py", input_path, output_path)
    elif ext in (".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"):
        success = run_script("extract_image.sh", input_path, output_path)
    elif ext in (".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".flac"):
        success = run_script("extract_audio.py", input_path, output_path)
    else:
        # Unknown extension: attempt mime-type check or plain text read
        mime, _ = mimetypes.guess_type(input_path)
        if mime and mime.startswith("text/"):
            shutil.copyfile(input_path, output_path)
            success = True
        else:
            print(f"Error: Unsupported file format '{ext}' for file: {input_path}", file=sys.stderr)
            sys.exit(1)

    if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        lines = len(open(output_path, "r", encoding="utf-8", errors="ignore").readlines())
        print(f"Done. Successfully extracted {lines} lines to {output_path}", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"Error: Extraction failed for {input_path}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
