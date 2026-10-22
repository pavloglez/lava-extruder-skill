#!/usr/bin/env python3
"""
lint_vault.py — Deterministic vault integrity lint for Lava Extruder vaults.
Usage: lint_vault.py <vault_dir> [--json]

Checks (no LLM needed):
- broken wikilinks               -> ERROR   link target doesn't exist
- orphan articles                -> WARN    wiki page with no inbound [[links]]
- index vs filesystem drift      -> WARN    article on disk missing from topic index / master index
- missing/invalid frontmatter    -> ERROR   missing required fields or bad YAML block
- tags outside taxonomy          -> WARN    tag used but not in SCHEMA.md taxonomy
- articles with <2 outbound links-> WARN    invisible to graph navigation
- oversized articles (>200 lines)-> WARN    candidate for splitting
- stale articles                 -> INFO    updated older than 180 days or stale vs vault
- digested index vs raw files    -> ERROR   raw path missing or sha256 changed since digest
- source notes for digested files-> WARN    digested file missing wiki/sources/ note
- raw folder pollution           -> ERROR   extracted file located in /raw
- coverage ledger errors         -> ERROR   unmapped sections or invalid targets in ledger
- hot.md size >500 words         -> WARN    hot cache grown too large
- index.md/_index.md missing     -> WARN    navigation gaps

Exit code: number of ERROR findings (capped at 255). 0 means clean.
"""

import os
import re
import sys
import json
import hashlib
import datetime
from pathlib import Path
from collections import defaultdict

SEVERITY_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}
REQUIRED_FM = ["title", "created", "updated", "tags", "sources"]
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[^\]]*)\]\]")
HASH_RE = re.compile(r"^\s*\|\s*([^|]+)\s*\|\s*([a-f0-9]{64})\s*\|\s*([^|]*)\s*\|\s*$")


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, text
    body = m.group(1)

    # Try PyYAML if installed
    try:
        import yaml
        parsed = yaml.safe_load(body)
        if isinstance(parsed, dict):
            return parsed, text[m.end():]
    except Exception:
        pass

    # Resilient stdlib YAML fallback parser supporting indented list items
    fm = {}
    current_key = None
    for line in body.splitlines():
        line_s = line.rstrip()
        if not line_s or line_s.strip().startswith("#"):
            continue

        # Indented list item: "  - tag"
        list_match = re.match(r"^\s+-\s+(.+)$", line_s)
        if list_match and current_key:
            item = list_match.group(1).strip().strip('"').strip("'")
            if not isinstance(fm.get(current_key), list):
                fm[current_key] = []
            fm[current_key].append(item)
            continue

        if ":" in line_s:
            key, _, val = line_s.partition(":")
            key = key.strip()
            val = val.strip()
            current_key = key
            if not val:
                fm[key] = []
            elif val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                fm[key] = [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()] if inner else []
            else:
                fm[key] = val.strip('"').strip("'")

    return fm, text[m.end():]


def main():
    if len(sys.argv) < 2:
        print("Usage: lint_vault.py <vault_dir> [--json]", file=sys.stderr)
        sys.exit(2)

    vault_root = Path(sys.argv[1]).resolve()
    as_json = "--json" in sys.argv

    if not vault_root.is_dir():
        print(f"Error: not a directory: {vault_root}", file=sys.stderr)
        sys.exit(2)

    findings = []  # (severity, message, path)

    # --- 0. Check raw folder pollution (no .extracted files inside /raw) ---
    raw_dir = vault_root / "raw"
    if raw_dir.is_dir():
        for p in raw_dir.rglob("*"):
            if p.is_file() and (".extracted." in p.name or p.name.endswith(".extracted.md")):
                findings.append(("ERROR", f"extracted intermediate file found in raw/: {p.name}", str(p)))

    # --- 1. Gather taxonomy from SCHEMA.md ---
    taxonomy = set()
    schema_path = vault_root / "SCHEMA.md"
    if schema_path.exists():
        text = schema_path.read_text(encoding="utf-8", errors="replace")
        in_taxonomy = False
        for line in text.splitlines():
            if "taxonomy" in line.lower():
                in_taxonomy = True
                continue
            if in_taxonomy:
                if line.strip().startswith("#"):
                    break
                m = re.match(r"\s*[-•]\s*(.+)", line)
                if m:
                    tag = m.group(1).strip().strip("`").strip()
                    tag = tag.split(",")[0]
                    if tag:
                        taxonomy.add(tag.lower())

    # --- 2. Index all markdown files in vault ---
    wiki_dir = vault_root / "wiki"
    articles = {}       # path -> (frontmatter, raw_text)
    index_files = {}    # path -> raw_text

    if wiki_dir.is_dir():
        for p in wiki_dir.rglob("*.md"):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if p.name.startswith("_"):
                index_files[p] = text
            else:
                fm, _ = parse_frontmatter(text)
                articles[p] = (fm, text)

    root_index = vault_root / "index.md"
    if root_index.exists():
        try:
            index_files[root_index] = root_index.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass

    # --- 3. Build linkable identifier map ---
    LINK_TITLES = {}
    for path, (fm, text) in articles.items():
        candidates = [path.stem]
        if fm and fm.get("title"):
            candidates.append(str(fm["title"]).strip())
        # Frontmatter aliases
        if fm and fm.get("aliases"):
            al = fm["aliases"]
            if isinstance(al, list):
                candidates.extend(str(a).strip() for a in al if a)
            elif isinstance(al, str):
                candidates.append(al.strip())
        # First H1
        m = re.search(r"^#\s+(.+)$", text, re.M)
        if m:
            candidates.append(m.group(1).strip())
        # Path relative to wiki/ and vault root
        try:
            rel_wiki = path.relative_to(wiki_dir).with_suffix("").as_posix()
            candidates.append(rel_wiki)
        except ValueError:
            pass
        try:
            rel_vault = path.relative_to(vault_root).with_suffix("").as_posix()
            candidates.append(rel_vault)
        except ValueError:
            pass

        for c in candidates:
            LINK_TITLES[c.lower().strip()] = path

    # Add index files to valid linkable targets
    for idx_path in index_files:
        try:
            rel = idx_path.relative_to(vault_root).with_suffix("").as_posix()
            LINK_TITLES[rel.lower().strip()] = idx_path
            LINK_TITLES[idx_path.stem.lower().strip()] = idx_path
            if idx_path.name == "_master-index.md":
                LINK_TITLES["_master-index"] = idx_path
                LINK_TITLES["wiki/_master-index"] = idx_path
        except ValueError:
            pass

    # Also allow links to raw files
    if raw_dir.is_dir():
        for rp in raw_dir.rglob("*"):
            if rp.is_file():
                try:
                    rel_r = rp.relative_to(vault_root).as_posix().lower()
                    LINK_TITLES[rel_r] = rp
                    LINK_TITLES[rp.name.lower()] = rp
                except ValueError:
                    pass

    # --- 4. Build outbound / inbound link graphs ---
    outbound = defaultdict(set)
    inbound = defaultdict(set)
    for path, (fm, text) in articles.items():
        for m in LINK_RE.finditer(text):
            target = m.group(1).strip()
            # Ignore anchor-only links (#heading)
            if not target:
                continue
            outbound[path].add(target)
            inbound[target.lower()].add(path)

    # Include index files in inbound link credit
    for path, text in index_files.items():
        for m in LINK_RE.finditer(text):
            target = m.group(1).strip()
            if target:
                inbound[target.lower()].add(path)

    # --- 5. Broken wikilinks check ---
    for path, targets in outbound.items():
        for target in targets:
            clean_target = target.lower().strip()
            if clean_target not in LINK_TITLES:
                # Also check with trailing /
                if clean_target.rstrip("/") not in LINK_TITLES:
                    findings.append(("ERROR", f"broken wikilink [[{target}]]", str(path)))

    # --- 6. Orphan articles (no inbound links) ---
    for path in articles:
        # Check if any link target resolved to this path
        has_inbound = False
        for target_text, callers in inbound.items():
            if LINK_TITLES.get(target_text) == path:
                has_inbound = True
                break
        if not has_inbound:
            findings.append(("WARN", "orphan article: no inbound [[links]]", str(path)))

    # --- 7. Frontmatter, taxonomy, link counts, size, and stale dates ---
    today = datetime.date.today()
    for path, (fm, text) in articles.items():
        if fm is None:
            findings.append(("ERROR", "missing YAML frontmatter", str(path)))
            continue

        missing = [f for f in REQUIRED_FM if f not in fm or fm[f] in ("", [], None)]
        if missing:
            findings.append(("ERROR", f"frontmatter missing fields: {', '.join(missing)}", str(path)))
        else:
            # Check tags in taxonomy
            tags = fm.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            for tag in tags:
                if taxonomy and tag.lower() not in taxonomy:
                    findings.append(("WARN", f"tag '{tag}' not in SCHEMA.md taxonomy", str(path)))

            # Check sources validity
            sources = fm.get("sources", [])
            if isinstance(sources, str):
                sources = [sources]
            for s in sources:
                s_str = str(s).strip()
                if s_str.startswith("raw/"):
                    full_s = vault_root / s_str
                    if not full_s.exists():
                        findings.append(("WARN", f"source file '{s_str}' not found in raw/", str(path)))

            # Check stale updated date (>180 days)
            updated_str = str(fm.get("updated", "")).strip()
            if updated_str:
                try:
                    up_date = datetime.date.fromisoformat(updated_str)
                    if (today - up_date).days > 180:
                        findings.append(("INFO", f"stale article: updated {(today - up_date).days} days ago ({updated_str})", str(path)))
                except ValueError:
                    findings.append(("WARN", f"invalid updated date format '{updated_str}' (expected YYYY-MM-DD)", str(path)))

        # Link count (minimum 2 outbound links)
        links = outbound.get(path, set())
        if len(links) < 2:
            findings.append(("WARN", f"article has {len(links)} outbound link(s) (needs ≥2)", str(path)))

        # Article size
        lines = text.count("\n") + 1
        if lines > 200:
            findings.append(("WARN", f"article is {lines} lines (>200): consider splitting", str(path)))

    # --- 8. Index maps existence & filesystem drift ---
    if not (vault_root / "index.md").exists():
        findings.append(("WARN", "root index.md missing", str(vault_root / "index.md")))

    master = vault_root / "wiki" / "_master-index.md"
    if not master.exists():
        findings.append(("WARN", "wiki/_master-index.md missing", str(master)))
    else:
        master_text = index_files.get(master, "")
        # Check every topic folder in wiki has an entry in _master-index
        if wiki_dir.is_dir():
            for topic_dir in wiki_dir.iterdir():
                if topic_dir.is_dir() and not topic_dir.name.startswith("."):
                    if topic_dir.name not in master_text:
                        findings.append(("WARN", f"topic folder '{topic_dir.name}' missing from _master-index.md", str(master)))

    # Check topic _index.md files
    if wiki_dir.is_dir():
        for topic_dir in wiki_dir.iterdir():
            if topic_dir.is_dir() and not topic_dir.name.startswith("."):
                t_index = topic_dir / "_index.md"
                if not t_index.exists():
                    findings.append(("WARN", f"topic index missing: {t_index.name}", str(t_index)))
                else:
                    t_text = index_files.get(t_index, "")
                    for art_path in topic_dir.glob("*.md"):
                        if not art_path.name.startswith("_"):
                            if art_path.stem not in t_text and art_path.name not in t_text:
                                findings.append(("WARN", f"article '{art_path.stem}' missing from topic _index.md", str(t_index)))

    # --- 9. Digested index verification & source notes ---
    digested = vault_root / "runs" / "digested_index.md"
    if digested.exists():
        text = digested.read_text(encoding="utf-8", errors="replace")
        for m in HASH_RE.finditer(text):
            raw_path = m.group(1).strip()
            stored_hash = m.group(2).strip()
            date = m.group(3).strip()
            p = Path(raw_path)
            if not p.is_absolute():
                p = vault_root / raw_path

            if not p.exists():
                findings.append(("ERROR", f"digested raw file missing: {raw_path} (digested {date})", str(digested)))
            else:
                actual = hashlib.sha256(p.read_bytes()).hexdigest()
                if actual != stored_hash:
                    findings.append(("ERROR", f"digested raw file changed (sha256 drift): {raw_path} (digested {date})", str(digested)))

            # Source note existence in wiki/sources/
            slug = Path(raw_path).stem
            source_note = vault_root / "wiki" / "sources" / f"{slug}.md"
            if not source_note.exists():
                findings.append(("WARN", f"digested raw file missing source note: wiki/sources/{slug}.md", str(source_note)))

    # --- 10. Ledger verification check ---
    ledger_script = vault_root / "skills" / "lava-extruder" / "scripts" / "ledger.py"
    if not ledger_script.exists():
        # Look in skill directory
        ledger_script = Path(__file__).parent / "ledger.py"

    ledger_dir = vault_root / "runs" / "ledger"
    if ledger_dir.is_dir() and ledger_script.exists():
        import subprocess
        res = subprocess.run([sys.executable, str(ledger_script), "check", str(vault_root)], capture_output=True, text=True)
        if res.returncode != 0:
            for l in res.stderr.splitlines():
                if l.startswith("ERROR:"):
                    findings.append(("ERROR", l.removeprefix("ERROR:").strip(), str(ledger_dir)))
                elif l.startswith("WARN:"):
                    findings.append(("WARN", l.removeprefix("WARN:").strip(), str(ledger_dir)))

    # --- 11. hot.md size ---
    hot = vault_root / "runs" / "hot.md"
    if hot.exists():
        words = len(hot.read_text(encoding="utf-8", errors="replace").split())
        if words > 500:
            findings.append(("WARN", f"runs/hot.md is {words} words (>500): rewrite as compact cache", str(hot)))

    # --- Report Output ---
    order = sorted(findings, key=lambda f: SEVERITY_ORDER[f[0]])
    error_count = sum(1 for f in order if f[0] == "ERROR")
    warn_count = sum(1 for f in order if f[0] == "WARN")
    info_count = sum(1 for f in order if f[0] == "INFO")

    if as_json:
        out_dict = {
            "errors": error_count,
            "warnings": warn_count,
            "info": info_count,
            "clean": len(order) == 0,
            "findings": [{"severity": f[0], "message": f[1], "file": f[2]} for f in order]
        }
        print(json.dumps(out_dict, indent=2))
        return min(error_count, 255)

    if not order:
        print("✅ Vault lint clean — no issues found.")
        return 0

    for sev, msg, p in order:
        print(f"[{sev}] {msg}  ({p})")
    print(f"\n{error_count} error(s), {warn_count} warning(s), {info_count} info note(s).")
    return min(error_count, 255)


if __name__ == "__main__":
    sys.exit(main())
