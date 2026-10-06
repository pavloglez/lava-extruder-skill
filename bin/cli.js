#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

const SCRIPT_DIR = path.join(__dirname, '..', 'skills', 'lava-extruder', 'scripts');
const EXTRACT_SCRIPT = path.join(SCRIPT_DIR, 'extract_raw.py');
const COUNT_SCRIPT = path.join(SCRIPT_DIR, 'count_sections.sh');

function printHelp() {
  console.log(`
🌋 Lava Extruder CLI — Universal Document Ingestion & Obsidian Vault Scaffolding

Usage:
  lava-extruder extract <input_file> [output_file]  Extract any document to Markdown
  lava-extruder count <file>                        Count structural markers & chunk plan
  lava-extruder init [vault_dir]                    Scaffold Karpathy RAG vault folders & maps
  lava-extruder install [--target <target>]         Install plugin (gemini, claude, all)
  lava-extruder --help                              Show this help menu
`);
}

function handleExtract(args) {
  if (args.length === 0) {
    console.error('Error: Missing input file for extraction.\nUsage: lava-extruder extract <input_file> [output_file]');
    process.exit(1);
  }
  const proc = spawnSync('python3', [EXTRACT_SCRIPT, ...args], { stdio: 'inherit' });
  process.exit(proc.status || 0);
}

function handleCount(args) {
  if (args.length === 0) {
    console.error('Error: Missing input file for section counting.\nUsage: lava-extruder count <input_file>');
    process.exit(1);
  }
  const proc = spawnSync('bash', [COUNT_SCRIPT, ...args], { stdio: 'inherit' });
  process.exit(proc.status || 0);
}

function handleInit(args) {
  const vaultDir = path.resolve(args[0] || process.cwd());
  console.log(`🌋 Scaffolding Karpathy RAG Obsidian Vault at: ${vaultDir}`);

  const dirs = ['raw', 'wiki', 'outputs', 'runs'];
  for (const d of dirs) {
    const full = path.join(vaultDir, d);
    if (!fs.existsSync(full)) {
      fs.mkdirSync(full, { recursive: true });
      console.log(`  Created folder: /${d}`);
    }
  }

  // Root index.md
  const rootIndex = path.join(vaultDir, 'index.md');
  if (!fs.existsSync(rootIndex)) {
    fs.writeFileSync(rootIndex, `# Vault Navigation Map\n\n- [[raw/|Raw Inbox]] — Unstructured source data\n- [[wiki/_master-index|Wiki Knowledge Base]] — Crystallized, LLM-maintained intelligence\n- [[outputs/|Outputs]] — Generated deliverables and synthesis reports\n- [[runs/logs|Agent Runs]] — Memory, state, and loop engineering logs\n`, 'utf-8');
    console.log('  Created: index.md');
  }

  // Master index
  const masterIndex = path.join(vaultDir, 'wiki', '_master-index.md');
  if (!fs.existsSync(masterIndex)) {
    fs.writeFileSync(masterIndex, `# Master Knowledge Index\n\nEntry point for the knowledge base. Topic subfolders are listed below.\n\n| Topic | Description | Articles |\n|---|---|---|\n`, 'utf-8');
    console.log('  Created: wiki/_master-index.md');
  }

  // Runs logs and digested index
  const runLog = path.join(vaultDir, 'runs', 'logs.md');
  if (!fs.existsSync(runLog)) {
    fs.writeFileSync(runLog, `# Vault Agent Logs\n\nThis file tracks automated agent runs and vault modifications.\n`, 'utf-8');
    console.log('  Created: runs/logs.md');
  }

  const digestedIndex = path.join(vaultDir, 'runs', 'digested_index.md');
  if (!fs.existsSync(digestedIndex)) {
    fs.writeFileSync(digestedIndex, `# Digested Files Index\n\nTracks raw files fully processed into the wiki.\n\n`, 'utf-8');
    console.log('  Created: runs/digested_index.md');
  }

  // AGENTS.md & CLAUDE.md
  const agentRules = `# Knowledge Base — Vault Conventions

## Vault Structure
- /raw — source material, clipped articles, research (the input zone)
- /wiki — LLM-compiled knowledge base
- /outputs — query results and generated reports
- /runs — loop engineering logs and agent state tracking

## Wiki System
You are the librarian of the wiki/ folder. You write and maintain everything in it.
- wiki/_master-index.md is the entry point — lists every topic with a one-line description.
- Each topic gets its own subfolder with its own _index.md listing all articles.

## Compiling (The Lava Cooling Process)
When I say "compile", "/compile", or dump new material in raw/:
1. Consult /runs/digested_index.md to skip already processed files.
2. For binary/non-text files, extract to clean Markdown first using \`lava-extract "<raw_file_path>"\`.
3. If extracted text exceeds ~2,000 lines, build a segmentation plan in /runs/ and process in ~500-800 line segments stream-to-disk.
4. Route each distinct concept into its own topic folder in wiki/ with standard YAML frontmatter.
5. Cross-link related topics using [[wiki links]].
6. Verify line and section completeness before adding the file to /runs/digested_index.md.
`;

  const agentsPath = path.join(vaultDir, 'AGENTS.md');
  if (!fs.existsSync(agentsPath)) {
    fs.writeFileSync(agentsPath, agentRules, 'utf-8');
    console.log('  Created: AGENTS.md');
  }

  const claudePath = path.join(vaultDir, 'CLAUDE.md');
  if (!fs.existsSync(claudePath)) {
    fs.writeFileSync(claudePath, agentRules, 'utf-8');
    console.log('  Created: CLAUDE.md');
  }

  console.log('\n✅ Vault scaffolding complete!');
}

function handleInstall(args) {
  const installScript = path.join(__dirname, '..', 'install.js');
  const proc = spawnSync('node', [installScript, ...args], { stdio: 'inherit' });
  process.exit(proc.status || 0);
}

function main() {
  const args = process.argv.slice(2);
  const command = args[0];

  if (!command || command === 'install') {
    handleInstall(args.slice(1));
  } else if (command === 'extract') {
    handleExtract(args.slice(1));
  } else if (command === 'count') {
    handleCount(args.slice(1));
  } else if (command === 'init' || command === 'scaffold') {
    handleInit(args.slice(1));
  } else if (command === '--help' || command === '-h' || command === 'help') {
    printHelp();
  } else {
    // If first argument is a file that exists, treat as extraction shortcut
    if (fs.existsSync(command)) {
      handleExtract(args);
    } else {
      console.error(`Unknown command: ${command}`);
      printHelp();
      process.exit(1);
    }
  }
}

main();
