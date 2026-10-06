#!/usr/bin/env python3
"""
extract_zip.py — Extract ZIP archives to structured Markdown.
Usage: extract_zip.py <input.zip> [output.md]

Features:
1. Safely inspects and extracts archive contents into temporary storage.
2. Filters out system metadata files (__MACOSX, .DS_Store, Thumbs.db, .git).
3. Recursively converts all supported inner files (markdown, text, PDFs, docs, spreadsheets, code, notebooks).
4. Assembles content into a unified Markdown document with '## File: <relative_path>' sections.
5. Cleans up temporary files automatically.
"""

import sys
import os
import zipfile
import tempfile
import subprocess

IGNORE_PATTERNS = {
    "__macosx", ".ds_store", "thumbs.db", ".git", ".idea", ".vscode",
    "node_modules", "__pycache__", ".pytest_cache"
}

TEXT_EXTENSIONS = {
    ".md", ".txt", ".csv", ".tsv", ".json", ".yaml", ".yml",
    ".py", ".sh", ".bash", ".js", ".ts", ".jsx", ".tsx",
    ".css", ".sql", ".rs", ".go", ".c", ".cpp", ".h", ".java", ".xml"
}


def should_ignore(path: str) -> bool:
    parts = path.lower().replace("\\", "/").split("/")
    return any(p in IGNORE_PATTERNS or p.startswith("._") for p in parts)


def convert_zip(input_path: str, output_path: str) -> None:
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    zip_basename = os.path.basename(input_path)
    md_sections = [f"# Archive: {zip_basename}\n"]

    MAX_UNCOMPRESSED_BYTES = 500 * 1024 * 1024  # 500 MB limit
    MAX_FILE_COUNT = 10000

    with tempfile.TemporaryDirectory() as tmpdir:
        real_tmpdir = os.path.realpath(tmpdir)
        total_extracted_bytes = 0
        extracted_file_count = 0

        try:
            with zipfile.ZipFile(input_path, "r") as z:
                for member_info in z.infolist():
                    member = member_info.filename
                    # Reject absolute paths or path traversal
                    target_path = os.path.realpath(os.path.join(tmpdir, member))
                    if not target_path.startswith(real_tmpdir + os.sep) and target_path != real_tmpdir:
                        print(f"Warning: Skipping dangerous zip path: {member}", file=sys.stderr)
                        continue

                    # Reject symlinks (prevent link following attacks)
                    is_symlink = (member_info.external_attr >> 16) & 0o120000 == 0o120000
                    if is_symlink:
                        print(f"Warning: Skipping symlink inside zip: {member}", file=sys.stderr)
                        continue

                    if should_ignore(member):
                        continue

                    # Guard against zip bombs
                    total_extracted_bytes += member_info.file_size
                    extracted_file_count += 1
                    if total_extracted_bytes > MAX_UNCOMPRESSED_BYTES:
                        print("Error: Zip file exceeds maximum uncompressed size ceiling (500MB).", file=sys.stderr)
                        sys.exit(1)
                    if extracted_file_count > MAX_FILE_COUNT:
                        print("Error: Zip file exceeds maximum file count limit (10,000 files).", file=sys.stderr)
                        sys.exit(1)

                    z.extract(member_info, tmpdir)
        except Exception as e:
            print(f"Error reading zip file: {e}", file=sys.stderr)
            sys.exit(1)

        extracted_count = 0

        # Walk extracted directory in sorted order
        for root, _, files in sorted(os.walk(tmpdir)):
            for filename in sorted(files):
                full_file_path = os.path.join(root, filename)
                rel_file_path = os.path.relpath(full_file_path, tmpdir).replace("\\", "/")

                if should_ignore(rel_file_path):
                    continue

                ext = os.path.splitext(filename)[1].lower()

                # Direct text files
                if ext in TEXT_EXTENSIONS:
                    try:
                        with open(full_file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read().strip()
                        if content:
                            md_sections.append(f"## File: {rel_file_path}\n\n{content}\n\n---\n")
                            extracted_count += 1
                    except Exception:
                        pass
                else:
                    # Check if there is an extractor script for this format
                    extractor_map = {
                        ".ipynb": "extract_ipynb.py",
                        ".epub": "extract_epub.py",
                        ".html": "extract_html.py",
                        ".htm": "extract_html.py",
                        ".docx": "extract_docx.sh",
                        ".odt": "extract_docx.sh",
                        ".rtf": "extract_docx.sh",
                        ".pdf": "extract_pdf.sh",
                        ".pptx": "extract_pptx.py",
                        ".xlsx": "extract_xlsx.py",
                        ".xls": "extract_xlsx.py",
                        ".eml": "extract_email.py",
                        ".msg": "extract_email.py",
                    }
                    if ext in extractor_map:
                        script = os.path.join(script_dir, extractor_map[ext])
                        if os.path.exists(script):
                            sub_out = full_file_path + ".extracted.md"
                            cmd = ["python3", script, full_file_path, sub_out] if script.endswith(".py") else ["bash", script, full_file_path, sub_out]
                            try:
                                res = subprocess.run(cmd, capture_output=True, timeout=60)
                                if os.path.exists(sub_out):
                                    with open(sub_out, "r", encoding="utf-8", errors="ignore") as f:
                                        content = f.read().strip()
                                    if content:
                                        md_sections.append(f"## File: {rel_file_path}\n\n{content}\n\n---\n")
                                        extracted_count += 1
                            except Exception:
                                pass

    final_md = "\n".join(md_sections).strip() + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_md)

    lines = len(final_md.splitlines())
    print(f"Done. Extracted {extracted_count} files ({lines} lines) to {output_path}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_zip.py <input.zip> [output.md]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else f"{input_path}.extracted.md"
    convert_zip(input_path, output_path)


if __name__ == "__main__":
    main()
