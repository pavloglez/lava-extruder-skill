#!/usr/bin/env python3
"""
extract_epub.py — Extract EPUB books to clean, structured Markdown.
Usage: extract_epub.py <input.epub> [output.md]

Zero external dependencies required (uses Python standard library zipfile and xml.dom.minidom).
Features:
1. Extracts Dublin Core book metadata (title, author, publisher, date, description).
2. Follows official EPUB Spine (<itemref>) for guaranteed chronological chapter order.
3. Converts XHTML chapters to clean Markdown (headings, lists, tables, formatting).
4. Inserts '--- PAGE BREAK ---' markers between chapters for segmented chunking.
"""

import sys
import os
import zipfile
import re
import shutil
import subprocess
from xml.dom import minidom
from html.parser import HTMLParser


def _get_node_text(element) -> str:
    """Extract all text inside an XML DOM node."""
    text_parts = []
    for child in element.childNodes:
        if child.nodeType in (child.TEXT_NODE, child.CDATA_SECTION_NODE):
            if child.nodeValue:
                text_parts.append(child.nodeValue)
        elif child.hasChildNodes():
            text_parts.append(_get_node_text(child))
    return "".join(text_parts).strip()


class SimpleHtmlToMarkdown(HTMLParser):
    """
    Lightweight HTML/XHTML to Markdown converter without third-party dependencies.
    Converts headers, lists, links, emphasis, blockquotes, tables, and code.
    """

    def __init__(self):
        super().__init__()
        self.result = []
        self.list_stack = []  # ('ul' | 'ol', count)
        self.in_pre = False
        self.in_code = False
        self.in_table = False
        self.table_rows = []
        self.current_row = []
        self.current_cell = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        tag = tag.lower()

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.result.append(f"\n\n{'#' * level} ")
        elif tag == "p":
            self.result.append("\n\n")
        elif tag == "br":
            self.result.append("\n")
        elif tag in ("b", "strong"):
            self.result.append("**")
        elif tag in ("i", "em"):
            self.result.append("*")
        elif tag == "code":
            if not self.in_pre:
                self.result.append("`")
                self.in_code = True
        elif tag == "pre":
            self.in_pre = True
            self.result.append("\n\n```\n")
        elif tag == "blockquote":
            self.result.append("\n\n> ")
        elif tag == "ul":
            self.list_stack.append(("ul", 0))
            self.result.append("\n")
        elif tag == "ol":
            self.list_stack.append(("ol", 1))
            self.result.append("\n")
        elif tag == "li":
            indent = "  " * (len(self.list_stack) - 1) if self.list_stack else ""
            if self.list_stack and self.list_stack[-1][0] == "ol":
                idx = self.list_stack[-1][1]
                self.result.append(f"\n{indent}{idx}. ")
                self.list_stack[-1] = ("ol", idx + 1)
            else:
                self.result.append(f"\n{indent}- ")
        elif tag == "table":
            self.in_table = True
            self.table_rows = []
        elif tag == "tr":
            self.current_row = []
        elif tag in ("td", "th"):
            self.current_cell = []
        elif tag == "hr":
            self.result.append("\n\n---\n\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("b", "strong"):
            self.result.append("**")
        elif tag in ("i", "em"):
            self.result.append("*")
        elif tag == "code":
            if self.in_code and not self.in_pre:
                self.result.append("`")
                self.in_code = False
        elif tag == "pre":
            self.in_pre = False
            self.result.append("\n```\n\n")
        elif tag in ("ul", "ol"):
            if self.list_stack:
                self.list_stack.pop()
            self.result.append("\n")
        elif tag in ("td", "th"):
            cell_text = "".join(self.current_cell).strip().replace("\n", " ")
            self.current_row.append(cell_text)
        elif tag == "tr":
            if self.current_row:
                self.table_rows.append(self.current_row)
        elif tag == "table":
            self.in_table = False
            if self.table_rows:
                # Render table to markdown
                col_count = max(len(r) for r in self.table_rows)
                formatted_rows = []
                for row in self.table_rows:
                    padded = row + [""] * (col_count - len(row))
                    formatted_rows.append("| " + " | ".join(padded) + " |")
                if formatted_rows:
                    header = formatted_rows[0]
                    separator = "| " + " | ".join(["---"] * col_count) + " |"
                    rest = formatted_rows[1:]
                    table_md = "\n\n" + "\n".join([header, separator] + rest) + "\n\n"
                    self.result.append(table_md)

    def handle_data(self, data):
        if self.in_table:
            self.current_cell.append(data)
        else:
            self.result.append(data)

    def get_markdown(self) -> str:
        raw = "".join(self.result)
        # Collapse excessive newlines
        clean = re.sub(r"\n{3,}", "\n\n", raw).strip()
        return clean


def html_to_markdown(html_str: str) -> str:
    """Convert HTML string to markdown using markdownify if available, else stdlib parser."""
    # Remove script and style tags first
    html_str = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_str, flags=re.DOTALL | re.IGNORECASE)

    try:
        import markdownify
        return markdownify.markdownify(html_str, heading_style="ATX").strip()
    except ImportError:
        pass

    parser = SimpleHtmlToMarkdown()
    parser.feed(html_str)
    return parser.get_markdown()


def convert_epub(input_path: str, output_path: str) -> None:
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        z = zipfile.ZipFile(input_path, "r")
    except Exception as e:
        if shutil.which("pandoc"):
            print(f"Notice: Stdlib zip reader failed ({e}). Falling back to pandoc...", file=sys.stderr)
            res = subprocess.run(["pandoc", input_path, "-t", "markdown", "--wrap=none", "-o", output_path], capture_output=True)
            if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                lines = len(open(output_path, "r", encoding="utf-8", errors="ignore").readlines())
                print(f"Done. Extracted {lines} lines to {output_path} via pandoc fallback", file=sys.stderr)
                return
        print(f"Error opening EPUB as zip: {e}", file=sys.stderr)
        sys.exit(1)

    with z:
        # 1. Locate content.opf from META-INF/container.xml
        try:
            container_bytes = z.read("META-INF/container.xml")
            container_dom = minidom.parseString(container_bytes)
            rootfile_nodes = container_dom.getElementsByTagName("rootfile")
            if not rootfile_nodes:
                raise ValueError("No rootfile tag found in META-INF/container.xml")
            opf_path = rootfile_nodes[0].getAttribute("full-path")
        except Exception as e:
            print(f"Error locating rootfile: {e}. Searching for .opf directly...", file=sys.stderr)
            opf_candidates = [n for n in z.namelist() if n.endswith(".opf")]
            if not opf_candidates:
                print("Error: No .opf file found in EPUB archive.", file=sys.stderr)
                sys.exit(1)
            opf_path = opf_candidates[0]

        # 2. Parse OPF metadata & spine
        try:
            opf_bytes = z.read(opf_path)
            opf_dom = minidom.parseString(opf_bytes)
        except Exception as e:
            print(f"Error reading OPF file {opf_path}: {e}", file=sys.stderr)
            sys.exit(1)

        # Extract metadata
        def get_all(tag: str) -> list[str]:
            nodes = opf_dom.getElementsByTagName(tag)
            return [_get_node_text(n) for n in nodes if _get_node_text(n)]

        title = (get_all("dc:title") or ["Untitled"])[0]
        creators = get_all("dc:creator")
        language = (get_all("dc:language") or [""])[0]
        publisher = (get_all("dc:publisher") or [""])[0]
        date = (get_all("dc:date") or [""])[0]
        description = (get_all("dc:description") or [""])[0]

        # Extract Manifest (id -> href)
        manifest = {}
        for item in opf_dom.getElementsByTagName("item"):
            item_id = item.getAttribute("id")
            href = item.getAttribute("href")
            if item_id and href:
                manifest[item_id] = href

        # Extract Spine (reading order)
        spine_items = opf_dom.getElementsByTagName("itemref")
        spine_idrefs = [item.getAttribute("idref") for item in spine_items if item.getAttribute("idref")]

        # Resolve paths relative to OPF base directory
        opf_dir = os.path.dirname(opf_path)
        chapter_files = []
        for idref in spine_idrefs:
            if idref in manifest:
                rel_path = manifest[idref]
                # Normalize relative path
                if opf_dir:
                    full_path = os.path.normpath(os.path.join(opf_dir, rel_path)).replace("\\", "/")
                else:
                    full_path = rel_path
                chapter_files.append(full_path)

        # Fallback if spine was empty: find HTML/XHTML items in manifest
        if not chapter_files:
            for item in opf_dom.getElementsByTagName("item"):
                mtype = item.getAttribute("media-type")
                if mtype in ("application/xhtml+xml", "text/html"):
                    rel = item.getAttribute("href")
                    full = os.path.normpath(os.path.join(opf_dir, rel)).replace("\\", "/") if opf_dir else rel
                    chapter_files.append(full)

        # 3. Build Markdown document
        sections = []

        # Metadata Header
        meta_lines = [f"# {title}", ""]
        if creators:
            meta_lines.append(f"**Author(s):** {', '.join(creators)}")
        if publisher:
            meta_lines.append(f"**Publisher:** {publisher}")
        if date:
            meta_lines.append(f"**Date:** {date}")
        if language:
            meta_lines.append(f"**Language:** {language}")
        if description:
            meta_lines.append(f"\n> {description.strip()}\n")
        meta_lines.append("\n---\n")
        sections.append("\n".join(meta_lines))

        # Extract each chapter
        extracted_chapters = 0
        for ch_path in chapter_files:
            if ch_path not in z.namelist():
                # Try case-insensitive lookup
                lower_map = {n.lower(): n for n in z.namelist()}
                ch_path = lower_map.get(ch_path.lower(), ch_path)

            if ch_path not in z.namelist():
                continue

            try:
                raw_bytes = z.read(ch_path)
                try:
                    ch_html = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    ch_html = raw_bytes.decode("latin-1", errors="ignore")

                ch_md = html_to_markdown(ch_html)
                if ch_md.strip():
                    sections.append(ch_md)
                    sections.append("\n--- PAGE BREAK ---\n")
                    extracted_chapters += 1
            except Exception as e:
                print(f"Warning: Failed to extract chapter {ch_path}: {e}", file=sys.stderr)

        final_md = "\n\n".join(sections).strip()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_md + "\n")

        line_count = len(final_md.splitlines())
        print(f"Done. Extracted '{title}' ({extracted_chapters} chapters, {line_count} lines) to {output_path}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_epub.py <input.epub> [output.md]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else f"{input_path}.extracted.md"
    convert_epub(input_path, output_path)


if __name__ == "__main__":
    main()
