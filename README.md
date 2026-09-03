# Lava Extruder Skill

<img width="2752" height="1536" src="https://github.com/user-attachments/assets/4bfcfc4d-752c-4cb4-aa16-3e842e789aed" />

This plugin provides the `lava-extruder` skill for Antigravity, Gemini, and Claude agents. It allows an AI agent to automatically scaffold an AI-optimized Obsidian vault based on the "Karpathy RAG" architecture.

## Features

- **Automated Directory Scaffolding**: Creates `/raw`, `/wiki`, `/outputs`, and `/runs` folders, or customizes them to your needs.
- **Index Maps (`index.md`)**: Automatically generates a "table of contents" in every directory so agents can navigate your vault programmatically.
- **Agent Instructions (`AGENTS.md` / `CLAUDE.md`)**: Injects guidelines documenting vault conventions, folder structures, and search navigation patterns.
- **Loop Engineering Logs**: Sets up a `/runs` directory with log files where agents can leave state and track past runs for self-improvement.

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

Once installed, just navigate to any folder you'd like to turn into a vault and tell your agent:
> *"Set up my Obsidian vault here."*
> *"Trigger the lava extruder here."*

Or, if you have an existing messy folder:
> *"Reorganize this messy folder into a Karpathy RAG vault using the lava-extruder skill."*
