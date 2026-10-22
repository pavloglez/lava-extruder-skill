#!/usr/bin/env python3
"""
extract_ipynb.py — Extract Jupyter Notebook (.ipynb) to clean Markdown without truncation.
Usage: extract_ipynb.py <input.ipynb> [output.md]

Zero external dependencies (uses Python standard library json).
Converts markdown cells directly, wraps code cells in ```python blocks,
and extracts notebook title from metadata or top heading.
Outputs exceeding 1,000 characters are placed into collapsible <details> blocks.
"""

import sys
import os
import json


def convert_ipynb(input_path: str, output_path: str) -> None:
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            notebook = json.load(f)
    except Exception as e:
        print(f"Error reading notebook JSON: {e}", file=sys.stderr)
        sys.exit(1)

    cells = notebook.get("cells", [])
    if not cells:
        print(f"Warning: No cells found in notebook {input_path}", file=sys.stderr)

    metadata = notebook.get("metadata", {})
    nb_title = metadata.get("title")

    md_output = []
    found_title = None

    for cell in cells:
        cell_type = cell.get("cell_type", "")
        source = cell.get("source", [])
        if isinstance(source, list):
            source_text = "".join(source).strip()
        else:
            source_text = str(source).strip()

        if not source_text:
            continue

        if cell_type == "markdown":
            md_output.append(source_text)
            if not found_title:
                for line in source_text.splitlines():
                    line = line.strip()
                    if line.startswith("# "):
                        found_title = line.removeprefix("# ").strip()
                        break

        elif cell_type == "code":
            # Code cell
            code_block = f"```python\n{source_text}\n```"
            md_output.append(code_block)

            # Outputs (e.g. stdout / print statements / execution results)
            outputs = cell.get("outputs", [])
            output_texts = []
            for out in outputs:
                out_type = out.get("output_type", "")
                if out_type == "stream" and "text" in out:
                    t = "".join(out["text"]).strip()
                    if t:
                        output_texts.append(t)
                elif out_type in ("execute_result", "display_data") and "data" in out:
                    data = out["data"]
                    if "text/plain" in data:
                        t = "".join(data["text/plain"]).strip()
                        if t:
                            output_texts.append(t)
            if output_texts:
                combined_out = "\n".join(output_texts)
                if len(combined_out) > 1000:
                    md_output.append(
                        f"> **Output:**\n<details><summary>Click to expand output ({len(combined_out)} chars)</summary>\n\n```\n{combined_out}\n```\n</details>"
                    )
                else:
                    md_output.append(f"> **Output:**\n```\n{combined_out}\n```")

        elif cell_type == "raw":
            md_output.append(f"```\n{source_text}\n```")

    final_content = "\n\n".join(md_output).strip()

    title_to_use = nb_title or found_title or os.path.splitext(os.path.basename(input_path))[0]
    if not final_content.startswith("# "):
        final_content = f"# {title_to_use}\n\n" + final_content

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_content + "\n")

    lines = len(final_content.splitlines())
    print(f"Done. Extracted {len(cells)} cells ({lines} lines) to {output_path}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_ipynb.py <input.ipynb> [output.md]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else f"{input_path}.extracted.md"
    convert_ipynb(input_path, output_path)


if __name__ == "__main__":
    main()
