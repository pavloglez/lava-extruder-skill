#!/usr/bin/env python3
"""
extract_email.py — Extract Outlook (.msg) and standard (.eml) emails to Markdown.
Usage: extract_email.py <input_file> [output.md]

Features:
1. Supports Outlook .msg files (via olefile) and standard .eml files (via Python stdlib email).
2. Extracts email metadata: Subject, From, To, Cc, Date.
3. Extracts plain text message body or converts HTML body to Markdown.
4. Lists attachments names and sizes.
"""

import sys
import os
import email
from email import policy
import re


def convert_eml(input_path: str, output_path: str) -> None:
    """Convert standard RFC 822 .eml file to Markdown using standard library email."""
    with open(input_path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    subject = msg.get("Subject", "No Subject")
    from_addr = msg.get("From", "Unknown")
    to_addr = msg.get("To", "Unknown")
    date_str = msg.get("Date", "")
    cc_addr = msg.get("Cc", "")

    md_lines = [
        f"# {subject}\n",
        f"- **From:** {from_addr}",
        f"- **To:** {to_addr}",
    ]
    if cc_addr:
        md_lines.append(f"- **Cc:** {cc_addr}")
    if date_str:
        md_lines.append(f"- **Date:** {date_str}")

    # Extract body and attachments
    body_text = ""
    html_body = ""
    attachments = []

    for part in msg.walk():
        content_disposition = part.get_content_disposition()
        if content_disposition == "attachment":
            filename = part.get_filename() or "unnamed_attachment"
            payload = part.get_payload(decode=True)
            size = len(payload) if payload else 0
            attachments.append(f"{filename} ({size} bytes)")
        elif part.get_content_type() == "text/plain":
            body_text += part.get_content()
        elif part.get_content_type() == "text/html":
            html_body += part.get_content()

    md_lines.append("\n---\n")
    md_lines.append("## Message Content\n")

    if body_text.strip():
        md_lines.append(body_text.strip())
    elif html_body.strip():
        # Clean HTML body
        clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_body, flags=re.DOTALL | re.IGNORECASE)
        clean_text = re.sub(r"<[^>]+>", " ", clean)
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        md_lines.append(clean_text)
    else:
        md_lines.append("*(No text body in email)*")

    if attachments:
        md_lines.append("\n\n### Attachments\n")
        for att in attachments:
            md_lines.append(f"- {att}")

    final_md = "\n".join(md_lines).strip() + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_md)

    lines = len(final_md.splitlines())
    print(f"Done. Extracted {lines} lines to {output_path} (.eml)", file=sys.stderr)


def convert_msg(input_path: str, output_path: str) -> None:
    """Convert Outlook .msg file to Markdown using olefile."""
    try:
        import olefile
    except ImportError:
        print("Error: olefile is required to read Outlook .msg files.", file=sys.stderr)
        print("Install it with: pip install olefile", file=sys.stderr)
        sys.exit(1)

    ole = olefile.OleFileIO(input_path)

    def read_stream(stream_path: str) -> str:
        try:
            if ole.exists(stream_path):
                data = ole.openstream(stream_path).read()
                try:
                    return data.decode("utf-16-le").strip()
                except UnicodeDecodeError:
                    return data.decode("utf-8", errors="ignore").strip()
        except Exception:
            pass
        return ""

    # Outlook MAPI property streams
    subject = read_stream("__substg1.0_0037001F") or read_stream("__substg1.0_0037001E") or "No Subject"
    from_addr = read_stream("__substg1.0_0C1F001F") or read_stream("__substg1.0_0C1F001E") or "Unknown"
    to_addr = read_stream("__substg1.0_0E04001F") or read_stream("__substg1.0_0E04001E") or "Unknown"
    body = read_stream("__substg1.0_1000001F") or read_stream("__substg1.0_1000001E") or ""

    ole.close()

    md_lines = [
        f"# {subject}\n",
        f"- **From:** {from_addr}",
        f"- **To:** {to_addr}",
        "\n---\n",
        "## Message Content\n",
        body.strip() if body.strip() else "*(No text content extracted)*"
    ]

    final_md = "\n".join(md_lines).strip() + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(final_md)

    lines = len(final_md.splitlines())
    print(f"Done. Extracted {lines} lines to {output_path} (.msg)", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: extract_email.py <input_file> [output.md]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else f"{input_path}.extracted.md"

    if not os.path.isfile(input_path):
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(input_path)[1].lower()
    if ext == ".msg":
        convert_msg(input_path, output_path)
    else:
        convert_eml(input_path, output_path)


if __name__ == "__main__":
    main()
