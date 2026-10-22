#!/usr/bin/env python3
"""
extract_pptx.py — Extract PowerPoint presentations (.pptx) to clean Markdown.
Usage: extract_pptx.py <input.pptx> [output.md]

Features:
1. Extracts slide titles, bullet points, numbered lists, and paragraph text.
2. Formats tables into aligned GitHub-Flavored Markdown.
3. Formats embedded charts (categories and series data) into Markdown tables.
4. Extracts speaker notes and detects hidden slides.
5. Captures image shapes and visual element anchors.
"""

import sys
import os

try:
    import pptx
    from pptx.enum.shapes import MSO_SHAPE_TYPE
except ImportError:
    pptx = None


def convert_table_to_markdown(table) -> str:
    """Convert a PPTX Table shape into a Markdown table."""
    rows = []
    for row in table.rows:
        row_text = []
        for cell in row.cells:
            text = cell.text.strip().replace("\n", " ")
            row_text.append(text)
        if any(row_text):
            rows.append(row_text)

    if not rows:
        return ""

    col_count = max(len(r) for r in rows)
    padded_rows = [r + [""] * (col_count - len(r)) for r in rows]

    col_widths = [max(len(str(r[i])) for r in padded_rows) for i in range(col_count)]
    col_widths = [max(w, 3) for w in col_widths]

    md_lines = []
    header = padded_rows[0]
    md_lines.append("| " + " | ".join(header[i].ljust(col_widths[i]) for i in range(col_count)) + " |")
    md_lines.append("| " + " | ".join("-" * col_widths[i] for i in range(col_count)) + " |")

    for row in padded_rows[1:]:
        md_lines.append("| " + " | ".join(row[i].ljust(col_widths[i]) for i in range(col_count)) + " |")

    return "\n".join(md_lines)


def convert_chart_to_markdown(chart) -> str:
    """Extract chart title, categories, and series data into a Markdown table."""
    md_lines = []
    title = "Chart Data"
    if chart.has_title and chart.chart_title.has_text_frame:
        title = chart.chart_title.text_frame.text.strip() or title
    md_lines.append(f"**{title}**\n")

    try:
        categories = [c.label for c in chart.plots[0].categories] if chart.plots else []
        series = chart.series
        if not categories or not series:
            return ""

        header = ["Category"] + [s.name or f"Series {i+1}" for i, s in enumerate(series)]
        rows = [header]

        for cat_idx, cat in enumerate(categories):
            row = [str(cat)]
            for s in series:
                val = s.values[cat_idx] if cat_idx < len(s.values) else ""
                row.append(str(val) if val is not None else "")
            rows.append(row)

        col_count = len(header)
        col_widths = [max(len(str(r[i])) for r in rows) for i in range(col_count)]
        col_widths = [max(w, 3) for w in col_widths]

        md_table = []
        md_table.append("| " + " | ".join(rows[0][i].ljust(col_widths[i]) for i in range(col_count)) + " |")
        md_table.append("| " + " | ".join("-" * col_widths[i] for i in range(col_count)) + " |")
        for r in rows[1:]:
            md_table.append("| " + " | ".join(r[i].ljust(col_widths[i]) for i in range(col_count)) + " |")

        md_lines.append("\n".join(md_table))
        return "\n".join(md_lines)
    except Exception:
        return ""


def convert_pptx(input_path: str, output_path: str) -> None:
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    if pptx is None:
        print("Error: python-pptx is not installed.", file=sys.stderr)
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

        is_hidden = False
        try:
            if slide._element.get("show") == "0":
                is_hidden = True
        except Exception:
            pass

        hidden_prefix = "[Hidden Slide] " if is_hidden else ""
        if slide_title:
            title_header = f"## Slide {slide_idx}: {hidden_prefix}{slide_title}"
        else:
            title_header = f"## Slide {slide_idx}{(' (' + hidden_prefix.strip() + ')') if is_hidden else ''}"

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

            # Pictures / Images
            try:
                if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    name = getattr(shape, "name", "") or f"Image on Slide {slide_idx}"
                    slide_content.append(f"![{name}](slide-{slide_idx}-image)")
                    return
            except Exception:
                pass

            # Text frames (skip title shape as it is already in the header)
            if shape.has_text_frame and shape != title_shape:
                for para in shape.text_frame.paragraphs:
                    text = para.text.strip()
                    if text:
                        indent = "  " * (para.level or 0)
                        bullet = f"{indent}- {text}" if para.level > 0 else text
                        slide_content.append(bullet)

            # Group shapes
            try:
                if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                    for subshape in shape.shapes:
                        extract_shape(subshape)
            except Exception:
                pass

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
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
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
