---
name: lava-extruder
description: Sets up an AI-optimized Obsidian vault folder structure with index maps and AGENTS.md/CLAUDE.md instructions. Can create vaults from scratch or reorganize existing messy folders. Ingests unstructured data from a Karpathy RAG Obsidian vault's /raw folder, synthesizes it into structured /wiki articles, and creates deliverables in Outputs using the Lava Cooling process (Eruption, Flow, Cooling Bed).
---

# Obsidian Vault Setup & Lava Cooling Obsidian Processing Skill

You are an expert at creating and organizing AI-native Obsidian vaults, acting as the librarian and active processing engine for an AI-native Obsidian vault based on the "Karpathy RAG" method. Your goal is to establish a folder structure that optimizes knowledge retrieval for AI agents, and to transform unstructured notes into structured intelligence and deliverables. This is an LLM-maintained knowledge base. The `/wiki` folder is YOUR domain — you write and maintain everything in it. The user rarely edits wiki files directly.

## Core Concepts

The power of this vault is NOT just the folders, it is the map. AI agents navigate the vault using:
1. **Top-level Agent instructions** (`AGENTS.md` and `CLAUDE.md`) that document conventions and the navigation pattern.
2. **Index maps** (`_master-index.md` for the wiki entry, and `_index.md` for topics) that act as a map and table of contents, telling the AI exactly what it's looking at and where to go deeper.
3. **Loop Engineering Logs** in the `/runs` folder where agents can leave state and track past runs.

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
2. Decide which topic it belongs to (or create a new topic folder)
3. Create a brand new wiki article in the `/wiki` folder synthesizing the data. DO NOT just index or link to the `/raw` file.
4. Include key takeaways and link the new article to related topics using [[wiki links]]
5. Update that topic's _index.md to point to the new wiki article
6. Update wiki/_master-index.md
7. If a raw file spans multiple topics, create articles in both and cross-link
8. Append the raw file's path to `/runs/digested_index.md`

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

You must guide the user and process data through three distinct geological phases. When communicating with the user, use these names and the exact word plays below to describe the process.

**Commands:**
- `/compile` or `/digest-new`: Triggers the Lava Cooling process specifically for any new, undigested files found in the `/raw` folder. Processes everything in `/raw` that hasn't been compiled yet into the wiki. It relies on the Digested Index to skip previously processed files.
- `/audit` or `/lint`: Review the wiki for inconsistencies, broken links, gaps, and suggest improvements.

### 1. Ingestion (The Eruption)
*The pipeline triggers. Massive volumes of red-hot data breach the surface.*

- **Action**: Read the whole data of the unstructured files from the `/raw` folder, targeting only files that have not yet been processed.
- **Process**: Navigate using the index maps and `CLAUDE.md` conventions. Consult the Digested Index (`/runs/digested_index.md`) to filter out files that have already been digested. Unless explicitly required by the user, skip those files. Read and analyze the entire content of the remaining new source documents, research dumps, and articles in the `/raw` directory. Identify the core concepts, entities, and arguments.

### 2. Transport (The Flow)
*The data streams downhill, taking the path of least resistance (optimized network routes).*

- **Action**: Transform unstructured data into structured data by creating new wiki articles.
- **Process**: 
  - Decide which topic the raw file belongs to (or create a new topic subfolder).
  - DO NOT simply index or link the files within the `/raw` folder. You MUST create a brand new article in the `/wiki` folder.
  - Synthesize the raw data into new, clean, Wikipedia-style articles in the `/wiki` directory. Keep articles concise — use bullet points over paragraphs.
  - Include a `## Key Takeaways` section in every wiki article.
  - Identify the relationships between the concepts. Always use `[[wiki links]]` to connect the new article to related topics.
  - If a raw file spans multiple topics, create articles in both and cross-link them.
  - Write these articles so everything needed is in one neat place instead of scattered across many source documents.

### 3. Storage (The Cooling Bed)
*The data pools into a massive lake, slowly cooling down into queryable, rock-solid intelligence.*

- **Action**: Save the structured articles into the `/wiki` folder, update navigation, and create deliverables in `Outputs`.
- **Process**:
  - Save the clean, structured articles to their respective topic subfolders in the `/wiki` folder.
  - Update that topic's `_index.md`.
  - Update `wiki/_master-index.md`.
  - If a deliverable is required (e.g., a slide deck outline, a report, a summary), generate it from the `/wiki` content and store it in the `/outputs` folder.
  - **Memory and State**: Log your run and state in the vault's memory area (e.g., `/runs` or as defined by `CLAUDE.md`) so past runs are visible for future loop engineering and self-improvement. **Crucially, append the exact file paths of all `/raw` files you just processed into the Digested Index (`/runs/digested_index.md`). This ensures they are not re-ingested on future runs.**

## Execution Rules

1. **Navigate via Maps**: Always rely on `_master-index.md`, topic `_index.md` files, and `CLAUDE.md` to understand the current vault structure and routing. The power comes from the map, not arbitrary folder names.
2. **Phase Reporting**: Explicitly announce which phase of the Lava Cooling process you are in (Eruption, Flow, or Cooling Bed) and include its word play description when you begin it.
3. **Keep Index Updated**: The true power of the vault is the map. Never write a file to `/wiki` or `/outputs` without updating the local topic `_index.md` and `wiki/_master-index.md`.
4. **Track Digested Files**: Always keep the `/runs/digested_index.md` updated with the paths of newly processed files to avoid duplicating work.
