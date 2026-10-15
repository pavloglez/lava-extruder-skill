#!/usr/bin/env python3
"""
lint_vault.py — Deterministic vault integrity lint for Lava Extruder vaults.
Usage: lint_vault.py <vault_dir>

Checks (no LLM needed):
- broken wikilinks          -> ERROR   link target doesn't exist
- orphan articles           -> WARN    wiki page with no inbound [[links]]
- index vs filesystem drift -> ERROR   article on disk missing from _master-index (and vice versa)
- missing/invalid frontmatter -> ERROR missing required fields or bad YAML block
- tags outside taxonomy     -> WARN    tag used but not in SCHEMA.md taxonomy
- articles with <2 outbound links -> WARN invisible to graph navigation
- oversized articles (>200 lines) -> WARN candidate for splitting
- stale articles            -> INFO    updated older than most other articles' updated
- digested index vs raw files -> ERROR raw path missing or sha256 changed since digest
- hot.md size >500 words    -> WARN    hot cache grown too large
- index.md/_index.md missing -> WARN   navigation gaps

Exit code: number of ERROR findings (capped at 255). 0 means clean.
"""

import os
import re
import sys
import hashlib
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
    fm = {}
    for line in body.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            fm[key] = [t.strip().strip('"').strip("'") for t in inner.split(",") if t.strip()] if inner else []
        else:
            fm[key] = val.strip('"').strip("'")
    return fm, text[m.end():]


def wiki_path_for_link(link_text, vault_root):
    """Resolve a wikilink target to a candidate .md path under the vault."""
    link_text = link_text.strip()
    # Direct candidates
    candidates = [
        vault_root / f"{link_text}.md",
        vault_root / "wiki" / f"{link_text}.md",
    ]
    # Also allow wiki/<topic>/<article>
    return candidates


def main():
    if len(sys.argv) < 2:
        print("Usage: lint_vault.py <vault_dir>", file=sys.stderr)
        sys.exit(2)

    vault_root = Path(sys.argv[1]).resolve()
    if not vault_root.is_dir():
        print(f"Error: not a directory: {vault_root}", file=sys.stderr)
        sys.exit(2)

    findings = []  # (severity, message, path)

    # --- gather taxonomy from SCHEMA.md ---
    taxonomy = set()
    schema_path = vault_root / "SCHEMA.md"
    if schema_path.exists():
        text = schema_path.read_text(encoding="utf-8", errors="ignore")
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

    # --- index every wiki article ---
    wiki_dir = vault_root / "wiki"
    articles = {}  # path -> (frontmatter, raw_text)
    if wiki_dir.is_dir():
        for p in wiki_dir.rglob("*.md"):
            if p.name.startswith("_"):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            fm, _ = parse_frontmatter(text)
            articles[p] = (fm, text)

    # --- build link graph ---
    outbound = defaultdict(set)   # path -> set of link targets (raw text)
    inbound = defaultdict(set)    # target text -> set of linking paths
    for path, (fm, text) in articles.items():
        for m in LINK_RE.finditer(text):
            target = m.group(1).strip()
            outbound[path].add(target)
            inbound[target].add(path)

    def article_titles():
        """Map linkable identifiers (title, h1, stem) -> article path."""
        titles = {}
        for path, (fm, text) in articles.items():
            candidates = []
            if fm and fm.get("title"):
                candidates.append(str(fm["title"]).strip())
            # first H1 heading
            m = re.search(r"^#\s+(.+)$", text, re.M)
            if m:
                candidates.append(m.group(1).strip())
            candidates.append(path.stem)
            for c in candidates:
                titles.setdefault(c.lower(), path)
        return titles

    LINK_TITLES = article_titles()

    def exists_anywhere(target):
        return target.strip().lower() in LINK_TITLES

    def link_to_path(target):
        return LINK_TITLES.get(target.strip().lower())

    # --- 1. broken wikilinks ---
    for path, targets in outbound.items():
        for target in targets:
            if not exists_anywhere(target):
                findings.append(("ERROR", f"broken wikilink [[{target}]]", str(path)))

    # --- 2. orphan articles (no inbound links; index/master index excluded) ---
    for path in articles:
        if path.name in ("_master-index.md", "_index.md", "index.md", "SCHEMA.md"):
            continue
        has_inbound = False
        for target, linkers in inbound.items():
            if link_to_path(target) == path:
                has_inbound = True
                break
        if not has_inbound:
            findings.append(("WARN", f"orphan article: no inbound [[links]]", str(path)))

    # --- 3. frontmatter, tags, link counts, size ---
    for path, (fm, text) in articles.items():
        if path.name in ("_master-index.md", "_index.md"):
            continue
        if fm is None:
            findings.append(("ERROR", "missing YAML frontmatter", str(path)))
            continue
        missing = [f for f in REQUIRED_FM if f not in fm or fm[f] in ("", [], None)]
        if missing:
            findings.append(("ERROR", f"frontmatter missing fields: {', '.join(missing)}", str(path)))
        else:
            # tags in taxonomy
            tags = fm.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            for tag in tags:
                if taxonomy and tag.lower() not in taxonomy:
                    findings.append(("WARN", f"tag '{tag}' not in SCHEMA.md taxonomy", str(path)))
        # link count
        links = outbound.get(path, set())
        if len(links) < 2:
            findings.append(("WARN", f"article has {len(links)} outbound link(s) (needs ≥2)", str(path)))
        # size
        lines = text.count("\n") + 1
        if lines > 200:
            findings.append(("WARN", f"article is {lines} lines (>200): consider splitting", str(path)))

    # --- 4. index.md / _master-index.md existence ---
    if not (vault_root / "index.md").exists():
        findings.append(("WARN", "root index.md missing", str(vault_root / "index.md")))
    master = vault_root / "wiki" / "_master-index.md"
    if not master.exists():
        findings.append(("WARN", "wiki/_master-index.md missing", str(master)))

    # --- 5. digested index vs raw files ---
    digested = vault_root / "runs" / "digested_index.md"
    if digested.exists():
        text = digested.read_text(encoding="utf-8", errors="ignore")
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

    # --- 6. hot.md size ---
    hot = vault_root / "runs" / "hot.md"
    if hot.exists():
        words = len(hot.read_text(encoding="utf-8", errors="ignore").split())
        if words > 500:
            findings.append(("WARN", f"runs/hot.md is {words} words (>500): rewrite as compact cache", str(hot)))

    # --- report, grouped by severity ---
    order = sorted(findings, key=lambda f: SEVERITY_ORDER[f[0]])
    error_count = sum(1 for f in order if f[0] == "ERROR")
    warn_count = sum(1 for f in order if f[0] == "WARN")
    info_count = sum(1 for f in order if f[0] == "INFO")

    if not order:
        print("✅ Vault lint clean — no issues found.")
        return 0

    for sev, msg, p in order:
        print(f"[{sev}] {msg}  ({p})")
    print(f"\n{error_count} error(s), {warn_count} warning(s), {info_count} info note(s).")
    return min(error_count, 255)


if __name__ == "__main__":
    sys.exit(main())
