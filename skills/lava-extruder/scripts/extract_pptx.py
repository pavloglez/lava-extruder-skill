#!/usr/bin/env python3
"""
extract_pptx.py — Extract PowerPoint presentations (.pptx) to structured Markdown.
Usage: extract_pptx.py <input.pptx> [output.md]

Features:
1. Extracts slide titles, bullet points, text boxes, and group shapes.
2. Converts tables to aligned GitHub-Flavored Markdown tables.
3. Converts chart series/categories to Markdown tables.
4. Extracts speaker notes under '### Notes:'.
5. Fallback via LibreOffice headless conversion to PDF if python-pptx is not installed.
"""

import sys
import os
import re
import html
import subprocess
import tempfile


def convert_table_to_markdown(table) -> str:
    """Convert a python-pptx Table object into a GitHub-Flavored Markdown table."""
    rows_data = []
    for row in table.rows:
        row_cells = []
        for cell in row.cells:
            cell_text = cell.text.strip().replace("\n", " ")
            row_cells.append(cell_text)
        rows_data.append(row_cells)

    if not rows_data:
        return ""

    col_count = max(len(r) for r in rows_data)
    md_lines = []
    header = rows_data[0]
    padded_header = header + [""] * (col_count - len(header))
    md_lines.append("| " + " | ".join(padded_header) + " |")
    md_lines.append("| " + " | ".join(["---"] * col_count) + " |")

    for row in rows_data[1:]:
        padded_row = row + [""] * (col_count - len(row))
        md_lines.append("| " + " | ".join(padded_row) + " |")

    return "\n" + "\n".join(md_lines) + "\n\n"


def convert_chart_to_markdown(chart) -> str:
    """Convert a python-pptx Chart object into a Markdown table."""
    try:
        title_str = ""
        if chart.has_title and chart.chart_title.has_text_frame:
            title_str = f": {chart.chart_title.text_frame.text.strip()}"

        categories = [c.label for c in chart.plots[0].categories]
        series_list = list(chart.series)
        series_names = [s.name for s in series_list]

        if not categories or not series_list:
            return f"\n\n### Chart{title_str}\n\n"

        header = ["Category"] + series_names
        rows = [header]

        series_values = [list(s.values) for s in series_list]
        for idx, cat in enumerate(categories):
            row = [str(cat)]
            for s_vals in series_values:
                row.append(str(s_vals[idx]) if idx < len(s_vals) else "")
            rows.append(row)

        col_count = len(header)
        md = [f"\n\n### Chart{title_str}\n"]
        md.append("| " + " | ".join(rows[0]) + " |")
        md.append("| " + " | ".join(["---"] * col_count) + " |")
        for r in rows[1:]:
            md.append("| " + " | ".join(r) + " |")
        return "\n".join(md) + "\n\n"
    except Exception:
        return "\n\n[Chart]\n\n"


def convert_pptx(input_path: str, output_path: str) -> None:
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Check for python-pptx
    try:
        import pptx
    except ImportError:
        # Fallback via LibreOffice headless -> pdf -> pdftotext
        if subprocess.run(["which", "libreoffice"], capture_output=True).returncode == 0:
            print("python-pptx not found. Converting via LibreOffice fallback...", file=sys.stderr)
            with tempfile.TemporaryDirectory() as tmpdir:
                cmd = ["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", tmpdir, input_path]
                res = subprocess.run(cmd, capture_output=True)
                pdf_name = os.path.splitext(os.path.basename(input_path))[0] + ".pdf"
                pdf_path = os.path.join(tmpdir, pdf_name)
                if os.path.exists(pdf_path):
                    txt_cmd = ["pdftotext", "-layout", pdf_path, output_path]
                    subprocess.run(txt_cmd, capture_output=True)
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 10:
                        lines = len(open(output_path, "r", encoding="utf-8", errors="ignore").readlines())
                        print(f"Done. Extracted {lines} lines to {output_path} via LibreOffice", file=sys.stderr)
                        return

        print("Error: python-pptx is required to parse presentations.", file=sys.stderr)
        print("Install it with: pip install python-pptx", file=sys.stderr)
        sys.exit(1)

    prs = pptx.Presentation(input_path)
    deck_title = os.path.splitext(os.path.basename(input_path))[0]
    md_output = [f"# {deck_title}\n"]

    for slide_idx, slide in enumerate(prs.slides, start=1):
        slide_title = None
        title_shape = None
        if slide.shapes.title:
            slide_title = slide.shapes.title.text.strip()
            title_shape = slide.shapes.title

        title_header = f"## Slide {slide_idx}: {slide_title}" if slide_title else f"## Slide {slide_idx}"
        md_output.append(title_header)

        slide_content = []

        def extract_shape(shape):
            nonlocal slide_content
            # Tables
            if shape.has_table:
                table_md = convert_table_to_markdown(shape.table)
                if table_md.strip():
                    slide_content.append(table_md)
                return

            # Charts
            if shape.has_chart:
                chart_md = convert_chart_to_markdown(shape.chart)
                if chart_md.strip():
                    slide_content.append(chart_md)
                return

            # Text frames (skip title shape as it is already in the header)
            if shape.has_text_frame and shape != title_shape:
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if text:
                        indent = "  " * (para.level or 0)
                        bullet = f"{indent}- {text}" if para.level > 0 else text
                        slide_content.append(bullet)

            # Group shapes
            if shape.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.GROUP:
                for subshape in shape.shapes:
                    extract_shape(subshape)

        # Sort shapes top-to-bottom, left-to-right
        sorted_shapes = sorted(
            slide.shapes,
            key=lambda s: (s.top if s.top is not None else float("inf"), s.left if s.left is not None else float("inf"))
        )
        for shape in sorted_shapes:
            extract_shape(shape)

        if slide_content:
            md_output.append("\n".join(slide_content))

        # Speaker notes
        if slide.has_notes_slide:
            notes_frame = slide.notes_slide.notes_text_frame
            if notes_frame and notes_frame.text.strip():
                md_output.append(f"\n### Notes:\n{notes_frame.text.strip()}")

        md_output.append("\n---\n")

    final_md = "\n\n".join(md_output).strip()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_md + "\n")

    lines = len(final_md.splitlines())
    print(f"Done. Extracted {len(prs.slides)} slides ({lines} lines) to {output_path}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_pptx.py <input.pptx> [output.md]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else f"{input_path}.extracted.md"
    convert_pptx(input_path, output_path)


if __name__ == "__main__":
    main()
