# Obsidian Vault Setup Plugin

This plugin provides the `obsidian-vault-setup` skill for Antigravity, Gemini, and Claude agents. It allows an AI agent to automatically scaffold an AI-optimized Obsidian vault based on the "Karpathy RAG" architecture.

## Features

- **Automated Directory Scaffolding**: Creates `/raw`, `/wiki`, `/outputs`, and `/runs` folders, or customizes them to your needs.
- **Index Maps (`index.md`)**: Automatically generates a "table of contents" in every directory so agents can navigate your vault programmatically.
- **Agent Instructions (`AGENTS.md` / `CLAUDE.md`)**: Injects guidelines documenting vault conventions, folder structures, and search navigation patterns.
- **Loop Engineering Logs**: Sets up a `/runs` directory with log files where agents can leave state and track past runs for self-improvement.

## Installation

You can install this plugin globally on your machine so that it's available for all your projects.

1. Navigate to your agent's global plugin configuration folder:
   ```bash
   cd ~/.gemini/config/plugins/
   # If the plugins directory does not exist, create it: mkdir -p ~/.gemini/config/plugins/ && cd ~/.gemini/config/plugins/
   ```

2. Clone this repository directly into the plugins folder:
   ```bash
   git clone https://github.com/<your-username>/obsidian-vault-setup-plugin.git
   ```

3. Start your agent. The plugin will be automatically discovered and enabled!

## Usage

Once installed, just navigate to any folder you'd like to turn into a vault and tell your agent:
> *"Set up my Obsidian vault here."*

Or, if you have an existing messy folder:
> *"Reorganize this messy folder into a Karpathy RAG vault using the obsidian-vault-setup skill."*
