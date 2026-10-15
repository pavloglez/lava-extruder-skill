# Lava Extruder Skill

<img width="2752" height="1536" src="https://github.com/user-attachments/assets/4bfcfc4d-752c-4cb4-aa16-3e842e789aed" />

This plugin provides the `lava-extruder` skill for Antigravity, Gemini, and Claude agents. It allows an AI agent to automatically scaffold an AI-optimized Obsidian vault based on the "Karpathy RAG" architecture.

## Features

- **Automated Directory Scaffolding**: Creates `/raw`, `/wiki`, `/outputs`, and `/runs` folders, or customizes them to your needs. Also writes `SCHEMA.md` (the vault governance contract), `runs/hot.md` (session continuity cache), and self-contained `AGENTS.md`/`CLAUDE.md`/`GEMINI.md` so any agent can run the vault.
- **`--git` option**: `lava-extruder init <dir> --git` also runs `git init` so every digest batch has an undo point and temporal history.
- **Index Maps (`index.md`)**: Automatically generates a "table of contents" in every directory so agents can navigate your vault programmatically.
- **Agent Instructions (`AGENTS.md` / `CLAUDE.md`)**: Injects comprehensive guidelines documenting vault conventions, folder structures, and search navigation patterns.
- **Lava Cooling Process (Data Pipeline)**: An automated four-phase process (Eruption, Flow, Cooling Bed, Crystallization) that ingests raw documents, structures them into Wikipedia-style articles, cross-links related content across sources, and outputs deliverables.
- **Automated Compilation**: Use the `/compile` or `/digest-new` commands to automatically read undigested files from `/raw`, synthesize them, and route them to the correct `/wiki` topics.
- **Querying**: `/query <question>` answers from the compiled wiki with `[[wiki link]]` citations, respecting `confidence`/`contested` frontmatter flags, and files substantial answers to `outputs/queries/`.
- **Wiki Auditing**: Use the `/audit` or `/lint` commands to review your knowledge base for inconsistencies, broken links, or gaps — or run `lava-extruder lint <vault_dir>` directly for a deterministic, no-LLM integrity check.
- **Loop Engineering Logs**: Sets up a `/runs` directory with log files (like `digested_index.md`) where agents can leave state, track past runs, and prevent duplicate processing.
- **Representation, Not Micro-paging**: Every substantive concept gets representation in the wiki; minor mentions fold into existing articles instead of minting micro-pages, keeping the graph navigable (see Page Thresholds).
- **Segmented Extraction (Stream-to-disk)**: Safely processes massive documents (thousands of lines) by extracting and writing wiki articles segment-by-segment immediately. It **does not** accumulate large files into a single context-breaking WIP file, preventing silent data loss.
- **Completeness Verification Gate**: Automatically audits section and line coverage to ensure 100% completeness before marking any large file as fully digested.
- **Page Thresholds**: Articles are created only when a concept is central to a source or appears in 2+ sources; minor mentions fold into existing articles; articles over ~200 lines get split. No `misc/` catch-alls.
- **Cross-File Association**: After processing a batch, the Crystallization phase automatically discovers connections between articles from different sources, adds bidirectional cross-links, merges duplicates, and splits overgrown articles.

## Supported Formats

Lava Extruder features a **Universal Document Ingestion Pipeline** inspired by Microsoft MarkItDown with local-first, zero-cost fallbacks:

| Category | Format | Primary Method | Fallback(s) |
|---|---|---|---|
| **Universal** | *Any supported file* | `extract_raw.py` | Auto-detects & dispatches to specialized converters |
| **Presentations** | `.pptx` | `extract_pptx.py` (`python-pptx`) | LibreOffice headless → pdftotext |
| **Spreadsheets** | `.xlsx`, `.xls` | `extract_xlsx.py` (`openpyxl`) | `pandas` → stdlib XML parser → LibreOffice |
| **Spreadsheets** | `.csv`, `.tsv` | `extract_raw.py` (streamed Markdown table) | Direct read |
| **Notebooks** | `.ipynb` | `extract_ipynb.py` (stdlib `json`) | Zero external dependencies |
| **Documents** | `.pdf` | `extract_pdf.sh` (table-aware `pdfplumber`/`markitdown`) | Poppler `pdftotext` → `PyMuPDF` → Tesseract OCR |
| **Books** | `.epub` | `extract_epub.py` (stdlib spine & Dublin Core metadata) | `pandoc` |
| **Documents** | `.docx`, `.odt`, `.rtf` | `extract_docx.sh` (`pandoc`) | `mammoth` → `python-docx` → LibreOffice |
| **Web Pages** | `.html`, `.htm` | `extract_html.py` (`markdownify` / `bs4`) | Built-in HTMLParser (strips script/styles) |
| **Archives** | `.zip` | `extract_zip.py` (stdlib `zipfile`) | Recursive inner extraction & synthesis |
| **Emails** | `.msg`, `.eml` | `extract_email.py` (`olefile` / stdlib `email`) | Extracts headers, body, & attachment lists |
| **Audio** | `.mp3`, `.wav`, `.m4a`, `.mp4` | `extract_audio.py` (OpenAI Whisper) | `SpeechRecognition` → `ffmpeg` metadata |
| **Images** | `.png`, `.jpg`, `.jpeg`, `.webp` | `extract_image.sh` (Tesseract OCR) | Dimension & date metadata |
| **Plain Text** | `.md`, `.txt`, `.json`, `.yaml` | Direct read / copy | — |

Scanned/image-only PDFs and standalone image notes are automatically OCR'd. If extraction fails for any file, it is logged to `/runs/failed_extractions.md` and the pipeline continues.

## Installation

You have two options for installing this plugin: automatically via NPX, or manually via Git clone.

### Option 1: Install automatically via NPX (Recommended)

If you have Node.js installed, you can instantly install the plugin to your global configuration directory using NPX:

```bash
npx lava-extruder
```

### Option 2: Install manually via Git Clone

If you prefer to clone the repository manually, simply place it in your agent's global plugin configuration folder:

1. Navigate to your agent's global plugin directory:
   ```bash
   cd ~/.gemini/config/plugins/
   # If the directory doesn't exist, create it first: mkdir -p ~/.gemini/config/plugins/ && cd ~/.gemini/config/plugins/
   ```

2. Clone this repository directly into the folder:
   ```bash
   git clone https://github.com/<your-username>/lava-extruder-plugin.git
   ```

3. Start your agent. The plugin will be automatically discovered and enabled!

## Usage

### Scaffolding a Vault

Once installed, just navigate to any folder you'd like to turn into a vault and tell your agent:
> *"Set up my Obsidian vault here."*
> *"Trigger the lava extruder here."*

Or, if you have an existing messy folder:
> *"Reorganize this messy folder into a Karpathy RAG vault using the lava-extruder skill."*

The agent will scaffold the folders, write `SCHEMA.md` (customized to your domain), `AGENTS.md`/`CLAUDE.md`/`GEMINI.md`, index maps, and the session hot cache. Use `lava-extruder init ./my-vault --git` if you want git history on every digest batch.

### Compiling Knowledge

Once your vault is set up and you've dumped source materials into the `/raw` folder, trigger the data processing pipeline:
> *"/compile"* or *"/digest-new"*

This triggers the "Lava Cooling Process", which will ingest the new documents, synthesize them into structured wiki articles in `/wiki`, cross-link related content from different sources, and prevent re-processing them in the future (digested files are tracked by path **and SHA-256** in `/runs/digested_index.md`, so re-drops are skipped and changed sources are flagged as drift).

### Auditing the Vault

To review your compiled knowledge base for gaps, inconsistencies, or missing cross-links:
> *"/audit"* or *"/lint"*

## CLI & CI/CD Tooling

Lava Extruder provides both conversational agent skill triggers and direct command-line tools for CI/CD pipelines:

```bash
# Initialize / scaffold a Karpathy RAG vault directly
lava-extruder init ./my-vault
# Same, plus git init for digest-batch history
lava-extruder init ./my-vault --git

# Extract any supported document format to Markdown
lava-extract raw/architecture-whitepaper.pdf
# or:
lava-extruder extract raw/metrics.xlsx

# Inspect structural markers & plan large file segmentation
lava-extruder count raw/book.extracted.md

# Deterministic vault integrity lint
lava-extruder lint ./my-vault
```

## Running Tests

Verify the extraction suite and vault scaffolding:

```bash
npm test
```

## Helper Scripts Catalog

The skill includes modular, local-first extractors in `skills/lava-extruder/scripts/`:

| Script | Purpose |
|--------|---------|
| `extract_raw.py` | **Universal Master Dispatcher** (`lava-extract`) — auto-detects and converts any file |
| `extract_pdf.sh` | PDF → text/tables (`pdfplumber` / `markitdown` → `pdftotext` → `PyMuPDF` → Tesseract OCR) |
| `extract_epub.py` | EPUB → structured markdown (stdlib spine order + Dublin Core metadata + pandoc fallback) |
| `extract_docx.sh` | DOCX/ODT/RTF → markdown (`pandoc` → `mammoth` → `python-docx` → LibreOffice) |
| `extract_pptx.py` | PowerPoint → markdown (slides, notes, tables, charts via `python-pptx`) |
| `extract_xlsx.py` | Spreadsheets → markdown tables (`openpyxl` → `pandas` → stdlib XML) |
| `extract_ipynb.py` | Jupyter Notebooks → markdown (stdlib `json`, code & markdown blocks) |
| `extract_html.py` | Web pages → clean markdown (strips scripts, styles, boilerplate) |
| `extract_zip.py` | ZIP archives → sandboxed recursive extraction & synthesis with zip-slip guard |
| `extract_email.py` | Emails (.msg, .eml) → markdown (headers, message body, attachments) |
| `extract_audio.py` | Audio transcription (OpenAI Whisper → `SpeechRecognition` → `ffmpeg`) |
| `extract_image.sh` | Image OCR & metadata (Tesseract OCR + dimensions/dates) |
| `count_sections.sh` | Count structural markers for segmentation plans |
| `lint_vault.py` | Deterministic vault integrity lint (`lava-extruder lint`) |

