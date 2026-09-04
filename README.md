# Lava Extruder Skill

<img width="2752" height="1536" src="https://github.com/user-attachments/assets/4bfcfc4d-752c-4cb4-aa16-3e842e789aed" />

This plugin provides the `lava-extruder` skill for Antigravity, Gemini, and Claude agents. It allows an AI agent to automatically scaffold an AI-optimized Obsidian vault based on the "Karpathy RAG" architecture.

## Features

- **Automated Directory Scaffolding**: Creates `/raw`, `/wiki`, `/outputs`, and `/runs` folders, or customizes them to your needs.
- **Index Maps (`index.md`)**: Automatically generates a "table of contents" in every directory so agents can navigate your vault programmatically.
- **Agent Instructions (`AGENTS.md` / `CLAUDE.md`)**: Injects comprehensive guidelines documenting vault conventions, folder structures, and search navigation patterns.
- **Lava Cooling Process (Data Pipeline)**: An automated four-phase process (Eruption, Flow, Cooling Bed, Crystallization) that ingests raw documents, structures them into Wikipedia-style articles, cross-links related content across sources, and outputs deliverables.
- **Automated Compilation**: Use the `/compile` or `/digest-new` commands to automatically read undigested files from `/raw`, synthesize them, and route them to the correct `/wiki` topics.
- **Wiki Auditing**: Use the `/audit` or `/lint` commands to review your knowledge base for inconsistencies, broken links, or gaps.
- **Loop Engineering Logs**: Sets up a `/runs` directory with log files (like `digested_index.md`) where agents can leave state, track past runs, and prevent duplicate processing.
- **Leave Nothing Behind**: Every concept, no matter how small or tangential, gets its own dedicated topic folder and article. Nothing is dropped or lumped into generic catch-all categories.
- **Segmented Extraction (Stream-to-disk)**: Safely processes massive documents (thousands of lines) by extracting and writing wiki articles segment-by-segment immediately. It **does not** accumulate large files into a single context-breaking WIP file, preventing silent data loss.
- **Completeness Verification Gate**: Automatically audits section and line coverage to ensure 100% completeness before marking any large file as fully digested.
- **Cross-File Association**: After processing a batch of files, the Crystallization phase automatically discovers connections between articles from different sources, adds cross-links, and merges overlapping content.

## Supported Formats

| Format | Method | Fallback |
|--------|--------|----------|
| `.md`, `.txt`, `.csv`, `.json`, `.html` | Direct read | — |
| `.pdf` | `pdftotext` | PyMuPDF → Tesseract OCR |
| `.epub` | `pandoc` | `ebooklib` |
| `.docx`, `.odt`, `.rtf` | `pandoc` | LibreOffice headless |

Scanned/image-only PDFs are automatically detected and processed via OCR. If extraction fails for any file, it is logged to `/runs/failed_extractions.md` and the pipeline continues.

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

### Compiling Knowledge

Once your vault is set up and you've dumped source materials into the `/raw` folder, trigger the data processing pipeline:
> *"/compile"* or *"/digest-new"*

This triggers the "Lava Cooling Process", which will ingest the new documents, synthesize them into structured wiki articles in `/wiki`, cross-link related content from different sources, and prevent re-processing them in the future.

### Auditing the Vault

To review your compiled knowledge base for gaps, inconsistencies, or missing cross-links:
> *"/audit"* or *"/lint"*

## Helper Scripts

The skill includes extraction scripts in `skills/lava-extruder/scripts/`:

| Script | Purpose |
|--------|---------|
| `extract_pdf.sh` | PDF → text (pdftotext → PyMuPDF → Tesseract OCR) |
| `extract_epub.sh` | EPUB → markdown (pandoc → ebooklib) |
| `extract_docx.sh` | DOCX/ODT/RTF → markdown (pandoc → LibreOffice) |
| `count_sections.sh` | Count structural markers for segmentation plans |
