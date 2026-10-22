#!/usr/bin/env python3
"""
ledger.py — Section-level coverage ledger and deterministic verification gate.
Usage:
  ledger.py init <extracted_file> [ledger_output]
  ledger.py check <vault_dir> [--source <raw_rel_path>]
  ledger.py sync-source <vault_dir> <raw_rel_path>

Deterministic Checks:
- No empty targets.
- Skips must provide explicit justification.
- Target articles must exist in /wiki/.
- Target articles must list the source in frontmatter sources:.
- Line coverage must be complete without gaps.
- Recall heuristic (WARN): highlights numbers, dates, and named entities missing from target articles.
"""

import sys
import os
import re
import datetime
from pathlib import Path

SECTION_MARKER_RE = re.compile(
    r"^(?:<!--\s*page:\s*(\d+)\s*-->|#{1,6}\s+(.+)|---\s*PAGE\s*BREAK\s*---|##\s*Slide\s*(\d+).*|##\s*File:\s*(.+)|##\s*Rows\s+(\d+.*))$",
    re.M
)

LEDGER_ROW_RE = re.compile(
    r"^\s*\|\s*(S\d+)\s*\|\s*(\d+)-(\d+)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|\s*$"
)
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[^\]]*)\]\]")


def find_vault_root(path: str) -> str:
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


def parse_frontmatter(text: str) -> tuple:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    body = m.group(1)
    fm = {}
    for line in body.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            fm[k] = [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()] if inner else []
        else:
            fm[k] = v.strip('"').strip("'")
    return fm, text[m.end():]


def init_ledger(extracted_path: str, ledger_path: str = None) -> int:
    extracted_path = os.path.abspath(extracted_path)
    if not os.path.isfile(extracted_path):
        print(f"Error: Extracted file not found: {extracted_path}", file=sys.stderr)
        return 1

    vault_root = find_vault_root(extracted_path)
    if not ledger_path:
        if vault_root:
            rel = os.path.relpath(extracted_path, os.path.join(vault_root, "runs", "extracted"))
            if not rel.startswith(".."):
                ledger_path = os.path.join(vault_root, "runs", "ledger", rel)
        if not ledger_path:
            ledger_path = extracted_path + ".ledger.md"

    with open(extracted_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    total_lines = len(lines)
    if total_lines == 0:
        print(f"Warning: {extracted_path} is empty.", file=sys.stderr)
        return 1

    # Find structural markers
    marker_indices = []  # list of (line_idx_0_based, heading_label)
    for i, line in enumerate(lines):
        line_str = line.strip()
        m = SECTION_MARKER_RE.match(line_str)
        if m:
            label = m.group(2) or m.group(4) or m.group(5) or (f"Page {m.group(1)}" if m.group(1) else "") or (f"Slide {m.group(3)}" if m.group(3) else "") or line_str
            clean_label = label.replace("|", "-").strip()
            marker_indices.append((i, clean_label))

    # Break into bounded sections (~150-500 lines)
    sections = []
    if not marker_indices:
        # Fallback: slice every 150 lines
        step = 150
        for start in range(0, total_lines, step):
            end = min(start + step, total_lines)
            sections.append((start + 1, end, f"Lines {start + 1} to {end}"))
    else:
        # Build sections between markers
        current_start = 0
        current_heading = "Preamble / Frontmatter"
        for idx, heading in marker_indices:
            if idx > current_start:
                sections.append((current_start + 1, idx, current_heading))
            current_start = idx
            current_heading = heading
        if current_start < total_lines:
            sections.append((current_start + 1, total_lines, current_heading))

    os.makedirs(os.path.dirname(os.path.abspath(ledger_path)), exist_ok=True)
    basename = os.path.basename(extracted_path)
    out = [
        f"# Coverage Ledger: {basename}\n",
        f"Source: `{extracted_path}`",
        f"Total Lines: {total_lines}",
        f"Total Sections: {len(sections)}\n",
        "| ID | Lines | Heading | Target | Note |",
        "|---|---|---|---|---|"
    ]

    for idx, (start_l, end_l, h) in enumerate(sections, start=1):
        s_id = f"S{idx:03d}"
        clean_h = h.replace("\n", " ").strip()
        out.append(f"| {s_id} | {start_l}-{end_l} | {clean_h} | | |")

    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")

    print(f"Created coverage ledger with {len(sections)} sections at: {ledger_path}")
    return 0


def collect_article_titles(vault_root: Path) -> dict:
    """Map link targets (title, heading, stem) to article Path."""
    wiki_dir = vault_root / "wiki"
    titles = {}
    if not wiki_dir.is_dir():
        return titles

    for p in wiki_dir.rglob("*.md"):
        if p.name.startswith("_"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm, _ = parse_frontmatter(text)
        candidates = [p.stem]
        if fm.get("title"):
            candidates.append(str(fm["title"]).strip())
        # Add aliases from frontmatter if present
        aliases = fm.get("aliases", [])
        if isinstance(aliases, list):
            candidates.extend(str(a).strip() for a in aliases if a)
        elif isinstance(aliases, str):
            candidates.append(aliases.strip())
        # First H1
        m = re.search(r"^#\s+(.+)$", text, re.M)
        if m:
            candidates.append(m.group(1).strip())
        # Relative path under wiki/
        rel = str(p.relative_to(wiki_dir)).removesuffix(".md").replace("\\", "/")
        candidates.append(rel)

        for c in candidates:
            titles[c.lower()] = p
    return titles


def extract_salient_tokens(text: str) -> set:
    """Extract numbers, percentages, dates, and capitalized named entities for recall heuristic."""
    tokens = set()
    # Numbers with decimals or percentages (e.g. 84.5%, 2026, 150)
    for m in re.finditer(r"\b\d+(?:\.\d+)?%?", text):
        val = m.group(0)
        if len(val) >= 2:  # ignore single digits 0-9
            tokens.add(val)
    # Capitalized entity phrases on the same line (e.g. Paxos Protocol, Raft Algorithm)
    for m in re.finditer(r"\b[A-Z][a-z]{2,}(?:[ \t]+[A-Z][a-z]{2,})+\b", text):
        tokens.add(m.group(0).strip())
    return tokens


def check_ledger(vault_dir: str, specific_source: str = None) -> int:
    vault_root = Path(vault_dir).resolve()
    if not vault_root.is_dir():
        print(f"Error: Vault directory not found: {vault_root}", file=sys.stderr)
        return 1

    ledger_dir = vault_root / "runs" / "ledger"
    if not ledger_dir.is_dir():
        print(f"Notice: No ledger directory found at {ledger_dir}. Vault has no active ledgers.", file=sys.stderr)
        return 0

    known_articles = collect_article_titles(vault_root)
    errors = []
    warnings = []

    ledger_files = list(ledger_dir.rglob("*.md"))
    if specific_source:
        clean_spec = Path(specific_source).name.removesuffix(".extracted.md").removesuffix(".md")
        ledger_files = [lf for lf in ledger_files if clean_spec.lower() in lf.name.lower()]

    if not ledger_files:
        if specific_source:
            errors.append(f"No ledger found matching source: {specific_source}")
        else:
            print("Notice: No ledger files in runs/ledger/.", file=sys.stderr)
            return 0

    for lf in ledger_files:
        try:
            content = lf.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            errors.append(f"Could not read ledger {lf}: {e}")
            continue

        # Extract source path if specified in header
        raw_source_match = re.search(r"Source:\s*`([^`]+)`", content)
        raw_source_path = raw_source_match.group(1).strip() if raw_source_match else ""

        # Find corresponding extracted file to check line coverage & text tokens
        extracted_content_lines = []
        if raw_source_path and os.path.exists(raw_source_path):
            try:
                with open(raw_source_path, "r", encoding="utf-8", errors="replace") as ef:
                    extracted_content_lines = ef.readlines()
            except OSError:
                pass

        rows = []
        for line in content.splitlines():
            m = LEDGER_ROW_RE.match(line)
            if m:
                rows.append((m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).strip(), m.group(5).strip(), m.group(6).strip()))

        if not rows:
            errors.append(f"Ledger {lf.name} has no valid table rows.")
            continue

        # 1. Contiguity & completeness check
        last_end = 0
        for s_id, start_l, end_l, heading, target, note in rows:
            if start_l > last_end + 1 and last_end != 0:
                errors.append(f"[{lf.name} {s_id}] Unmapped line gap detected between line {last_end} and {start_l}")
            last_end = max(last_end, end_l)

            # 2. Target check
            if not target:
                errors.append(f"[{lf.name} {s_id}] Empty Target for section '{heading}' (lines {start_l}-{end_l})")
                continue

            # 3. Skip check
            if target.lower() in ("skip", "skipped", "ignore", "ignored", "none"):
                if not note:
                    errors.append(f"[{lf.name} {s_id}] Target is '{target}' but Note is empty (justification required).")
                continue

            # 4. Resolve wiki articles in Target
            targets = WIKILINK_RE.findall(target)
            if not targets:
                # Target is plain text without [[ ]]
                targets = [target.strip()]

            target_article_texts = []
            for t in targets:
                t_clean = t.strip().lower()
                target_path = known_articles.get(t_clean)
                if not target_path or not target_path.exists():
                    errors.append(f"[{lf.name} {s_id}] Target article [[{t}]] not found in wiki/")
                else:
                    try:
                        art_text = target_path.read_text(encoding="utf-8", errors="replace")
                        target_article_texts.append(art_text)
                        # Check sources: frontmatter in target article
                        if raw_source_path:
                            fm, _ = parse_frontmatter(art_text)
                            sources_list = fm.get("sources", [])
                            if isinstance(sources_list, str):
                                sources_list = [sources_list]
                            # Check if relative raw path or source filename is cited
                            source_base = os.path.basename(raw_source_path).removesuffix(".extracted.md").removesuffix(".md")
                            found_source = any(source_base.lower() in str(s).lower() for s in sources_list)
                            if not found_source:
                                errors.append(f"[{lf.name} {s_id}] Target article [[{t}]] does not list '{source_base}' in frontmatter sources: list")
                    except OSError:
                        pass

            # 5. Recall heuristic (WARN)
            if extracted_content_lines and target_article_texts:
                section_text = "".join(extracted_content_lines[start_l - 1 : end_l])
                salient = extract_salient_tokens(section_text)
                combined_targets = "\n".join(target_article_texts)
                missing = [tok for tok in salient if tok not in combined_targets]
                if missing:
                    sample_missing = missing[:3]
                    warnings.append(
                        f"[{lf.name} {s_id}] Recall heuristic: section '{heading}' tokens {sample_missing} not found in target [[{targets[0]}]]"
                    )

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        print(f"\n❌ Ledger check failed with {len(errors)} error(s), {len(warnings)} warning(s).", file=sys.stderr)
        return min(len(errors), 255)

    print(f"✅ Ledger check clean — all sections accounted for ({len(warnings)} warning(s)).")
    return 0


def sync_source_note(vault_dir: str, raw_rel_path: str) -> int:
    vault_root = Path(vault_dir).resolve()
    slug = Path(raw_rel_path).stem
    source_note_path = vault_root / "wiki" / "sources" / f"{slug}.md"
    source_note_path.parent.mkdir(parents=True, exist_ok=True)

    today = datetime.date.today().isoformat()

    # Find matching ledger
    ledger_file = vault_root / "runs" / "ledger" / f"{Path(raw_rel_path).name}.md"
    if not ledger_file.exists():
        ledger_file = vault_root / "runs" / "ledger" / f"{Path(raw_rel_path).name}.extracted.md"
    if not ledger_file.exists():
        # Search by stem
        candidates = list((vault_root / "runs" / "ledger").rglob(f"*{slug}*.md"))
        if candidates:
            ledger_file = candidates[0]

    coverage_rows = []
    if ledger_file.exists():
        content = ledger_file.read_text(encoding="utf-8", errors="replace")
        for line in content.splitlines():
            m = LEDGER_ROW_RE.match(line)
            if m:
                s_id, _, _, heading, target, note = m.group(1), m.group(2), m.group(3), m.group(4).strip(), m.group(5).strip(), m.group(6).strip()
                coverage_rows.append(f"| {s_id} | {heading} | {target} | {note} |")

    table_lines = [
        "| Section | Heading | Target Article | Notes |",
        "|---|---|---|---|"
    ] + (coverage_rows if coverage_rows else ["| S001 | All Content | *(Pending ledger)* | |"])

    table_block = "<!-- ledger:start -->\n" + "\n".join(table_lines) + "\n<!-- ledger:end -->"

    if source_note_path.exists():
        old_text = source_note_path.read_text(encoding="utf-8", errors="replace")
        if "<!-- ledger:start -->" in old_text and "<!-- ledger:end -->" in old_text:
            new_text = re.sub(r"<!-- ledger:start -->.*?<!-- ledger:end -->", table_block, old_text, flags=re.DOTALL)
        else:
            new_text = old_text + "\n\n## Coverage Map\n" + table_block + "\n"
        source_note_path.write_text(new_text, encoding="utf-8")
        print(f"Updated source note at {source_note_path}")
    else:
        new_text = f"""---
title: "Source: {Path(raw_rel_path).name}"
created: {today}
updated: {today}
tags: [source]
sources: ["{raw_rel_path}"]
type: source
---

# Source: {Path(raw_rel_path).name}

## Metadata
- **File:** `{raw_rel_path}`
- **Extracted:** `runs/extracted/{Path(raw_rel_path).name}.md`
- **Ledger:** `runs/ledger/{Path(raw_rel_path).name}.md`

## Summary
<!-- Add 2-3 bullet executive summary of source content -->

## Coverage Map
{table_block}

## Outbound Links
- [[_master-index]]
"""
        source_note_path.write_text(new_text, encoding="utf-8")
        print(f"Created source note at {source_note_path}")

    return 0


def main():
    if len(sys.argv) < 2:
        print("Usage: ledger.py <init|check|sync-source> [args...]", file=sys.stderr)
        return 2

    cmd = sys.argv[1].lower()
    if cmd == "init":
        if len(sys.argv) < 3:
            print("Usage: ledger.py init <extracted_file> [ledger_output]", file=sys.stderr)
            return 2
        return init_ledger(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "check":
        if len(sys.argv) < 3:
            print("Usage: ledger.py check <vault_dir> [--source <raw_rel_path>]", file=sys.stderr)
            return 2
        vault_dir = sys.argv[2]
        source = None
        if len(sys.argv) >= 5 and sys.argv[3] == "--source":
            source = sys.argv[4]
        return check_ledger(vault_dir, source)
    elif cmd == "sync-source":
        if len(sys.argv) < 4:
            print("Usage: ledger.py sync-source <vault_dir> <raw_rel_path>", file=sys.stderr)
            return 2
        return sync_source_note(sys.argv[2], sys.argv[3])
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
