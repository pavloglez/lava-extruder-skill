#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

const SCRIPT_DIR = path.join(__dirname, '..', 'skills', 'lava-extruder', 'scripts');
const EXTRACT_SCRIPT = path.join(SCRIPT_DIR, 'extract_raw.py');
const COUNT_SCRIPT = path.join(SCRIPT_DIR, 'count_sections.sh');
const LEDGER_SCRIPT = path.join(SCRIPT_DIR, 'ledger.py');
const TEMPLATE_DIR = path.join(__dirname, '..', 'skills', 'lava-extruder', 'templates');

function printHelp() {
  console.log(`\n🌋 Lava Extruder CLI — Universal Document Ingestion & Obsidian Vault Scaffolding

Usage:
  lava-extruder extract <input_file> [output_file]  Extract any document to Markdown (in runs/extracted/)
  lava-extruder count <file>                        Count structural markers & chunk plan
  lava-extruder ledger init <extracted_file>        Initialize section coverage ledger
  lava-extruder ledger check <vault_dir>            Verify 100% section coverage gate
  lava-extruder ledger sync-source <vault> <raw>    Generate / sync wiki/sources/ source hub note
  lava-extruder init [vault_dir]                    Scaffold Karpathy RAG vault folders & maps
  lava-extruder init [vault_dir] --git              Same, plus git init
  lava-extruder lint <vault_dir> [--json]           Deterministic vault integrity lint
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

function handleLedger(args) {
  if (args.length === 0) {
    console.error('Error: Missing ledger subcommand.\nUsage: lava-extruder ledger <init|check|sync-source> [args]');
    process.exit(1);
  }
  const proc = spawnSync('python3', [LEDGER_SCRIPT, ...args], { stdio: 'inherit' });
  process.exit(proc.status || 0);
}

function handleInit(args) {
  const vaultDir = path.resolve(args.filter(a => a !== '--git')[0] || process.cwd());
  const gitInit = args.includes('--git');
  console.log(`🌋 Scaffolding Karpathy RAG Obsidian Vault at: ${vaultDir}`);

  const dirs = [
    'raw',
    'wiki',
    path.join('wiki', 'sources'),
    'outputs',
    path.join('outputs', 'queries'),
    path.join('outputs', 'reports'),
    'runs',
    path.join('runs', 'extracted'),
    path.join('runs', 'ledger'),
    '.obsidian'
  ];
  for (const d of dirs) {
    const full = path.join(vaultDir, d);
    if (!fs.existsSync(full)) {
      fs.mkdirSync(full, { recursive: true });
      console.log(`  Created folder: /${d}`);
    }
  }

  // Obsidian graph settings
  const graphJsonPath = path.join(vaultDir, '.obsidian', 'graph.json');
  if (!fs.existsSync(graphJsonPath)) {
    const graphConfig = {
      "collapse-filter": false,
      "search": "",
      "showTags": true,
      "showAttachments": false,
      "hideUnresolved": false,
      "showOrphans": true,
      "colorGroups": [
        { "query": "path:wiki/sources", "color": { "a": 1, "rgb": 14701138 } },
        { "query": "type:wiki-concept or tag:concept", "color": { "a": 1, "rgb": 5419502 } },
        { "query": "path:outputs", "color": { "a": 1, "rgb": 3855722 } }
      ]
    };
    fs.writeFileSync(graphJsonPath, JSON.stringify(graphConfig, null, 2) + '\n', 'utf-8');
    console.log('  Created: .obsidian/graph.json');
  }

  // Obsidian app settings (ignore runs/ and raw/ from graph & search)
  const appJsonPath = path.join(vaultDir, '.obsidian', 'app.json');
  if (!fs.existsSync(appJsonPath)) {
    const appConfig = {
      "userIgnoreFilters": ["runs/", "raw/"]
    };
    fs.writeFileSync(appJsonPath, JSON.stringify(appConfig, null, 2) + '\n', 'utf-8');
    console.log('  Created: .obsidian/app.json');
  }

  // Governance contract: SCHEMA.md (customized to the vault domain)
  const schemaPath = path.join(vaultDir, 'SCHEMA.md');
  if (!fs.existsSync(schemaPath)) {
    fs.writeFileSync(schemaPath, `# Vault Schema\n\n## Domain\nDescribe what this vault covers (e.g. "AI/ML research notes", "lab documentation", "company internal KB").\n\n## Conventions\n- File names: lowercase, hyphens, no spaces (e.g. \`distributed-consensus.md\`)\n- Every wiki page starts with YAML frontmatter\n- Use \`[[wikilinks]]\` to link between pages (minimum 2 outbound links per page)\n- When updating a page, always bump the \`updated\` date\n- Every new page must be added to \`wiki/_master-index.md\` under the correct topic\n- Every session must start with orientation (SCHEMA.md → hot.md → master index → recent logs)\n- Every tag used in frontmatter MUST appear in the taxonomy below; add new tags here first\n\n## Tag Taxonomy\n- concept\n- entity\n- source\n- query\n- report\n\n## Page Thresholds\n- Create an article when a concept/entity is central to a source OR appears in 2+ sources\n- Fold minor mentions into an existing article instead of making a new page (preserve concrete numbers & facts)\n- Never create an article for passing mentions or things outside the domain\n- Split an article when it exceeds ~200 lines\n\n## Frontmatter Standard (v3)\nRequired: title, created, updated, tags, sources, type\nOptional: aliases, confidence, contested, contradictions\n\n## Update Policy\nNew sources supersede older ones on the same fact. Genuine contradictions are kept side-by-side\nwith dates and sources, flagged with contested: true, and linked via contradictions: [slug].\n`, 'utf-8');
    console.log('  Created: SCHEMA.md');
  }

  // Session continuity cache
  const hotPath = path.join(vaultDir, 'runs', 'hot.md');
  if (!fs.existsSync(hotPath)) {
    fs.writeFileSync(hotPath, `# Session Hot Cache\n\nLast Updated: YYYY-MM-DD\n\n## Key Recent Facts\n- \n\n## Recent Changes\n- \n\n## Active Threads\n- \n`, 'utf-8');
    console.log('  Created: runs/hot.md');
  }

  // Root index.md
  const rootIndex = path.join(vaultDir, 'index.md');
  if (!fs.existsSync(rootIndex)) {
    fs.writeFileSync(rootIndex, `# Vault Navigation Map\n\n- [[raw/|Raw Inbox]] — Unstructured source data\n- [[SCHEMA.md|Vault Schema]] — Governance contract: domain, taxonomy, thresholds\n- [[wiki/_master-index|Wiki Knowledge Base]] — Crystallized, LLM-maintained intelligence\n- [[wiki/sources/_index|Sources Map]] — Provenance hubs and coverage ledgers\n- [[outputs/|Outputs]] — Generated deliverables and synthesis reports\n- [[runs/logs|Agent Runs]] — Memory, state, and loop engineering logs\n- [[runs/hot|Hot Cache]] — Session continuity summary\n`, 'utf-8');
    console.log('  Created: index.md');
  }

  // Master index
  const masterIndex = path.join(vaultDir, 'wiki', '_master-index.md');
  if (!fs.existsSync(masterIndex)) {
    fs.writeFileSync(masterIndex, `# Master Knowledge Index\n\nEntry point for the knowledge base. Topic subfolders are listed below.\n\n| Topic | Description | Articles |\n|---|---|---|\n| [[sources/_index|sources]] | Provenance hubs and source coverage maps | 0 |\n`, 'utf-8');
    console.log('  Created: wiki/_master-index.md');
  }

  // Sources index
  const sourcesIndex = path.join(vaultDir, 'wiki', 'sources', '_index.md');
  if (!fs.existsSync(sourcesIndex)) {
    fs.writeFileSync(sourcesIndex, `# Source Provenance Index\n\nMaps every raw document ingested into the vault to its derived knowledge articles.\n\n| Source | Ingested | Derived Articles | Status |\n|---|---|---|---|\n`, 'utf-8');
    console.log('  Created: wiki/sources/_index.md');
  }

  // Runs logs and digested index
  const runLog = path.join(vaultDir, 'runs', 'logs.md');
  if (!fs.existsSync(runLog)) {
    fs.writeFileSync(runLog, `# Vault Agent Logs\n\nThis file tracks automated agent runs and vault modifications.\n`, 'utf-8');
    console.log('  Created: runs/logs.md');
  }

  const digestedIndex = path.join(vaultDir, 'runs', 'digested_index.md');
  if (!fs.existsSync(digestedIndex)) {
    fs.writeFileSync(digestedIndex, `# Digested Files Index\n\nTracks raw files fully processed into the wiki.\n\n| Raw Path | SHA-256 | Digest Date |\n|---|---|---|\n`, 'utf-8');
    console.log('  Created: runs/digested_index.md');
  }

  // Agent rules from template
  let agentRules = '';
  const templatePath = path.join(TEMPLATE_DIR, 'AGENTS.md');
  if (fs.existsSync(templatePath)) {
    agentRules = fs.readFileSync(templatePath, 'utf-8');
  } else {
    agentRules = `# Knowledge Base — Vault Conventions\n\nSee SCHEMA.md and AGENTS.md.\n`;
  }

  for (const filename of ['AGENTS.md', 'CLAUDE.md', 'GEMINI.md']) {
    const dest = path.join(vaultDir, filename);
    if (!fs.existsSync(dest)) {
      fs.writeFileSync(dest, agentRules, 'utf-8');
      console.log(`  Created: ${filename}`);
    }
  }

  if (gitInit) {
    const proc = spawnSync('git', ['init'], { cwd: vaultDir, stdio: 'inherit' });
    if (proc.status === 0) {
      console.log('  Git initialized');
    } else {
      console.warn('  Could not initialize git (is git installed?)');
    }
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
  } else if (command === 'ledger') {
    handleLedger(args.slice(1));
  } else if (command === 'init' || command === 'scaffold') {
    handleInit(args.slice(1));
  } else if (command === 'lint') {
    const lintScript = path.join(SCRIPT_DIR, 'lint_vault.py');
    const proc = spawnSync('python3', [lintScript, ...args.slice(1)], { stdio: 'inherit' });
    process.exit(proc.status || 0);
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
