#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

const SCRIPT_DIR = path.join(__dirname, '..', 'skills', 'lava-extruder', 'scripts');
const EXTRACT_SCRIPT = path.join(SCRIPT_DIR, 'extract_raw.py');
const COUNT_SCRIPT = path.join(SCRIPT_DIR, 'count_sections.sh');

function printHelp() {
  console.log(`\n🌋 Lava Extruder CLI — Universal Document Ingestion & Obsidian Vault Scaffolding

Usage:
  lava-extruder extract <input_file> [output_file]  Extract any document to Markdown
  lava-extruder count <file>                        Count structural markers & chunk plan
  lava-extruder init [vault_dir]                    Scaffold Karpathy RAG vault folders & maps
  lava-extruder init [vault_dir] --git              Same, plus git init
  lava-extruder lint <vault_dir>                    Deterministic vault integrity lint
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
  const vaultDir = path.resolve(args.filter(a => a !== '--git')[0] || process.cwd());
  const gitInit = args.includes('--git');
  console.log(`🌋 Scaffolding Karpathy RAG Obsidian Vault at: ${vaultDir}`);

  const dirs = ['raw', 'wiki', 'outputs', 'runs'];
  for (const d of dirs) {
    const full = path.join(vaultDir, d);
    if (!fs.existsSync(full)) {
      fs.mkdirSync(full, { recursive: true });
      console.log(`  Created folder: /${d}`);
    }
  }

  // Governance contract: SCHEMA.md (customized to the vault domain)
  const schemaPath = path.join(vaultDir, 'SCHEMA.md');
  if (!fs.existsSync(schemaPath)) {
    fs.writeFileSync(schemaPath, `# Vault Schema\n\n## Domain\nAsk the agent to set this: describe what this vault covers (e.g. "AI/ML research notes", "lab documentation", "company internal KB").\n\n## Conventions\n- File names: lowercase, hyphens, no spaces (e.g. \`distributed-consensus.md\`)\n- Every wiki page starts with YAML frontmatter (see frontmatter standard)\n- Use \`[[wikilinks]]\` to link between pages (minimum 2 outbound links per page)\n- When updating a page, always bump the \`updated\` date\n- Every new page must be added to \`wiki/_master-index.md\` under the correct topic\n- Every session must start with orientation (SCHEMA.md → hot.md → master index → recent logs)\n- Every tag used in frontmatter MUST appear in the taxonomy below; add new tags here first\n\n## Tag Taxonomy\nAdd tags here as the vault grows: concept, entity, paper, benchmark, technique, domain-specific...\n\n## Page Thresholds\n- Create an article when a concept/entity is central to a source OR appears in 2+ sources\n- Fold minor mentions into an existing article instead of making a new page\n- Never create an article for passing mentions or things outside the domain\n- Split an article when it exceeds ~200 lines\n\n## Frontmatter\nRequired: title, created, updated, tags, sources\nOptional but recommended: confidence, contested, contradictions\n\n## Update Policy\nNew sources supersede older ones on the same fact. Genuine contradictions are kept side-by-side\nwith dates and sources, flagged with contested: true, and linked via contradictions: [slug].\n`, 'utf-8');
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
    fs.writeFileSync(rootIndex, `# Vault Navigation Map\n\n- [[raw/|Raw Inbox]] — Unstructured source data\n- [[SCHEMA.md|Vault Schema]] — Governance contract: domain, taxonomy, thresholds\n- [[wiki/_master-index|Wiki Knowledge Base]] — Crystallized, LLM-maintained intelligence\n- [[outputs/|Outputs]] — Generated deliverables and synthesis reports\n- [[runs/logs|Agent Runs]] — Memory, state, and loop engineering logs\n- [[runs/hot|Hot Cache]] — Session continuity summary\n`, 'utf-8');
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
    fs.writeFileSync(digestedIndex, `# Digested Files Index\n\nTracks raw files fully processed into the wiki.\n\n| Raw Path | SHA-256 | Digest Date |\n|---|---|---|\n`, 'utf-8');
    console.log('  Created: runs/digested_index.md');
  }

  // Agent instructions — full methodology so skill-less agents can run the vault
  const agentRules = `# Knowledge Base — Vault Conventions

## Vault Structure
- /raw — source material, clipped articles, research (the input zone). Immutable — never edit; corrections go in wiki articles.
- /wiki — LLM-compiled knowledge base
- /outputs — query results and generated reports (outputs/queries/, outputs/reports/)
- /runs — loop engineering logs and agent state tracking (logs.md, digested_index.md, hot.md)

## Session Orientation (mandatory every session)
1. Read SCHEMA.md — domain, taxonomy, thresholds.
2. Read runs/hot.md — recent facts, changes, active threads.
3. Read wiki/_master-index.md — what topics and articles exist.
4. Scan the last ~30 lines of runs/logs.md.

## Wiki System
- wiki/_master-index.md is the entry point — lists every topic with a one-line description.
- Each topic gets its own subfolder with its own _index.md listing all articles.
- Every article needs YAML frontmatter (title, created, updated, tags, sources) and ≥2 outbound [[wikilinks]].
- Use tags from the SCHEMA.md taxonomy only.

## Compiling (The Lava Cooling Process)
When I say "compile", "/compile", or dump new material in raw/:
1. Consult /runs/digested_index.md to skip already processed files (check path + SHA-256).
2. For binary/non-text files, extract to clean Markdown first using \`lava-extract "<raw_file_path>"\`.
3. If extracted text exceeds ~2,000 lines, build a segmentation plan in /runs/ and process in ~500-800 line segments stream-to-disk.
4. Route each qualifying concept into its own topic folder in wiki/ with v2 frontmatter.
5. Fold minor mentions into existing articles rather than minting new pages.
6. Cross-link related topics using [[wiki links]].
7. Verify line and section completeness before adding the file to /runs/digested_index.md.
8. Commit if this vault is a git repo: wiki: digest <source> YYYY-MM-DD.

## Querying
Answer from the wiki with citations: "Based on [[article-a]] and [[article-b]]..." File substantial answers to outputs/queries/.
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

  const geminiPath = path.join(vaultDir, 'GEMINI.md');
  if (!fs.existsSync(geminiPath)) {
    fs.writeFileSync(geminiPath, agentRules, 'utf-8');
    console.log('  Created: GEMINI.md');
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
