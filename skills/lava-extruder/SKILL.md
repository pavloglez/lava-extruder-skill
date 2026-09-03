---
name: lava-extruder
description: Sets up an AI-optimized Obsidian vault folder structure with index.md waypoints and AGENTS.md/CLAUDE.md instructions. Can create vaults from scratch or reorganize existing messy folders.
---

# Obsidian Vault Setup Skill

You are an expert at creating and organizing AI-native Obsidian vaults. Your goal is to establish a folder structure that optimizes knowledge retrieval for AI agents using the "Karpathy RAG" method.

## Core Concepts

The power of this vault is NOT just the folders, it is the map. AI agents navigate the vault using:
1. **Top-level Agent instructions** (`AGENTS.md` and `CLAUDE.md`) that document conventions and the navigation pattern.
2. **`index.md` files** in every folder that act as a map and table of contents for that specific level, telling the AI exactly what it's looking at and where to go deeper.
3. **Loop Engineering Logs** in the `/runs` folder where agents can leave state and track past runs.

## Workflow

### 1. Assess the Vault
When invoked, first check the current directory:
- If the directory is mostly empty, proceed with **Creating from Scratch**.
- If the directory has existing messy data, ask the user if they want to **Reorganize** their existing data into the new structure or just create the new structure alongside it.
- Ask the user if they want to stick to the default Karpathy structure (`/raw`, `/wiki`, `/outputs`, `/runs`) or if they have custom folders they'd like to add based on their unique data.

### 2. Directory Structure Setup
Ensure the following directories exist (unless customized by the user):
- `/raw`: For all unstructured data (research dumps, articles, source docs, meeting notes).
- `/wiki`: For structured data (clean, Wikipedia-style articles synthesizing the raw data).
- `/outputs`: For deliverables (slide decks, reports, final products).
- `/runs`: For memory, state, and loop engineering.

### 3. Generate `index.md` Maps
In every folder (and the root), generate or update an `index.md`.
- **Root `index.md`**: Must explain the high-level vault structure (e.g., "We have `/raw` for unstructured data, `/wiki` for structured, `/outputs` for deliverables, and `/runs` for agent memory").
- **Folder `index.md`**: Must describe what kind of files are in this folder, sub-folders, and provide a table of contents to quickly route agents to the right documents.

### 4. Generate Agent Configuration
Create two files at the root: `AGENTS.md` and `CLAUDE.md`. Both should contain similar information:
- A clear explanation of the vault's folder structure.
- The **Navigation Pattern**: "When looking for information, ALWAYS start by reading the root `index.md`, then navigate to the relevant folder and read its `index.md` to find the exact file path."
- Instructions for logging: "When executing tasks or processing data, record your state, discoveries, and actions in the `/runs` folder. You may append to `/runs/logs.md` or create your own agent-specific log at `/runs/logs_[AgentName].md`. This allows for loop engineering and self-improvement by reflecting on past runs."

### 5. Generate Logging Files
- Create the `/runs` directory.
- Create an initial `/runs/logs.md` with a header `# Vault Agent Logs\n\nThis file tracks automated agent runs and vault modifications.`

### 6. Reorganizing Existing Data (If Applicable)
If the user chose to reorganize a messy folder:
1. Analyze the existing files.
2. Move unstructured source documents to `/raw`.
3. Move synthesized or structured notes to `/wiki`.
4. Move exported or final documents to `/outputs`.
5. Update the `index.md` files in each folder to reflect the newly moved files so the table of contents is accurate.
