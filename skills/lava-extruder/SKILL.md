---
name: lava-extruder
description: Sets up an AI-optimized Obsidian vault folder structure with index maps and AGENTS.md/CLAUDE.md instructions. Can create vaults from scratch or reorganize existing messy folders. Ingests unstructured data from a Karpathy RAG Obsidian vault's /raw folder, synthesizes it into structured /wiki articles, and creates deliverables in Outputs using the Lava Cooling process (Eruption, Flow, Cooling Bed, Crystallization).
---

# Obsidian Vault Setup & Lava Cooling Obsidian Processing Skill

You are an expert at creating and organizing AI-native Obsidian vaults, acting as the librarian and active processing engine for an AI-native Obsidian vault based on the "Karpathy RAG" method. Your goal is to establish a folder structure that optimizes knowledge retrieval for AI agents, and to transform unstructured notes into structured intelligence and deliverables. This is an LLM-maintained knowledge base. The `/wiki` folder is YOUR domain — you write and maintain everything in it. The user rarely edits wiki files directly.

## Core Concepts

The power of this vault is NOT just the folders, it is the map. AI agents navigate the vault using:
1. **Top-level Agent instructions** (`AGENTS.md` and `CLAUDE.md`) that document conventions and the navigation pattern.
2. **Index maps** (`_master-index.md` for the wiki entry, and `_index.md` for topics) that act as a map and table of contents, telling the AI exactly what it's looking at and where to go deeper.
3. **Loop Engineering Logs** in the `/runs` folder where agents can leave state and track past runs.

## Supported File Formats

Before processing any file in `/raw`, identify its format and follow the appropriate extraction method below. **You MUST convert binary formats to readable plain text before attempting to read or analyze their content.**

### Plain Text Files (.md, .txt, .csv, .json, .html)
Read directly with file-reading tools. No special handling needed.

### PDF Files (.pdf)
PDFs are binary files that cannot be read directly by `view_file`. You MUST extract their text content before processing:

1. **Extract text using a CLI tool.** Run one of these commands to convert the PDF to plain text:
   ```bash
   # Preferred: pdftotext (from poppler-utils)
   pdftotext "<raw_file_path>" "<raw_file_path>.extracted.txt"

   # Fallback: python with PyMuPDF
   python3 -c "
   import fitz
   doc = fitz.open('<raw_file_path>')
   with open('<raw_file_path>.extracted.txt', 'w') as f:
       for page in doc:
           f.write(page.get_text())
           f.write('\n--- PAGE BREAK ---\n')
   "
   ```
2. **If the tool is not installed**, install it first:
   ```bash
   # For pdftotext
   sudo apt-get install -y poppler-utils  # Debian/Ubuntu
   brew install poppler                    # macOS

   # For PyMuPDF fallback
   pip install PyMuPDF
   ```
3. Once extracted, process the `.extracted.txt` file using the Segmented Extraction Strategy described below if it exceeds ~2,000 lines.
4. **Scanned / Image-Only PDFs:** If `pdftotext` or `PyMuPDF` produces an empty or near-empty output (fewer than ~10 lines of non-whitespace text), the PDF is likely scanned or image-only. You MUST attempt OCR extraction:
   ```bash
   # Install OCR tools if not available
   sudo apt-get install -y tesseract-ocr poppler-utils  # Debian/Ubuntu
   brew install tesseract poppler                        # macOS

   # Convert PDF pages to images, then OCR each page
   TMPDIR=$(mktemp -d)
   pdftoppm "<raw_file_path>" "$TMPDIR/page" -png
   : > "<raw_file_path>.extracted.txt"
   for img in "$TMPDIR"/page-*.png; do
     tesseract "$img" - >> "<raw_file_path>.extracted.txt"
     echo -e "\n--- PAGE BREAK ---\n" >> "<raw_file_path>.extracted.txt"
   done
   rm -rf "$TMPDIR"
   ```
   If OCR also produces little/no text, follow the **Extraction Failure Handling** process below.

### EPUB Files (.epub)
EPUBs are ZIP archives containing structured XHTML chapters. You MUST unpack and extract their text content before processing:

1. **Extract text using a CLI tool.** Run one of these commands:
   ```bash
   # Preferred: pandoc (converts EPUB to plain markdown)
   pandoc "<raw_file_path>" -t markdown --wrap=none -o "<raw_file_path>.extracted.md"

   # Fallback: python with ebooklib
   python3 -c "
   import ebooklib
   from ebooklib import epub
   from html.parser import HTMLParser

   class TextExtractor(HTMLParser):
       def __init__(self):
           super().__init__()
           self.result = []
       def handle_data(self, data):
           self.result.append(data)
       def get_text(self):
           return ''.join(self.result)

   book = epub.read_epub('<raw_file_path>')
   with open('<raw_file_path>.extracted.md', 'w') as f:
       for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
           extractor = TextExtractor()
           extractor.feed(item.get_content().decode('utf-8', errors='ignore'))
           text = extractor.get_text().strip()
           if text:
               f.write(f'# {item.get_name()}\n\n')
               f.write(text)
               f.write('\n\n---\n\n')
   "
   ```
2. **If the tool is not installed**, install it first:
   ```bash
   # For pandoc
   sudo apt-get install -y pandoc  # Debian/Ubuntu
   brew install pandoc              # macOS

   # For ebooklib fallback
   pip install EbookLib
   ```
3. Once extracted, process the `.extracted.md` file using the Segmented Extraction Strategy described below if it exceeds ~2,000 lines.

### DOCX, ODT & RTF Files (.docx, .odt, .rtf)
These are binary document formats common in office workflows. You MUST convert them to readable text before processing:

1. **Extract text using pandoc** (the same tool used for EPUB):
   ```bash
   pandoc "<raw_file_path>" -t markdown --wrap=none -o "<raw_file_path>.extracted.md"
   ```
2. **Fallback: LibreOffice headless conversion** (if pandoc is not available):
   ```bash
   # Install LibreOffice if needed
   sudo apt-get install -y libreoffice  # Debian/Ubuntu

   # Convert to plain text
   libreoffice --headless --convert-to txt:"Text" --outdir /tmp "<raw_file_path>"
   # Then move the resulting .txt file to <raw_file_path>.extracted.md
   ```
3. **If pandoc is not installed**, install it first:
   ```bash
   sudo apt-get install -y pandoc  # Debian/Ubuntu
   brew install pandoc              # macOS
   ```
4. Once extracted, process the `.extracted.md` file using the Segmented Extraction Strategy described below if it exceeds ~2,000 lines.

### Extraction Failure Handling

When extraction fails for ANY file format — the tool errors out, produces corrupt output, or yields near-empty text — follow this procedure:

1. **Do NOT mark the file as digested** in `/runs/digested_index.md`. The file is NOT processed.
2. **Log the failure.** Append an entry to `/runs/failed_extractions.md` with:
   - The file path
   - The format attempted
   - The extraction method(s) tried
   - The error message or reason for failure (e.g., "pdftotext: empty output; tesseract OCR: 3 lines of garbage text")
   - A timestamp
3. **Notify the user** in your response that the file could not be processed automatically and may need manual conversion or a different tool.
4. **Continue processing** the remaining files in the batch. One failure must not halt the entire pipeline.

### Helper Scripts
This skill includes ready-to-use extraction scripts in its `scripts/` directory. If available, you can use them instead of constructing commands manually:
- `extract_pdf.sh <input.pdf> <output.txt>` — Extracts PDF to plain text with automatic fallback (pdftotext → PyMuPDF → Tesseract OCR)
- `extract_epub.sh <input.epub> <output.md>` — Extracts EPUB to markdown with automatic fallback
- `extract_docx.sh <input_file> <output.md>` — Extracts DOCX, ODT, or RTF to markdown with automatic fallback
- `count_sections.sh <input_file>` — Counts structural markers (headings, dividers, numbered sections) to aid chunking

**Finding the scripts:** The scripts are located at the skill's installation path. To find them, run:
```bash
find ~/.gemini -name "extract_pdf.sh" -path "*/lava-extruder/*" 2>/dev/null | head -1 | xargs dirname
```
Typical location: `~/.gemini/config/plugins/lava-extruder-plugin/skills/lava-extruder/scripts/`
If using a project-local skill, check `./skills/lava-extruder/scripts/` relative to the plugin root.

## Segmented Extraction Strategy for Large Files

Any extracted file larger than ~2,000 lines (roughly 50 pages) MUST be processed using this segmented, stream-to-disk strategy. The core principle is: **process each segment independently and write its wiki article(s) immediately — never accumulate the entire file's content in a single working file or in your context.**

> **Why not accumulate?** A single WIP file for a 5,000-line source will itself be 2,000+ lines of notes. When you try to read it all at synthesis time, you'll overflow context and silently drop information. Stream-to-disk avoids this entirely: each segment goes from raw text → wiki article in one pass, keeping your working set small.

### Pre-Processing: Build a Segmentation Plan
Before reading the content, build a detailed plan of the extracted file:

1. Count total lines: `wc -l "<file>"`
2. Identify ALL structural markers (chapter headings, `---` dividers, `# heading` markers, numbered sections, roman numeral chapters, page breaks) using grep:
   ```bash
   grep -nE "^#{1,6} |^---$|^Chapter |^CHAPTER |^Part |^PART |^--- PAGE BREAK ---|^Section [0-9]|^SECTION [0-9]|^[0-9]+\.[0-9]* |^[IVXLC]+\.\s" "<file>"
   ```
3. If the file has a table of contents or front matter listing sections, extract it separately:
   ```bash
   head -100 "<file>"
   ```
4. Write the segmentation plan to `/runs/segmentation_plan_<filename>.md` with:
   - Total lines / estimated pages
   - **Complete list** of ALL chapters/sections with their line numbers
   - **Total expected segment count** (record this number — you'll verify against it later)
   - Planned segment boundaries (aim for ~500-800 line segments, breaking at section boundaries)
   - A checklist with `[ ]` for each segment

### Processing Loop (Stream-to-Disk)
For each segment in the plan, process it **completely and independently** before moving to the next:

1. **Read the segment** using line-range reading (e.g., `view_file` with StartLine/EndLine). Use the FULL 800-line window if the segment is large — do NOT read less than the segment boundaries.
2. **Identify topics** — which wiki topic(s) does this segment contribute to?
3. **Write the wiki article(s) immediately.** Do NOT defer to a later synthesis step. Create a dedicated wiki article for each distinct topic/concept found in this segment. Write it to disk NOW.
   - Name the article descriptively to indicate its source context (e.g., `transformer-attention-mechanisms.md`, NOT `chapter-3-notes.md`)
   - Each article MUST include `## Key Takeaways`, `## Tags`, and a `## Source` section noting the raw file path and line range
   - If this segment continues a topic from a previous segment, **append to or update** the existing article — do NOT create a duplicate
4. **Update indexes immediately.** Update the topic `_index.md` and `wiki/_master-index.md` after writing each article. Do not batch index updates.
5. **Mark progress** — check off `[x]` the segment in the segmentation plan
6. **Repeat** until ALL segments have been processed — do NOT stop early, do NOT skip segments, do NOT summarize remaining segments

### Critical Rules for Segmented Processing

- **ONE segment at a time.** Never read more than one segment into your context at once. Process it, write to disk, then move on.
- **NEVER use a single WIP accumulation file.** The old pattern of appending everything to `/runs/wip_<filename>.md` and synthesizing later causes data loss on large files. Each segment produces its own output immediately.
- **Every segment MUST produce output.** If a segment contains meaningful content, it must result in a new article or an update to an existing one. If you read a segment and don't write anything, something is wrong — go back and re-read it.
- **Keep separate files for separate sections.** Do NOT compile multiple chapters or sections into a single monolithic wiki article. Each major section/chapter should have its own dedicated wiki article. A book with 20 chapters should produce roughly 20 (or more) wiki articles, not 1-3 summary articles.
- **Preserve granularity.** Subsections within a chapter that cover distinct concepts should get their own articles. When in doubt, create more articles rather than fewer — an article is never "too small" but information loss is always too much.

### Post-Processing: Completeness Verification
After ALL segments have been processed, perform a **mandatory verification gate** before marking the file as digested:

1. **Count check.** Re-read `/runs/segmentation_plan_<filename>.md`. Count the total segments. Verify that every `[ ]` has been checked off as `[x]`. If ANY segment is unchecked, go back and process it NOW.
2. **Section coverage audit.** Compare the list of sections/chapters from the segmentation plan against the wiki articles you actually created. List them side by side. If any section from the source file does not have a corresponding wiki article (or article section), go back and create it.
3. **Line coverage check.** Verify that your segments covered from line 1 to the last line of the file with no gaps. Run:
   ```bash
   wc -l "<file>"
   ```
   Cross-reference against your segment boundaries. If there's a gap (e.g., you jumped from segment ending at line 1600 to segment starting at line 2100), go back and process the missing range.
4. **Log the verification.** Append a verification summary to `/runs/logs.md`:
   - File processed
   - Total segments: X / X completed
   - Total wiki articles created/updated: Y
   - Line coverage: 1–N (complete / gaps found at: ...)
5. **Clean up.** Remove `/runs/segmentation_plan_<filename>.md` only after verification passes.
6. **Mark as digested.** Append the raw file's path to `/runs/digested_index.md` — but ONLY after the verification gate passes.

### Critical Rule
**NEVER mark a file as digested in `/runs/digested_index.md` until the completeness verification gate has passed.** Partial digestion is worse than no digestion. If verification fails, fix the gaps before proceeding.

## Phase 1: Vault Setup

### 1. Assess the Vault
When invoked, first check the current directory:
- If the directory is mostly empty, proceed with **Creating from Scratch**.
- If the directory has existing messy data, ask the user if they want to **Reorganize** their existing data into the new structure or just create the new structure alongside it.
- Ask the user if they want to stick to the default Karpathy structure (`/raw`, `/wiki`, `/outputs`, `/runs`) or if they have custom folders they'd like to add based on their unique data.

### 2. Directory Structure Setup
Ensure the following directories exist (unless customized by the user):
- `/raw`: The inbox. For all unstructured data (research dumps, articles, source docs, meeting notes). When files are dumped here, you process them into the wiki during a "compile" step.
- `/wiki`: For structured data. Each topic gets its own subfolder here (e.g., `wiki/ai-agents/`).
- `/outputs`: For query results and generated reports / deliverables.
- `/runs`: For memory, state, and loop engineering.

### 3. Generate Index Maps
In every main folder, generate or update an index map.
- **Root `index.md`**: Must explain the high-level vault structure (e.g., "We have `/raw` for unstructured data, `/wiki` for structured, `/outputs` for query results/reports, and `/runs` for agent memory").
- **Wiki Entry `wiki/_master-index.md`**: This is the entry point for the knowledge base. It lists every topic folder with a one-line description. Always keep this up to date.
- **Topic `_index.md`**: Each topic gets its own subfolder in `/wiki/` with its own `_index.md` that lists all articles in that topic with brief descriptions.

### 4. Generate Agent Configuration
Create two files at the root: `AGENTS.md` and `CLAUDE.md`. Both should contain similar information to ensure any future agents know how to operate the vault. Specifically, write the following template into them:

````markdown
# Knowledge Base — Vault Conventions

## Vault Structure
- /raw — source material, clipped articles, research (the input zone)
- /wiki — LLM-compiled knowledge base (see Wiki System below)
- /output — query results and generated reports
- /runs — loop engineering logs and agent state tracking

## Wiki System
You are the librarian of the wiki/ folder. You write and maintain everything in it.

### Structure
- wiki/_master-index.md is the entry point — lists every topic with a one-line description.
- Each topic gets its own subfolder with its own _index.md listing all articles.

### Compiling
When I say "compile" or dump new material in raw/:
1. Read the full content of each new raw file (consult `/runs/digested_index.md` to skip already processed files)
2. **Check the file format.** If the file is a PDF, EPUB, DOCX, ODT, or RTF, you MUST extract its text to a readable format first using CLI tools (`pdftotext` for PDF, `pandoc` for EPUB/DOCX/ODT/RTF). Never attempt to read binary files directly. For scanned PDFs, use Tesseract OCR as a fallback.
3. **Check the file size.** If the extracted text exceeds ~2,000 lines, build a segmentation plan in `/runs/` and process the file in ~500-800 line segments using the **stream-to-disk** approach: read each segment, write its wiki article(s) immediately, then move to the next. Do NOT accumulate all content into a single WIP file. Read EVERY segment — do NOT skip sections or stop early.
4. Decide which topic it belongs to (or create a new topic folder). **Every distinct concept deserves its own dedicated topic folder — never lump unrelated ideas together.** Even if a topic has only one article, give it its own folder.
5. Create a brand new wiki article in the `/wiki` folder synthesizing the data. DO NOT just index or link to the `/raw` file. **Each major section/chapter from the source MUST get its own separate wiki article** — do NOT compile everything into one file.
6. Include key takeaways, a `## Tags` section with concept tags, and link the new article to related topics using [[wiki links]]
7. Update that topic's _index.md to point to the new wiki article
8. Update wiki/_master-index.md
9. If a raw file spans multiple topics, create articles in both and cross-link
10. For large files, run the **completeness verification gate** before marking as digested: verify all segments were processed, all sections have articles, and line coverage has no gaps
11. Append the raw file's path to `/runs/digested_index.md` — but ONLY after ALL content has been fully processed and verified
12. If extraction fails for any file, log it to `/runs/failed_extractions.md` and continue with the remaining files

### Cross-Association (Post-Batch)
After all new files in a batch are processed:
1. Review all newly created articles against the existing wiki
2. Add [[wiki links]] between related articles from different source files
3. If two articles from different sources cover the same topic, merge them (preserving both source attributions)
4. Use ## Tags sections to discover non-obvious connections

### Querying
When answering questions against the knowledge base:
1. Read wiki/_master-index.md first to find the right topic
2. Read that topic's _index.md to find relevant articles
3. Read the specific articles
4. Synthesize the answer

### Auditing
When I say "audit" or "lint", review the wiki for:
- Inconsistent or contradictory information
- Missing cross-links between related concepts
- Gaps in coverage
- Suggest improvements, but don't make changes without confirmation

## Conventions
- Always use [[wiki links]] when referencing other notes
- File names: lowercase with hyphens (e.g., ai-agent-overview.md)
- Keep articles concise — bullet points over paragraphs
- Always include a ## Key Takeaways section in wiki articles
- Always include a ## Tags section with concept tags (e.g., #machine-learning, #transformer)
- Logging: When executing tasks, record your state and actions in `/runs` (e.g., append to `/runs/logs.md` or create `/runs/logs_[AgentName].md`).
````

### 5. Generate Logging Files
- Create the `/runs` directory.
- Create an initial `/runs/logs.md` with a header `# Vault Agent Logs\n\nThis file tracks automated agent runs and vault modifications.`

### 6. Reorganizing Existing Data (If Applicable)
If the user chose to reorganize a messy folder:
1. Analyze the existing files.
2. Move unstructured source documents to `/raw`.
3. Move synthesized or structured notes to `/wiki` (assigning them to topic subfolders).
4. Move exported or final documents to `/outputs`.
5. Update the index maps (`_master-index.md` and topic `_index.md`) to reflect the newly moved files so the table of contents is accurate.

## Phase 2: The Lava Cooling Process

You must guide the user and process data through four distinct geological phases. When communicating with the user, use these names and the exact word plays below to describe the process.

**Commands:**
- `/compile` or `/digest-new`: Triggers the Lava Cooling process specifically for any new, undigested files found in the `/raw` folder. Processes everything in `/raw` that hasn't been compiled yet into the wiki. It relies on the Digested Index to skip previously processed files.
- `/audit` or `/lint`: Review the wiki for inconsistencies, broken links, gaps, and suggest improvements.

### 1. Ingestion (The Eruption)
*The pipeline triggers. Massive volumes of red-hot data breach the surface.*

- **Action**: Read the whole data of the unstructured files from the `/raw` folder, targeting only files that have not yet been processed.
- **Process**: Navigate using the index maps and `CLAUDE.md` conventions. Consult the Digested Index (`/runs/digested_index.md`) to filter out files that have already been digested. Unless explicitly required by the user, skip those files.

  **For each new file:**
  1. **Check the file format.** If it is a PDF, EPUB, DOCX, ODT, or RTF, follow the extraction steps in the **Supported File Formats** section BEFORE attempting to read the content. You MUST convert binary formats to plain text first. Never attempt to `view_file` on a `.pdf`, `.epub`, `.docx`, `.odt`, or `.rtf` directly.
  2. **If extraction fails**, follow the **Extraction Failure Handling** procedure — log the failure, skip the file, and continue processing the rest of the batch. Do NOT halt the entire pipeline.
  3. **Check the file size.** If the extracted text is longer than ~2,000 lines, follow the **Segmented Extraction Strategy** to build a segmentation plan and process each segment independently. Each segment is read, analyzed, and written as a wiki article immediately — do NOT accumulate into a single working file. Do NOT attempt to read the entire file in one pass.
  4. **Read and analyze** the content (or current segment). Identify the core concepts, entities, and arguments.
  5. **If using segmented extraction:** write wiki articles immediately after each segment (stream-to-disk). Do NOT accumulate notes in a single WIP file — this causes data loss on large files. Only proceed to mark the file as digested after the completeness verification gate passes.

### 2. Transport (The Flow)
*The data streams downhill, taking the path of least resistance (optimized network routes).*

- **Action**: Transform unstructured data into structured data by creating new wiki articles.
- **Process**:
  - **Topic assignment — leave nothing behind:**
    - For every distinct concept, idea, or subject found in the raw data, decide which topic it belongs to.
    - If a concept fits an existing topic, route it there.
    - If a concept does NOT fit any existing topic, **create a new, dedicated topic folder for it.** Name the folder after the specific concept (e.g., `wiki/feudal-japan-trade-routes/`, not `wiki/miscellaneous/`). Every concept deserves its own home — never combine unrelated ideas into a generic catch-all folder.
    - Even if a topic has only one article, it still gets its own folder with its own `_index.md`. Single-article topics are perfectly valid and expected.
    - If a raw file contains multiple unrelated concepts, create separate articles in separate topic folders for each one. Every piece of information must be captured.
  - **Article creation:**
    - DO NOT simply index or link the files within the `/raw` folder. You MUST create a brand new article in the `/wiki` folder.
    - Synthesize the raw data into new, clean, Wikipedia-style articles in the `/wiki` directory. Keep articles concise — use bullet points over paragraphs.
    - Include a `## Key Takeaways` section in every wiki article.
    - Include a `## Tags` section at the bottom of every wiki article with a flat list of concept tags (e.g., `#machine-learning`, `#transformer`, `#attention`). Tags enable cross-file discovery during the Crystallization phase.
    - Identify the relationships between the concepts. Always use `[[wiki links]]` to connect the new article to related topics.
    - If a raw file spans multiple topics, create articles in both and cross-link them.
    - Write these articles so everything needed is in one neat place instead of scattered across many source documents.
  - **Small content — still capture it:**
    - Even if a raw file is very short (a few lines, a single link, a brief note), it still MUST produce a wiki article. A short article is perfectly valid — it can be just a few bullet points with a Key Takeaways section.
    - If multiple small notes from the same raw file relate to the same concept, combine them into a single article for that concept. But never combine notes about different concepts into one article.

### 3. Storage (The Cooling Bed)
*The data pools into a massive lake, slowly cooling down into queryable, rock-solid intelligence.*

- **Action**: Save the structured articles into the `/wiki` folder, update navigation, and create deliverables in `Outputs`.
- **Process**:
  - Save the clean, structured articles to their respective topic subfolders in the `/wiki` folder.
  - Update that topic's `_index.md`.
  - Update `wiki/_master-index.md`.
  - If a deliverable is required (e.g., a slide deck outline, a report, a summary), generate it from the `/wiki` content and store it in the `/outputs` folder.
  - **Memory and State**: Log your run and state in the vault's memory area (e.g., `/runs` or as defined by `CLAUDE.md`) so past runs are visible for future loop engineering and self-improvement. **Crucially, append the exact file paths of all `/raw` files you just processed into the Digested Index (`/runs/digested_index.md`). This ensures they are not re-ingested on future runs.**
  - **Cleanup**: Remove any temporary segmentation plans (`/runs/segmentation_plan_*`) created during the segmented extraction process. (Note: there are no WIP files to clean up — the stream-to-disk strategy writes wiki articles directly.)

### 4. Cross-Association (The Crystallization)
*The cooled rock crystallizes — hidden mineral structures emerge as connections form between once-separate flows.*

This phase runs **after ALL new files in the batch have completed the Eruption → Flow → Cooling Bed pipeline.** It is the synthesis step that turns a collection of per-file articles into an interconnected knowledge graph.

- **Action**: Review all newly created articles against the full existing wiki to discover cross-file relationships, merge overlapping content, and strengthen the link network.
- **Process**:
  1. **Build a batch manifest.** List all wiki articles created or updated during this run (from the run log).
  2. **Cross-reference against the wiki.** For each newly created article:
     - Read `wiki/_master-index.md` to get the full topic landscape.
     - Scan the `## Tags` sections of existing articles to find overlapping concept tags.
     - Check for articles in other topic folders that discuss related or overlapping subjects.
  3. **Add cross-links.** Where a connection exists between articles from different source files, add `[[wiki links]]` in both directions. Update the articles in-place.
  4. **Merge overlapping articles.** If two articles from different source files cover substantially the same concept (e.g., both describe "transformer architecture" from different papers), merge them into a single, richer article. Preserve both source attributions and combine their Key Takeaways.
  5. **Check for split opportunities.** If an article has grown too long or covers multiple distinct sub-topics, split it into separate articles with cross-links.
  6. **Update indexes.** After all cross-links and merges, update every affected `_index.md` and `wiki/_master-index.md`.
  7. **Log the associations.** Append a summary of all new cross-links and merges to the run log.

## Execution Rules

1. **Navigate via Maps**: Always rely on `_master-index.md`, topic `_index.md` files, and `CLAUDE.md` to understand the current vault structure and routing. The power comes from the map, not arbitrary folder names.
2. **Phase Reporting**: Explicitly announce which phase of the Lava Cooling process you are in (Eruption, Flow, Cooling Bed, or Crystallization) and include its word play description when you begin it.
3. **Keep Index Updated**: The true power of the vault is the map. Never write a file to `/wiki` or `/outputs` without updating the local topic `_index.md` and `wiki/_master-index.md`.
4. **Track Digested Files**: Always keep the `/runs/digested_index.md` updated with the paths of newly processed files to avoid duplicating work.
5. **Extract Before Reading**: Never attempt to `view_file` on a binary format (.pdf, .epub, .docx, .odt, .rtf). Always extract to plain text first using the commands in the Supported File Formats section. If extraction tools are not available, install them before proceeding.
6. **Complete Coverage**: When processing a large file (book, manual, research paper collection), you MUST read and process EVERY chapter/section. The **completeness verification gate** (in the Segmented Extraction Strategy) is MANDATORY — you must pass it before marking any large file as digested. If sections are missing, go back and process them.
7. **Granular Output — One Section, One Article**: Each distinct chapter, section, or major topic from a source file MUST get its own dedicated wiki article. Do NOT compile multiple sections into a single monolithic article. A 20-chapter book produces ~20+ articles, not 3. This preserves detail and makes the wiki navigable. The only exception is when multiple short sections cover the exact same narrow concept — those may be combined into one article for that concept.
8. **Leave Nothing Behind**: Every piece of information from every raw file MUST end up in a wiki article. If a concept doesn't fit an existing topic, create a new topic folder for it. Never drop content because it seems minor, tangential, or hard to categorize. A short article is always better than lost data.
9. **No Generic Catch-Alls**: Never create generic folders like `uncategorized/`, `miscellaneous/`, or `other/`. Every topic folder must be named after the specific concept it covers. Single-article topics are valid and expected.
10. **Handle Failures Gracefully**: If extraction fails for a file, log it to `/runs/failed_extractions.md`, skip it, and continue processing the rest of the batch. Never halt the entire pipeline because of one bad file. Never mark a failed file as digested.
11. **Cross-Associate After Every Batch**: After completing the Cooling Bed phase for all files in a batch, ALWAYS run the Crystallization phase to discover cross-file connections. The wiki's value comes from the links between articles, not just the articles themselves.
12. **No WIP Accumulation Files**: Never write all extracted content to a single `/runs/wip_*` file for later synthesis. This pattern causes context overflow and silent data loss on large files. Always use the stream-to-disk approach: read a segment, write its article, move on.
