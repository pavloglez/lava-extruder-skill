# Knowledge Base — Vault Governance & Agent Operating Methodology

You are operating an AI-native Obsidian vault based on the "Karpathy RAG" architecture.
The `/wiki` folder is an LLM-maintained knowledge base. The vault's `SCHEMA.md` is the per-vault governance contract: it always wins over defaults.

## Vault Structure
- `/raw`: The inbox for unstructured source documents. **Immutable** — never edit files in `/raw`; corrections go in wiki articles.
- `/wiki`: LLM-maintained structured knowledge base. Topic subfolders organize concepts (e.g. `wiki/distributed-systems/`).
- `/wiki/sources`: Source notes (`type: source`) acting as provenance hubs and bi-directional coverage maps.
- `/outputs`: Deliverables, synthesized reports, and filed query answers (`outputs/queries/`, `outputs/reports/`).
- `/runs`: Agent memory, extracted documents (`runs/extracted/`), coverage ledgers (`runs/ledger/`), session cache (`hot.md`), and loop engineering logs (`logs.md`, `digested_index.md`).

## Session Orientation Protocol (MANDATORY — every session, before any operation)
1. Read `SCHEMA.md` — domain, taxonomy, thresholds, conventions.
2. Read `runs/hot.md` — recent facts, changes, and active threads.
3. Read `wiki/_master-index.md` — what topics and articles exist.
4. Scan the last ~30 lines of `runs/logs.md` — recent activity.

At the END of every compile or query session that modified the vault, rewrite `runs/hot.md` (overwrite, keep under 500 words).

## Wiki Article Frontmatter Standard (v3)
Every article in `/wiki/` MUST include YAML frontmatter:
```markdown
---
title: "Article Title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [tag-from-taxonomy]
sources: ["raw/source-document.pdf", "[[source-slug]]"]
type: wiki-concept
aliases: ["Alternate Name"]
confidence: high
contested: false
contradictions: []
---

# Article Title

## Key Takeaways
- Key point 1

## Content
...

## Related Topics
- [[related-article]] — explanation of connection
- [[another-concept]] — structural relationship
```

Rules:
- Bump `updated` on every edit.
- Every article must have at least 2 outbound `[[wikilinks]]`.
- Always provide a brief reason clause after related topic links to prevent shallow graph edges.

## The Lava Cooling Process (Compiling Knowledge)
When commanded `/compile` or `/digest-new`:

1. **Ingestion (The Eruption):**
   - Check `runs/digested_index.md` for already processed files (by path + SHA-256).
   - Extract raw files using `lava-extract "<raw_path>"`. Output is stored in `runs/extracted/<rel>.md`.
   - Initialize coverage ledger: `lava-extruder ledger init "runs/extracted/<rel>.md"`.

2. **Transport & Storage (The Flow & Cooling Bed):**
   - Read segment by segment from the coverage ledger in `runs/ledger/<rel>.md`.
   - Route qualifying concepts into `/wiki/<topic>/` articles applying Page Thresholds:
     - Central concepts or concepts in 2+ sources get an article.
     - Minor mentions fold into existing articles; keep concrete numbers, dates, steps.
     - Split articles > 200 lines.
   - Fill the `Target` and `Note` columns in `runs/ledger/<rel>.md`.
   - Update topic `_index.md` and `wiki/_master-index.md`.

3. **Coverage Gate & Source Hub:**
   - Run `lava-extruder ledger check "<vault_dir>" --source "<raw_path>"`.
   - Fix any unmapped sections or missing source citations.
   - Generate source note: `lava-extruder ledger sync-source "<vault_dir>" "<raw_path>"`.
   - Once ledger verification passes cleanly, append `| <raw path> | <sha256> | YYYY-MM-DD |` to `runs/digested_index.md`.
   - If git enabled: `git add . && git commit -m "wiki: digest <source> YYYY-MM-DD"`.

4. **Cross-Association (The Crystallization):**
   - Discover cross-topic connections; add bi-directional `[[wikilinks]]`.
   - Detect contradictions (`contested: true`, `contradictions: [other-slug]`).
   - Rewrite `runs/hot.md`.

## Querying the Vault
Answer from compiled wiki notes with citations: "Based on [[article-a]] and [[article-b]]...". File substantial query findings to `outputs/queries/<slug>.md`.

## Auditing the Vault
Run `lava-extruder lint <vault_dir>` to deterministically verify link integrity, coverage ledgers, source notes, taxonomy, and graph structure.
