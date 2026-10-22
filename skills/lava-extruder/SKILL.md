---
name: lava-extruder
description: Sets up an AI-optimized Obsidian vault folder structure with index maps, a SCHEMA.md governance contract, and AGENTS.md/CLAUDE.md instructions. Can create vaults from scratch or reorganize existing messy folders. Ingests unstructured data from the vault's /raw folder, synthesizes it into structured /wiki articles using the Lava Cooling process (Eruption, Flow, Cooling Bed, Crystallization), answers questions from the compiled wiki, and lints the knowledge base for integrity.
---

# Obsidian Vault Setup & Lava Cooling Obsidian Processing Skill

You are an expert at creating and maintaining AI-native Obsidian vaults based on the "Karpathy RAG" architecture. Your goal is to establish and navigate folder structures optimized for agentic retrieval, and to transform unstructured source documents into structured intelligence and deliverables without losing any facts or context.

The `/wiki` folder is an LLM-maintained knowledge base — you write and maintain everything in it. The vault's `SCHEMA.md` is the per-vault governance contract: it always wins over your defaults.

## Core Concepts

Agents navigate the vault using hierarchical maps:
1. **Schema Contract** (`SCHEMA.md`) at root — domain, tag taxonomy, naming conventions, page thresholds, and update policy for THIS vault.
2. **Agent Instructions** (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`) at root documenting conventions and routing.
3. **Index Maps** (`index.md` at root, `wiki/_master-index.md`, `wiki/sources/_index.md`, and per-topic `_index.md` files) that act as tables of contents.
4. **Source Hubs** (`wiki/sources/<slug>.md`) — provenance notes with bi-directional section-to-article coverage maps.
5. **Coverage Ledgers** (`runs/ledger/<file>.md`) — deterministic line and section tracking tables ensuring zero data loss.
6. **Session Continuity** (`runs/hot.md`) — a rolling ≤500-word summary of recent facts, changes, and active threads.
7. **Loop Engineering Logs** (`/runs/logs.md` and `/runs/digested_index.md`) tracking state, history, and processed files.

---

## Session Orientation Protocol (MANDATORY — every session, before any operation)

When operating on an existing vault, always orient first:
1. Read `SCHEMA.md` — domain, taxonomy, thresholds, conventions.
2. Read `runs/hot.md` — recent facts, changes, and active threads.
3. Read `wiki/_master-index.md` — what topics and articles exist.
4. Scan the last ~30 lines of `runs/logs.md` — recent activity.

Skipping orientation causes duplicate pages, missed cross-references, and schema violations. Before creating any new article, also search the wiki for the concept name to confirm it doesn't already exist.

At the END of every compile or query session that modified the vault, rewrite `runs/hot.md` (overwrite, don't append) with:
- `Last Updated: YYYY-MM-DD`
- `## Key Recent Facts` (3-8 bullets)
- `## Recent Changes` (files created/updated this session)
- `## Active Threads` (incomplete work, open questions, pending batches)

Keep it under 500 words — it is a cache, not a journal.

---

## Universal Lossless Extraction Pipeline

Never attempt to read binary or non-markdown files (`.pdf`, `.epub`, `.docx`, `.pptx`, `.xlsx`, `.zip`, `.mp3`, images, etc.) directly. Convert them to clean Markdown first. Extracted files are isolated in `runs/extracted/` and never written into `/raw/`.

### Execution Command:
```bash
# Primary (global CLI):
lava-extract "<raw_file_path>"

# CLI alias:
lava-extruder extract "<raw_file_path>"
```
*Note: If the input file is inside `<vault>/raw/`, output is automatically placed at `<vault>/runs/extracted/<relative_path>.md` with YAML manifest frontmatter.*

### Supported Formats & Capabilities:
- **Presentations (.pptx):** Extracts slide titles, text, bullet hierarchy, speaker notes, charts, tables, and image anchors. Detects hidden slides.
- **Spreadsheets (.xlsx, .xls, .csv, .tsv):** Converts every sheet into aligned GitHub-Flavored Markdown tables without row truncation.
- **Documents (.pdf):** Structure-aware extraction inserting `<!-- page: N -->` anchors and tables, with Poppler `pdftotext`, PyMuPDF, and Tesseract per-page OCR fallbacks.
- **Books (.epub):** Extracts Dublin Core metadata, preserves chronological chapter order via the EPUB Spine, and inserts chapter dividers.
- **Word Docs (.docx, .odt, .rtf):** Converts semantic headings and tables via `pandoc`, `mammoth`, `python-docx`, or LibreOffice.
- **Notebooks (.ipynb):** Renders Markdown cells, wraps code cells in ````python ... ```` blocks, and captures outputs without truncation (collapsible `<details>` for large outputs).
- **Web Pages (.html, .htm):** Strips scripts and UI boilerplate while preserving headings, tables, links, and image alt text.
- **Archives (.zip):** Sandboxed extraction with zip-slip protection, converting inner documents and appending an `## Extraction Manifest` table.
- **Emails (.msg, .eml):** Extracts headers (From, To, Date, Subject), message bodies, and attachment listings.
- **Audio (.mp3, .wav, .m4a, .mp4):** Transcribes speech via Whisper or SpeechRecognition, with audio metadata fallbacks.
- **Images (.png, .jpg, .webp):** Extracts text via Tesseract OCR and appends resolution/date metadata.

---

## Universal Coverage Ledger & Completeness Gate

Every source file ingested into the vault MUST be audited through a Coverage Ledger to ensure 100% information retention without silent dropping or premature summarization.

### 1. Initialize Ledger
Generate a section breakdown for the extracted document:
```bash
lava-extruder ledger init "runs/extracted/<file>.md"
```
This generates `runs/ledger/<file>.md` listing every section `S001..Snnn` with line ranges and headings.

### 2. Map Content to Wiki
As you write or fold articles in `/wiki/`, record each section's destination in `runs/ledger/<file>.md`:
- If mapped to an article: enter `Target: [[article-slug]]`
- If folded into an existing note: enter `Target: [[existing-article]]` (ensure concrete numbers, dates, and steps are preserved)
- If deliberately skipped (e.g. legal disclaimers, license boilerplate): enter `Target: skip` and provide an explicit reason in `Note: <reason>`

### 3. Verification Gate (Mandatory before digestion)
Run the deterministic coverage verification check:
```bash
lava-extruder ledger check "<vault_dir>" --source "<raw_path>"
```
The check verifies:
1. Every row has a non-empty Target.
2. Every `skip` row has an explicit explanation in `Note`.
3. Every target article exists on disk in `wiki/`.
4. Every target article references the raw file in its frontmatter `sources:` list.
5. All line ranges from line 1 to EOF are accounted for without unmapped gaps.
6. **Recall Heuristic (WARN):** Warns if concrete numbers, dates, or named entities from the source section are absent in the target article.

### 4. Sync Source Hub Note
Generate or update the provenance hub note in `wiki/sources/<slug>.md`:
```bash
lava-extruder ledger sync-source "<vault_dir>" "<raw_path>"
```

Only after `ledger check` passes and the source note is synchronized may the file be added to `runs/digested_index.md`.

---

## Phase 1: Vault Setup

Scaffold with `lava-extruder init <dir>` (add `--git` to initialize a git repository).

### Directory Layout
- `/raw`: The inbox for unstructured source documents. **Immutable** — never edit files in `/raw`.
- `/wiki`: LLM-maintained structured knowledge base. Organized by topic folders (`wiki/distributed-systems/`).
- `/wiki/sources`: Source notes (`type: source`) acting as provenance hubs and bi-directional coverage maps.
- `/outputs`: Deliverables, synthesized reports, and filed query answers (`outputs/queries/`, `outputs/reports/`).
- `/runs`: Agent memory, extracted documents (`runs/extracted/`), coverage ledgers (`runs/ledger/`), session cache (`hot.md`), and logs.

### Article Frontmatter Standard (v3)
Every article in `/wiki/` MUST include YAML frontmatter:
```markdown
---
title: "Article Title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [tag-from-taxonomy]
sources: ["raw/source-document.pdf", "[[source-slug]]"]
type: wiki-concept
aliases: ["Alternate Title"]
confidence: high   # high | medium | low
contested: false   # true when unresolved contradictions exist
contradictions: [] # slugs of conflicting articles
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
- Every article must have **at least 2 outbound `[[wikilinks]]`** with connection reason clauses.
- On articles synthesizing 3+ sources, append `^[raw/source-file.pdf]` provenance markers to paragraphs whose claims trace to a specific source.

---

## Phase 2: The Lava Cooling Process

When communicating with the user, identify and announce each phase:

### 1. Ingestion (The Eruption)
- Consult `/runs/digested_index.md` to identify unprocessed files in `/raw`.
- Compute SHA-256 hash. If hash matches digested index, skip it. If hash differs, flag drift and re-process.
- Run `lava-extract "<file>"`. Output is saved to `runs/extracted/<rel>.md`.
- Initialize coverage ledger: `lava-extruder ledger init "runs/extracted/<rel>.md"`.

### 2. Transport (The Flow)
- Work section by section through `runs/ledger/<rel>.md`.
- Route central concepts into `/wiki/<topic>/` articles applying Page Thresholds:
  - Central concepts or concepts in 2+ sources get an article.
  - Minor mentions fold into existing articles (retain numbers, dates, steps).
  - Split articles > 200 lines.
- Record `Target` in the coverage ledger for every section.

### 3. Storage (The Cooling Bed)
- Save articles with v3 frontmatter in topic folders.
- Update local topic `_index.md` and `wiki/_master-index.md`.
- Run `lava-extruder ledger check "<vault_dir>" --source "<file>"`. Fix any reported errors.
- Sync provenance note: `lava-extruder ledger sync-source "<vault_dir>" "<file>"`.
- Append `| <raw path> | <sha256> | YYYY-MM-DD |` to `/runs/digested_index.md`.
- If vault is a git repo, commit the batch: `wiki: digest <source> YYYY-MM-DD`.

### 4. Cross-Association (The Crystallization)
- Discover connections across topics; add bi-directional `[[wikilinks]]`.
- Check contradictions; flag with `contested: true` and link `contradictions: [other-slug]`.
- Rewrite `runs/hot.md` for the session.

---

## Phase 3: Querying the Vault

1. Orient (Session Orientation Protocol).
2. Scan `wiki/_master-index.md` and `wiki/sources/_index.md` to shortlist articles.
3. Read shortlisted articles.
4. Synthesize answers citing wiki notes: "Based on [[article-a]] and [[source-hub]]...".
5. File substantial query answers to `outputs/queries/<slug>.md`.
6. Log query in `/runs/logs.md` and update `runs/hot.md`.

---

## Phase 4: Auditing (/audit, /lint)

Run the deterministic integrity linter:
```bash
lava-extruder lint <vault_dir>
```
It checks: broken wikilinks, orphan articles, index ↔ filesystem drift, missing/invalid frontmatter, tags not in taxonomy, articles with <2 outbound links, oversized articles (>200 lines), stale updated dates, missing source notes, raw folder pollution, and ledger coverage integrity.

---

## Commands Reference

- `/compile` or `/digest-new`: Ingests and processes all undigested files in `/raw` (Lava Cooling Process).
- `/query <question>`: Answers from the compiled wiki with citations (Phase 3).
- `/audit` or `/lint`: Runs `lava-extruder lint` plus the judgment-pass review (Phase 4).
