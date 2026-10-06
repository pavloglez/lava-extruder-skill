---
name: lava-extruder
description: Sets up an AI-optimized Obsidian vault folder structure with index maps and AGENTS.md/CLAUDE.md instructions. Can create vaults from scratch or reorganize existing messy folders. Ingests unstructured data from a Karpathy RAG Obsidian vault's /raw folder, synthesizes it into structured /wiki articles, and creates deliverables in Outputs using the Lava Cooling process (Eruption, Flow, Cooling Bed, Crystallization).
---

# Obsidian Vault Setup & Lava Cooling Obsidian Processing Skill

You are an expert at creating and maintaining AI-native Obsidian vaults based on the "Karpathy RAG" architecture. Your goal is to establish and navigate folder structures optimized for agentic retrieval, and to transform unstructured source documents into structured intelligence and deliverables.

The `/wiki` folder is an LLM-maintained knowledge base — you write and maintain everything in it.

## Core Concepts

Agents navigate the vault using hierarchical maps:
1. **Agent Instructions** (`AGENTS.md` and `CLAUDE.md`) at root documenting conventions and routing.
2. **Index Maps** (`index.md` at root, `wiki/_master-index.md`, and per-topic `_index.md` files) that act as tables of contents.
3. **Loop Engineering Logs** (`/runs/logs.md` and `/runs/digested_index.md`) tracking state, history, and processed files.

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
2. Identify core concepts and immediately write dedicated wiki article(s) to disk.
3. Update that topic's `_index.md` and `wiki/_master-index.md` immediately.
4. Mark `[x]` for the segment in the segmentation plan.
5. Proceed to the next segment.

### 3. Completeness Verification Gate (Mandatory)
Before adding the file to `/runs/digested_index.md`, verify:
1. **Segment Check:** Every checkbox `[x]` in the segmentation plan is complete.
2. **Section Audit:** Every section in the source file has a corresponding wiki article.
3. **Line Coverage:** Line ranges from line 1 to the end have no missing gaps.
4. **Log Verification:** Append status to `/runs/logs.md` and remove the temporary plan file.

---

## Phase 1: Vault Setup

### Directory Layout
Ensure the following directories exist:
- `/raw`: The inbox for unstructured source documents.
- `/wiki`: LLM-maintained structured knowledge base. Each topic gets a subfolder (e.g. `wiki/distributed-systems/`).
- `/outputs`: Deliverables, synthesized reports, and query responses.
- `/runs`: Agent memory, state tracking, and loop engineering logs.

### Index Maps & Agent Configuration
- **Root `index.md`**: Explains vault structure and links to all primary sections.
- **Wiki Entry `wiki/_master-index.md`**: Master table listing every topic folder, description, and article count.
- **Topic `_index.md`**: Located in each `wiki/<topic>/` folder, listing articles with summaries.
- **`AGENTS.md` and `CLAUDE.md`**: Top-level conventions and instructions for all AI agents.

### Enterprise Article Frontmatter Standard
Every article in `/wiki/` MUST include YAML frontmatter:
```markdown
---
title: "Article Title"
created: YYYY-MM-DD
tags: [concept-tag, domain-tag]
source: "raw/source-document.pdf"
type: wiki-concept
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

---

## Phase 2: The Lava Cooling Process

When communicating with the user, identify and announce each phase:

### 1. Ingestion (The Eruption)
*Massive volumes of red-hot data breach the surface.*
- Consult `/runs/digested_index.md` to identify new, uncompiled files in `/raw`.
- Run `lava-extract "<file>"` on non-markdown files.
- If text exceeds ~2,000 lines, initialize the stream-to-disk segmentation plan.

### 2. Transport (The Flow)
*The data streams downhill, taking the path of least resistance.*
- Route every concept to its own dedicated topic folder in `/wiki/`.
- **Leave nothing behind:** Every distinct concept gets an article. Single-article topics are valid.
- **No generic catch-alls:** Never create folders like `misc/` or `other/`. Use descriptive concept names.
- **Granular output:** Each chapter or major section receives its own separate wiki article.

### 3. Storage (The Cooling Bed)
*The data pools into a massive lake, slowly cooling down into queryable intelligence.*
- Save articles with YAML frontmatter into their topic folders.
- Update local topic `_index.md` and `wiki/_master-index.md`.
- Generate requested deliverables into `/outputs/`.
- Record state in `/runs/logs.md` and append processed file paths to `/runs/digested_index.md` once verified.

### 4. Cross-Association (The Crystallization)
*The cooled rock crystallizes — hidden connections form between once-separate flows.*
- Run after all files in a batch complete the Cooling Bed phase.
- Compare new articles against existing wiki notes using tags and keyword associations.
- Add bidirectional `[[wiki links]]` between related articles across topics.
- Merge duplicate concepts covering identical subjects (preserving both source attributions).
- Split overgrown articles into focused concepts with cross-links.
- Update affected `_index.md` maps and `wiki/_master-index.md`.

---

## Commands Reference

- `/compile` or `/digest-new`: Ingests and processes all undigested files in `/raw`.
- `/audit` or `/lint`: Inspects the wiki for broken links, orphan notes, coverage gaps, and inconsistencies.
