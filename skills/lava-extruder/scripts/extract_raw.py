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
1. Detects vault root; outputs to '<vault>/runs/extracted/<relpath>.md' to isolate from '/raw'.
2. Prioritizes structure-preserving specialized converters over general tools.
3. Attaches YAML manifest frontmatter (sha256, source, extractor, warnings).
4. Employs MarkItDown and plain-text fallbacks if specialized converters fail.
"""

import sys
import os
import shutil
import subprocess
import mimetypes
import hashlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_vault_root(path: str) -> str:
    """Walk up from path looking for SCHEMA.md to identify vault root."""
    curr = os.path.abspath(path)
    if os.path.isfile(curr):
        curr = os.path.dirname(curr)
    while True:
        if os.path.exists(os.path.join(curr, "SCHEMA.md")):
            return curr
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    return ""


def determine_default_output(input_path: str) -> str:
    """If input is in a vault's /raw folder, output to /runs/extracted/. Otherwise <file>.extracted.md."""
    abs_input = os.path.abspath(input_path)
    vault_root = find_vault_root(abs_input)
    if vault_root:
        raw_dir = os.path.join(vault_root, "raw")
        try:
            rel = os.path.relpath(abs_input, raw_dir)
            if not rel.startswith(".."):
                target = os.path.join(vault_root, "runs", "extracted", f"{rel}.md")
                os.makedirs(os.path.dirname(target), exist_ok=True)
                return target
        except ValueError:
            pass
    return f"{abs_input}.extracted.md"


def sha256_of_file(path: str) -> str:
    """Return hex sha256 digest of a file, streamed in chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def prepend_manifest(output_path: str, source_path: str, extractor_name: str, warnings: list = None, units: dict = None):
    """Ensure output markdown has a YAML frontmatter manifest."""
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return
    try:
        with open(output_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception:
        return

    # Check if manifest frontmatter already exists
    if content.startswith("---\n") and "extractor:" in content[:500]:
        return

    vault_root = find_vault_root(source_path)
    if vault_root:
        rel_source = os.path.relpath(os.path.abspath(source_path), vault_root).replace("\\", "/")
    else:
        rel_source = os.path.basename(source_path)

    file_hash = sha256_of_file(source_path)
    warnings_list = warnings or []
    units_dict = units or {}

    mf_lines = [
        "---",
        f"source: \"{rel_source}\"",
        f"sha256: \"{file_hash}\"",
        f"extractor: \"{extractor_name}\"",
    ]
    if units_dict:
        units_str = ", ".join(f"{k}: {v}" for k, v in units_dict.items())
        mf_lines.append(f"units: {{{units_str}}}")
    if warnings_list:
        mf_lines.append("warnings:")
        for w in warnings_list:
            clean_w = str(w).replace('"', '\\"')
            mf_lines.append(f"  - \"{clean_w}\"")
    else:
        mf_lines.append("warnings: []")
    mf_lines.append("---\n\n")

    manifest_block = "\n".join(mf_lines)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(manifest_block + content.lstrip("\n"))


def format_csv_as_markdown(input_path: str, output_path: str) -> tuple:
    """Format CSV / TSV into an aligned Markdown table without truncation."""
    import csv
    delimiter = "\t" if input_path.lower().endswith(".tsv") else ","
    rows = []
    replace_count = 0
    warnings = []

    try:
        with open(input_path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter=delimiter)
            for r in reader:
                if any(c.strip() for c in r):
                    clean_row = []
                    for c in r:
                        if "\ufffd" in c:
                            replace_count += c.count("\ufffd")
                        clean_row.append(c.strip().replace("\n", " "))
                    rows.append(clean_row)
    except Exception as e:
        return False, [f"CSV parse error: {e}"]

    if not rows:
        return False, ["CSV empty or whitespace only"]

    if replace_count > 0:
        warnings.append(f"{replace_count} undecodable byte(s) replaced with U+FFFD")

    col_count = max(len(r) for r in rows)
    padded = [r + [""] * (col_count - len(r)) for r in rows]
    col_widths = [max(len(str(r[i])) for r in padded) for i in range(col_count)]
    col_widths = [max(w, 3) for w in col_widths]

    out = [f"# {os.path.splitext(os.path.basename(input_path))[0]}\n"]
    header = padded[0]
    header_str = "| " + " | ".join(header[i].ljust(col_widths[i]) for i in range(col_count)) + " |"
    sep = "| " + " | ".join("-" * col_widths[i] for i in range(col_count)) + " |"

    CHUNK_SIZE = 5000
    data_rows = padded[1:]
    if len(data_rows) <= CHUNK_SIZE:
        out.append(header_str)
        out.append(sep)
        for r in data_rows:
            out.append("| " + " | ".join(r[i].ljust(col_widths[i]) for i in range(col_count)) + " |")
    else:
        for idx in range(0, len(data_rows), CHUNK_SIZE):
            chunk = data_rows[idx : idx + CHUNK_SIZE]
            out.append(f"\n## Rows {idx + 1} to {idx + len(chunk)}\n")
            out.append(header_str)
            out.append(sep)
            for r in chunk:
                out.append("| " + " | ".join(r[i].ljust(col_widths[i]) for i in range(col_count)) + " |")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    return True, warnings


def try_markitdown(input_path: str, output_path: str) -> bool:
    """Attempt extraction using the markitdown library if installed."""
    try:
        import markitdown
        md = markitdown.MarkItDown()
        result = md.convert(input_path)
        if result and result.markdown and len(result.markdown.strip().splitlines()) > 3:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
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

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

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


def copy_text_with_replace(input_path: str, output_path: str) -> tuple:
    """Copy text file handling encoding errors gracefully and counting replacements."""
    replace_count = 0
    warnings = []
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(input_path, "r", encoding="utf-8", errors="replace") as fin:
        text = fin.read()
        replace_count = text.count("\ufffd")
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(text)
    if replace_count > 0:
        warnings.append(f"{replace_count} undecodable byte(s) replaced with U+FFFD")
    return True, warnings


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_raw.py <input_file> [output_file]", file=sys.stderr)
        sys.exit(1)

    input_path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(input_path)[1].lower()
    output_path = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else determine_default_output(input_path)

    print(f"Universal Extractor processing: {os.path.basename(input_path)} ({ext})", file=sys.stderr)

    used_extractor = "raw"
    warnings = []

    # 1. Plain text formats
    if ext in (".csv", ".tsv"):
        success, warn = format_csv_as_markdown(input_path, output_path)
        if success:
            warnings.extend(warn)
            prepend_manifest(output_path, input_path, "csv-table", warnings)
            lines = sum(1 for _ in open(output_path, "r", encoding="utf-8", errors="ignore"))
            print(f"Done. Extracted {lines} lines to {output_path} (CSV table)", file=sys.stderr)
            sys.exit(0)

    if ext in (".md", ".txt", ".json", ".yaml", ".yml"):
        success, warn = copy_text_with_replace(input_path, output_path)
        if success:
            warnings.extend(warn)
            prepend_manifest(output_path, input_path, "direct-read", warnings)
            lines = sum(1 for _ in open(output_path, "r", encoding="utf-8", errors="ignore"))
            print(f"Done. Copied {lines} lines to {output_path} (direct read)", file=sys.stderr)
            sys.exit(0)

    # 2. Prioritize specialized converters that preserve layout & structure
    success = False

    if ext == ".pdf":
        used_extractor = "extract_pdf.sh"
        success = run_script("extract_pdf.sh", input_path, output_path)
    elif ext == ".epub":
        used_extractor = "extract_epub.py"
        success = run_script("extract_epub.py", input_path, output_path)
    elif ext in (".docx", ".odt", ".rtf"):
        used_extractor = "extract_docx.sh"
        success = run_script("extract_docx.sh", input_path, output_path)
    elif ext == ".pptx":
        used_extractor = "extract_pptx.py"
        success = run_script("extract_pptx.py", input_path, output_path)
    elif ext in (".xlsx", ".xls"):
        used_extractor = "extract_xlsx.py"
        success = run_script("extract_xlsx.py", input_path, output_path)
    elif ext == ".ipynb":
        used_extractor = "extract_ipynb.py"
        success = run_script("extract_ipynb.py", input_path, output_path)
    elif ext in (".html", ".htm"):
        used_extractor = "extract_html.py"
        success = run_script("extract_html.py", input_path, output_path)
    elif ext == ".zip":
        used_extractor = "extract_zip.py"
        success = run_script("extract_zip.py", input_path, output_path)
    elif ext in (".eml", ".msg"):
        used_extractor = "extract_email.py"
        success = run_script("extract_email.py", input_path, output_path)
    elif ext in (".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"):
        used_extractor = "extract_image.sh"
        success = run_script("extract_image.sh", input_path, output_path)
    elif ext in (".mp3", ".wav", ".m4a", ".mp4", ".ogg", ".flac"):
        used_extractor = "extract_audio.py"
        success = run_script("extract_audio.py", input_path, output_path)

    # 3. Fallback to MarkItDown if specialized converter failed
    if not success:
        if try_markitdown(input_path, output_path):
            used_extractor = "markitdown"
            success = True

    # 4. Unknown extension: check mime-type
    if not success and ext not in (
        ".pdf", ".epub", ".docx", ".odt", ".rtf", ".pptx", ".xlsx",
        ".xls", ".ipynb", ".html", ".htm", ".zip", ".eml", ".msg",
        ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp", ".mp3",
        ".wav", ".m4a", ".mp4", ".ogg", ".flac"
    ):
        mime, _ = mimetypes.guess_type(input_path)
        if mime and mime.startswith("text/"):
            success, warn = copy_text_with_replace(input_path, output_path)
            used_extractor = "mime-text"
            warnings.extend(warn)

    if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
        prepend_manifest(output_path, input_path, used_extractor, warnings)
        lines = sum(1 for _ in open(output_path, "r", encoding="utf-8", errors="ignore"))
        print(f"Done. Successfully extracted {lines} lines to {output_path}", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"Error: Extraction failed for {input_path}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
