#!/usr/bin/env python3
"""
extract_html.py — Convert saved HTML web pages to clean, structured Markdown.
Usage: extract_html.py <input.html> [output.md]

Features:
1. Strips noisy web elements (<script>, <style>, <nav>, <footer>, <header>, <aside>, <svg>, <iframe>).
2. Preserves semantic document structure: headings, lists, tables, blockquotes, code blocks, links, image alt text.
3. Uses markdownify / BeautifulSoup4 if installed, with a zero-dependency HTMLParser fallback.
4. Reduces LLM token bloat by up to 80-90% compared to raw HTML while retaining critical information.
"""

import sys
import os
import re
from html.parser import HTMLParser


def clean_html_string(raw_html: str) -> str:
    """Pre-strip script, style, navigation, and boilerplate tags."""
    # Remove script and style tags
    cleaned = re.sub(r"<(script|style|noscript|svg|iframe)[^>]*>.*?</\1>", "", raw_html, flags=re.DOTALL | re.IGNORECASE)
    # Remove header, footer, nav, aside blocks that usually contain UI boilerplate
    cleaned = re.sub(r"<(nav|footer|aside)[^>]*>.*?</\1>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    # Replace inline base64 image data strings to avoid megabyte-long lines while preserving img tag
    cleaned = re.sub(r'src=["\']data:image/[^;]+;base64,[A-Za-z0-9+/=]+["\']', 'src="inline-image-data"', cleaned)
    return cleaned


class FallbackHtmlToMarkdown(HTMLParser):
    """Zero-dependency HTML to Markdown parser preserving text, tables, links, and images."""

    def __init__(self):
        super().__init__()
        self.result = []
        self.list_stack = []
        self.in_pre = False
        self.in_code = False
        self.in_table = False
        self.table_rows = []
        self.current_row = []
        self.current_cell = []
        self.current_link = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attr_dict = dict(attrs)

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
        elif tag == "a":
            href = attr_dict.get("href", "")
            if href and not href.startswith("javascript:"):
                self.current_link = href
                self.result.append("[")
        elif tag == "img":
            alt = attr_dict.get("alt", "").strip() or "Image"
            src = attr_dict.get("src", "").strip()
            self.result.append(f" ![{alt}]({src}) ")
        elif tag == "figcaption":
            self.result.append("\n*Caption: ")

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
        elif tag == "a":
            if self.current_link:
                self.result.append(f"]({self.current_link})")
                self.current_link = None
        elif tag == "figcaption":
            self.result.append("*\n")

    def handle_data(self, data):
        if self.in_table:
            self.current_cell.append(data)
        else:
            self.result.append(data)

    def get_markdown(self) -> str:
        raw = "".join(self.result)
        clean = re.sub(r"\n{3,}", "\n\n", raw).strip()
        return clean


def convert_html(input_path: str, output_path: str) -> None:
    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    raw_html = ""
    for enc in ("utf-8", "latin-1"):
        try:
            with open(input_path, "r", encoding=enc, errors="replace") as f:
                raw_html = f.read()
            break
        except Exception:
            continue

    if not raw_html:
        print(f"Error: Could not read file: {input_path}", file=sys.stderr)
        sys.exit(1)

    preprocessed = clean_html_string(raw_html)

    # 1. Try markdownify
    try:
        import markdownify
        md = markdownify.markdownify(
            preprocessed,
            heading_style="ATX",
            strip=["script", "style", "nav", "footer", "header", "aside"]
        )
        if md and len(md.strip().splitlines()) > 3:
            final_md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_md)
            lines = len(final_md.splitlines())
            print(f"Done. Extracted {lines} lines to {output_path} (markdownify)", file=sys.stderr)
            return
    except Exception:
        pass

    # 2. Try BeautifulSoup
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(preprocessed, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        parser = FallbackHtmlToMarkdown()
        parser.feed(str(soup))
        md = parser.get_markdown()
        if md and len(md.splitlines()) > 3:
            final_md = md + "\n"
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(final_md)
            lines = len(final_md.splitlines())
            print(f"Done. Extracted {lines} lines to {output_path} (BeautifulSoup + parser)", file=sys.stderr)
            return
    except Exception:
        pass

    # 3. Fallback standard library parser
    parser = FallbackHtmlToMarkdown()
    parser.feed(preprocessed)
    md = parser.get_markdown()
    final_md = (md if md else "# Document (No readable text found)") + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_md)
    lines = len(final_md.splitlines())
    print(f"Done. Extracted {lines} lines to {output_path} (Standard library parser)", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_html.py <input.html> [output.md]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else f"{input_path}.extracted.md"
    convert_html(input_path, output_path)


if __name__ == "__main__":
    main()
