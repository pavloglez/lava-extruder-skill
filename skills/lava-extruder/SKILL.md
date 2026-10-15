---
name: lava-extruder
description: Sets up an AI-optimized Obsidian vault folder structure with index maps, a SCHEMA.md governance contract, and AGENTS.md/CLAUDE.md instructions. Can create vaults from scratch or reorganize existing messy folders. Ingests unstructured data from the vault's /raw folder, synthesizes it into structured /wiki articles using the Lava Cooling process (Eruption, Flow, Cooling Bed, Crystallization), answers questions from the compiled wiki, and lints the knowledge base for integrity.
---

# Obsidian Vault Setup & Lava Cooling Obsidian Processing Skill

You are an expert at creating and maintaining AI-native Obsidian vaults based on the "Karpathy RAG" architecture. Your goal is to establish and navigate folder structures optimized for agentic retrieval, and to transform unstructured source documents into structured intelligence and deliverables.

The `/wiki` folder is an LLM-maintained knowledge base — you write and maintain everything in it. The vault's `SCHEMA.md` is the per-vault governance contract: it always wins over your defaults.

## Core Concepts

Agents navigate the vault using hierarchical maps:
1. **Schema Contract** (`SCHEMA.md`) at root — domain, tag taxonomy, naming conventions, page thresholds, and update policy for THIS vault.
2. **Agent Instructions** (`AGENTS.md` and `CLAUDE.md`) at root documenting conventions and routing.
3. **Index Maps** (`index.md` at root, `wiki/_master-index.md`, and per-topic `_index.md` files) that act as tables of contents.
4. **Session Continuity** (`runs/hot.md`) — a rolling ≤500-word summary of recent facts, changes, and active threads.
5. **Loop Engineering Logs** (`/runs/logs.md` and `/runs/digested_index.md`) tracking state, history, and processed files.

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

## Universal Extraction Pipeline

Never attempt to read binary or non-markdown files (`.pdf`, `.epub`, `.docx`, `.pptx`, `.xlsx`, `.zip`, `.mp3`, images, etc.) directly. Convert them to clean Markdown first.

### Execution Command:
```bash
# Primary (global CLI):
lava-extract "<raw_file_path>" "<raw_file_path>.extracted.md"

# CLI alias:
lava-extruder extract "<raw_file_path>" "<raw_file_path>.extracted.md"

# Fallback (direct script resolution):
python3 "$(which lava-extract 2>/dev/null || find ~/.gemini ~/.claude -name extract_raw.py 2>/dev/null | head -1)" "<raw_file_path>"
```

### Supported Formats & Capabilities:
- **Presentations (.pptx):** Extracts slide titles, text, bullet hierarchy, speaker notes, and converts tables & charts to Markdown.
- **Spreadsheets (.xlsx, .xls, .csv, .tsv):** Converts every sheet into aligned GitHub-Flavored Markdown tables.
- **Documents (.pdf):** Table-aware extraction via `pdfplumber`/`markitdown` with Poppler `pdftotext`, PyMuPDF, and Tesseract OCR fallbacks.
- **Books (.epub):** Extracts Dublin Core metadata, preserves chronological chapter order via the EPUB Spine, and inserts chapter dividers.
- **Word Docs (.docx, .odt, .rtf):** Converts semantic headings and tables via `pandoc`, `mammoth`, `python-docx`, or LibreOffice.
- **Notebooks (.ipynb):** Renders Markdown cells, wraps code cells in ````python ... ```` blocks, and captures stdout.
- **Web Pages (.html, .htm):** Strips scripts, styles, and UI boilerplate, producing clean semantic Markdown.
- **Archives (.zip):** Sandboxed extraction with zip-slip protection, converting all supported inner documents.
- **Emails (.msg, .eml):** Extracts headers (From, To, Date, Subject), message bodies, and attachment listings.
- **Audio (.mp3, .wav, .m4a, .mp4):** Transcribes speech via Whisper or SpeechRecognition, with audio metadata fallbacks.
- **Images (.png, .jpg, .webp):** Extracts text via Tesseract OCR and appends resolution/date metadata.

### Extraction Failure Protocol:
1. Do NOT mark failed files as digested in `/runs/digested_index.md`.
2. Append failure details to `/runs/failed_extractions.md` (file path, format, reason, timestamp).
3. Notify the user and continue processing the remaining files in the batch.

---

## Segmented Extraction Strategy (Files > 2,000 Lines)

Any extracted file exceeding ~2,000 lines MUST be processed using a stream-to-disk segmented approach. Never accumulate large documents into a single working file.

### 1. Pre-Processing: Build Segmentation Plan
Count structural markers and plan bounded segments (~500–800 lines each):
```bash
lava-extruder count "<extracted_file>"
```
Create `/runs/segmentation_plan_<filename>.md` containing:
- Total line count and total planned segments.
- List of chapter/section boundaries.
- Checklist `[ ]` for each segment.

### 2. Processing Loop (Stream-to-Disk)
For each segment:
1. Read the segment using bounded line ranges.
2. Identify core concepts and immediately write/update wiki article(s) on disk, applying the Page Thresholds below.
3. Update that topic's `_index.md` and `wiki/_master-index.md` immediately.
4. Mark `[x]` for the segment in the segmentation plan.
5. Proceed to the next segment.

### 3. Completeness Verification Gate (Mandatory)
Before adding the file to `/runs/digested_index.md`, verify:
1. **Segment Check:** Every checkbox `[x]` in the segmentation plan is complete.
2. **Section Audit:** Every section in the source file is represented in the wiki (as an article or as content folded into one).
3. **Line Coverage:** Line ranges from line 1 to the end have no missing gaps.
4. **Log Verification:** Append status to `/runs/logs.md` and remove the temporary plan file.

---

## Phase 1: Vault Setup

Scaffold with `lava-extruder init <dir>` (add `--git` to initialize a git repository), or create manually.

### Directory Layout
Ensure the following directories exist:
- `/raw`: The inbox for unstructured source documents. **Immutable** — never edit files in `/raw`; corrections go in wiki articles.
- `/wiki`: LLM-maintained structured knowledge base. Each topic gets a subfolder (e.g. `wiki/distributed-systems/`).
- `/outputs`: Deliverables, synthesized reports, and filed query answers (`outputs/queries/`, `outputs/reports/`).
- `/runs`: Agent memory, state tracking, hot cache, and loop engineering logs.

### Governance & Navigation Files
- **`SCHEMA.md`**: The vault contract — domain description, tag taxonomy, naming conventions, page thresholds, update policy. When setting up a new vault, ASK the user what domain it covers and customize SCHEMA.md to it. Every tag used in frontmatter MUST exist in the taxonomy; add new tags to SCHEMA.md first, then use them.
- **Root `index.md`**: Explains vault structure and links to all primary sections.
- **Wiki Entry `wiki/_master-index.md`**: Master table listing every topic folder, description, and article count.
- **Topic `_index.md`**: Located in each `wiki/<topic>/` folder, listing articles with one-line summaries.
- **`AGENTS.md` and `CLAUDE.md`**: Full operating methodology for any AI agent (self-contained — an agent without this skill must still be able to run the vault).
- **`runs/hot.md`**: Session continuity cache (see Orientation Protocol).

### Git Integration
If the vault is a git repository, commit after each completed batch (Cooling Bed phase) with the message convention `wiki: digest <source> YYYY-MM-DD` (or `wiki: <action> YYYY-MM-DD` for lint fixes/crystallization). Git is the vault's temporal history and undo layer. Never commit secrets; `/raw` may be gitignored for huge binary sources at the user's discretion.

### Article Frontmatter Standard (v2)
Every article in `/wiki/` MUST include YAML frontmatter:
```markdown
---
title: "Article Title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [tag-from-taxonomy, another-tag]
sources: ["raw/source-document.pdf"]
type: wiki-concept
confidence: high   # optional: high | medium | low — how well-supported the claims are
contested: false   # optional: true when the article holds unresolved contradictions
contradictions: [] # optional: slugs of articles this one conflicts with
---

# Article Title

## Key Takeaways
- Key point 1
- Key point 2

## Content
...

## Related Topics
- [[related-article]]
- [[another-concept]]
```
Rules:
- Bump `updated` on every edit.
- Every article must have **at least 2 outbound `[[wikilinks]]`** — isolated pages are invisible to graph navigation.
- Set `confidence: low|medium` for single-source or fast-moving claims; don't mark `high` unless corroborated across sources.
- On articles synthesizing 3+ sources, append `^[raw/source-file.pdf]` provenance markers to paragraphs whose claims trace to a specific source.

### Page Thresholds
- **Create an article** when a concept/entity is central to a source OR appears in 2+ sources.
- **Fold into an existing article** when a source mentions something already covered, or the concept is minor — add it as a section or bullet instead of a new page.
- **Do NOT create an article** for passing mentions, trivia, or concepts outside the vault's domain (per SCHEMA.md).
- **Split an article** when it exceeds ~200 lines — break into focused sub-concepts with cross-links.
- **No generic catch-alls:** Never create folders like `misc/` or `other/`. Use descriptive concept names.
- Single-article topics are valid when the concept is genuinely standalone, but prefer grouping related concepts under one topic folder.

---

## Phase 2: The Lava Cooling Process

When communicating with the user, identify and announce each phase:

### 1. Ingestion (The Eruption)
*Massive volumes of red-hot data breach the surface.*
- Consult `/runs/digested_index.md` to identify new, unprocessed files in `/raw`.
- Compute each candidate's hash: `sha256sum "<raw_file>"`. If the path AND hash already appear in the digested index, skip it. If the path matches but the hash differs, the source changed — flag drift to the user and re-process, superseding affected articles.
- Run `lava-extract "<file>"` on non-markdown files.
- If text exceeds ~2,000 lines, initialize the stream-to-disk segmentation plan.

### 2. Transport (The Flow)
*The data streams downhill, taking the path of least resistance.*
- Route every qualifying concept (per Page Thresholds) to its topic folder in `/wiki/`.
- Fold minor mentions into existing articles rather than minting new pages.
- Each chapter or major section of a large source gets represented — as its own article when substantive, or folded into a sibling article when thin.

### 3. Storage (The Cooling Bed)
*The data pools into a massive lake, slowly cooling down into queryable intelligence.*
- Save articles with v2 frontmatter into their topic folders.
- Update local topic `_index.md` and `wiki/_master-index.md`.
- Generate requested deliverables into `/outputs/`.
- Record state in `/runs/logs.md` and append `| <raw path> | <sha256> | YYYY-MM-DD |` rows to `/runs/digested_index.md` once verified.
- If the vault is a git repo, commit the batch.

### 4. Cross-Association (The Crystallization)
*The cooled rock crystallizes — hidden connections form between once-separate flows.*
- Run after all files in a batch complete the Cooling Bed phase.
- Compare new articles against existing wiki notes using tags and keyword associations.
- Add bidirectional `[[wiki links]]` between related articles across topics.
- **Contradiction policy (never silently blend):** when new content conflicts with an existing article, check dates — newer sources generally supersede. If genuinely contradictory, present both positions with dates and sources, set `contested: true` and `contradictions: [other-slug]` in both articles' frontmatter, and flag the pair for user review.
- Merge duplicate concepts covering identical subjects (preserving all source attributions).
- Split overgrown articles into focused concepts with cross-links.
- Update affected `_index.md` maps and `wiki/_master-index.md`.
- Rewrite `runs/hot.md` for the session.

---

## Phase 3: Querying the Vault

When the user asks a question answerable from the vault:
1. Orient (Session Orientation Protocol above).
2. Scan `wiki/_master-index.md` (and topic `_index.md` files) to shortlist relevant articles; for large vaults also grep the wiki for key terms.
3. Read the shortlisted articles.
4. Synthesize an answer from the compiled knowledge, citing the wiki articles used: "Based on [[article-a]] and [[article-b]]...". Respect `contested`/`confidence` flags — surface uncertainty instead of hiding it.
5. **File valuable answers back:** substantial comparisons, deep dives, or novel syntheses go to `outputs/queries/<slug>.md` with frontmatter (`type: query`, `sources:` listing the wiki articles). Don't file trivial lookups.
6. Log the query in `/runs/logs.md` and update `runs/hot.md` if anything was filed.

---

## Phase 4: Auditing (/audit, /lint)

Run the deterministic linter first, then fix findings:
```bash
lava-extruder lint <vault_dir>
```
It checks: broken wikilinks, orphan articles, index ↔ filesystem drift, missing/invalid frontmatter, tags not in SCHEMA.md taxonomy, articles with <2 outbound links, oversized articles (>200 lines), stale `updated` dates, digested-index entries whose raw file is missing or whose hash changed, and hot.md size.

After the mechanical pass, do the judgment pass the linter can't: contradictions between articles sharing tags/entities, coverage gaps versus digested sources, candidates for merging/splitting, and articles with `contested: true` or `confidence: low` needing corroboration. Report findings grouped by severity with file paths, fix what's safe, and log the audit in `/runs/logs.md`.

---

## Commands Reference

- `/compile` or `/digest-new`: Ingests and processes all undigested files in `/raw` (Lava Cooling Process).
- `/query <question>`: Answers from the compiled wiki with citations (Phase 3).
- `/audit` or `/lint`: Runs `lava-extruder lint` plus the judgment-pass review (Phase 4).

## Scaling Note

This architecture is deliberately zero-infrastructure (markdown + git, no vector DB) and works well up to roughly a thousand articles. If a vault outgrows file-level navigation, add a derived, rebuildable index (the basic-memory pattern: files stay the source of truth, the index is a cache) rather than migrating the knowledge into a database.
