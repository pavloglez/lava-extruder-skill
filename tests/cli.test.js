const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

const CLI_PATH = path.join(__dirname, '..', 'bin', 'cli.js');
const SCRIPT_DIR = path.join(__dirname, '..', 'skills', 'lava-extruder', 'scripts');
const EXTRACT_RAW = path.join(SCRIPT_DIR, 'extract_raw.py');
const LINT_VAULT = path.join(SCRIPT_DIR, 'lint_vault.py');
const LEDGER_SCRIPT = path.join(SCRIPT_DIR, 'ledger.py');

test('CLI: --help returns usage information', () => {
  const res = spawnSync('node', [CLI_PATH, '--help'], { encoding: 'utf-8' });
  assert.equal(res.status, 0);
  assert.match(res.stdout, /Lava Extruder CLI/);
  assert.match(res.stdout, /lava-extruder init/);
  assert.match(res.stdout, /lava-extruder lint/);
  assert.match(res.stdout, /lava-extruder ledger/);
});

test('CLI: init creates complete Karpathy RAG vault structure with Obsidian graph configs', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-vault-'));
  try {
    const res = spawnSync('node', [CLI_PATH, 'init', tmpDir], { encoding: 'utf-8' });
    assert.equal(res.status, 0);

    // Verify directories
    for (const dir of [
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
    ]) {
      assert.ok(fs.existsSync(path.join(tmpDir, dir)), `Directory ${dir} should exist`);
    }

    // Verify navigation and agent files
    assert.ok(fs.existsSync(path.join(tmpDir, 'index.md')), 'index.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'SCHEMA.md')), 'SCHEMA.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'wiki', '_master-index.md')), 'wiki/_master-index.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'wiki', 'sources', '_index.md')), 'wiki/sources/_index.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'runs', 'logs.md')), 'runs/logs.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'runs', 'digested_index.md')), 'runs/digested_index.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'runs', 'hot.md')), 'runs/hot.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'AGENTS.md')), 'AGENTS.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'CLAUDE.md')), 'CLAUDE.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'GEMINI.md')), 'GEMINI.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, '.obsidian', 'graph.json')), '.obsidian/graph.json should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, '.obsidian', 'app.json')), '.obsidian/app.json should exist');

    const graphJson = JSON.parse(fs.readFileSync(path.join(tmpDir, '.obsidian', 'graph.json'), 'utf-8'));
    assert.ok(Array.isArray(graphJson.colorGroups));

    const appJson = JSON.parse(fs.readFileSync(path.join(tmpDir, '.obsidian', 'app.json'), 'utf-8'));
    assert.ok(appJson.userIgnoreFilters.includes('runs/'));
    assert.ok(appJson.userIgnoreFilters.includes('raw/'));
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('CLI: init --git initializes a git repository', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-git-'));
  try {
    const res = spawnSync('node', [CLI_PATH, 'init', tmpDir, '--git'], { encoding: 'utf-8' });
    assert.equal(res.status, 0);
    assert.ok(fs.existsSync(path.join(tmpDir, '.git', 'HEAD')), '.git/HEAD should exist');
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Extractor: isolation ensures files in raw/ extract to runs/extracted/ without polluting raw/', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-isolation-'));
  try {
    spawnSync('node', [CLI_PATH, 'init', tmpDir], { encoding: 'utf-8' });
    const rawFile = path.join(tmpDir, 'raw', 'notes.txt');
    fs.writeFileSync(rawFile, 'Important architecture specifications.\nLine 2.\n', 'utf-8');

    const res = spawnSync('node', [CLI_PATH, 'extract', rawFile], { encoding: 'utf-8' });
    assert.equal(res.status, 0);

    // Verify output is in runs/extracted/
    const expectedOut = path.join(tmpDir, 'runs', 'extracted', 'notes.txt.md');
    assert.ok(fs.existsSync(expectedOut), `Expected extracted output at ${expectedOut}`);

    // Verify raw/ does not contain any .extracted.md files
    const rawEntries = fs.readdirSync(path.join(tmpDir, 'raw'));
    assert.deepEqual(rawEntries, ['notes.txt'], 'raw/ directory must remain unpolluted');

    const content = fs.readFileSync(expectedOut, 'utf-8');
    assert.match(content, /source: "raw\/notes\.txt"/);
    assert.match(content, /sha256: "[a-f0-9]{64}"/);
    assert.match(content, /extractor: "direct-read"/);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Extractor: CSV to Markdown table conversion with manifest', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-csv-'));
  try {
    const csvFile = path.join(tmpDir, 'sample.csv');
    const outFile = path.join(tmpDir, 'sample.extracted.md');
    fs.writeFileSync(csvFile, 'Name,Age,Role\nAlice,30,Engineer\nBob,25,Designer\n', 'utf-8');

    const res = spawnSync('python3', [EXTRACT_RAW, csvFile, outFile], { encoding: 'utf-8' });
    assert.equal(res.status, 0);
    assert.ok(fs.existsSync(outFile));

    const content = fs.readFileSync(outFile, 'utf-8');
    assert.match(content, /extractor: "csv-table"/);
    assert.match(content, /\| Name/);
    assert.match(content, /\| Alice/);
    assert.match(content, /\| Designer/);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Extractor: Jupyter Notebook (.ipynb) to Markdown without truncation', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-ipynb-'));
  try {
    const ipynbFile = path.join(tmpDir, 'sample.ipynb');
    const outFile = path.join(tmpDir, 'sample.extracted.md');
    const longOutput = 'A'.repeat(1500);
    const notebookJson = {
      cells: [
        { cell_type: 'markdown', source: ['# Title of Notebook\n', 'Notebook intro.'] },
        { cell_type: 'code', source: ['print("hello world")'], outputs: [{ output_type: 'stream', text: [longOutput] }] }
      ],
      metadata: {}
    };
    fs.writeFileSync(ipynbFile, JSON.stringify(notebookJson), 'utf-8');

    const res = spawnSync('python3', [EXTRACT_RAW, ipynbFile, outFile], { encoding: 'utf-8' });
    assert.equal(res.status, 0);
    assert.ok(fs.existsSync(outFile));

    const content = fs.readFileSync(outFile, 'utf-8');
    assert.match(content, /# Title of Notebook/);
    assert.match(content, /<details><summary>Click to expand output \(1500 chars\)<\/summary>/);
    assert.ok(!content.includes('[output truncated]'), 'Output should not be truncated');
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Ledger: init creates sections and check validates complete mappings', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-ledger-'));
  try {
    spawnSync('node', [CLI_PATH, 'init', tmpDir], { encoding: 'utf-8' });

    const rawFile = path.join(tmpDir, 'raw', 'consensus.md');
    fs.writeFileSync(rawFile, '# Raft Consensus\n\nIntro to raft.\n\n## Leader Election\n\nElection mechanics.\n', 'utf-8');

    // Extract
    spawnSync('node', [CLI_PATH, 'extract', rawFile], { encoding: 'utf-8' });
    const extractedFile = path.join(tmpDir, 'runs', 'extracted', 'consensus.md.md');
    assert.ok(fs.existsSync(extractedFile));

    // Ledger init
    const initRes = spawnSync('node', [CLI_PATH, 'ledger', 'init', extractedFile], { encoding: 'utf-8' });
    assert.equal(initRes.status, 0);

    const ledgerFile = path.join(tmpDir, 'runs', 'ledger', 'consensus.md.md');
    assert.ok(fs.existsSync(ledgerFile));

    // Create target wiki article
    const targetArticle = path.join(tmpDir, 'wiki', 'raft-consensus.md');
    fs.writeFileSync(targetArticle, '---\ntitle: "Raft Consensus"\ncreated: 2026-01-01\nupdated: 2026-01-01\ntags: [concept]\nsources: ["raw/consensus.md"]\ntype: wiki-concept\n---\n\n# Raft Consensus\n\nIntro to raft and Leader Election.\n\nSee [[wiki/_master-index]] and [[wiki/sources/_index]].\n', 'utf-8');

    // Update ledger rows to point to raft-consensus
    let ledgerContent = fs.readFileSync(ledgerFile, 'utf-8');
    ledgerContent = ledgerContent.replace(/\| (S\d+) \| (\d+-\d+) \| ([^|]+) \| \| \|/g, '| $1 | $2 | $3 | [[raft-consensus]] | |');
    fs.writeFileSync(ledgerFile, ledgerContent, 'utf-8');

    // Run check
    const checkRes = spawnSync('node', [CLI_PATH, 'ledger', 'check', tmpDir], { encoding: 'utf-8' });
    assert.equal(checkRes.status, 0, `ledger check should pass: ${checkRes.stderr}`);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Ledger: check fails on unmapped section, empty target, or skip without note', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-ledger-fail-'));
  try {
    spawnSync('node', [CLI_PATH, 'init', tmpDir], { encoding: 'utf-8' });
    const ledgerDir = path.join(tmpDir, 'runs', 'ledger');
    fs.mkdirSync(ledgerDir, { recursive: true });

    const ledgerFile = path.join(ledgerDir, 'test.md');
    fs.writeFileSync(ledgerFile, '# Coverage Ledger\n\n| ID | Lines | Heading | Target | Note |\n|---|---|---|---|---|\n| S001 | 1-20 | Overview | | |\n| S002 | 21-30 | Legal | skip | |\n', 'utf-8');

    const res = spawnSync('node', [CLI_PATH, 'ledger', 'check', tmpDir], { encoding: 'utf-8' });
    assert.notEqual(res.status, 0);
    assert.match(res.stderr, /Empty Target/);
    assert.match(res.stderr, /justification required/);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Ledger: sync-source generates wiki/sources note with coverage table', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-sync-'));
  try {
    spawnSync('node', [CLI_PATH, 'init', tmpDir], { encoding: 'utf-8' });

    const ledgerDir = path.join(tmpDir, 'runs', 'ledger');
    fs.mkdirSync(ledgerDir, { recursive: true });
    const ledgerFile = path.join(ledgerDir, 'whitepaper.pdf.md');
    fs.writeFileSync(ledgerFile, '# Coverage Ledger\n\n| ID | Lines | Heading | Target | Note |\n|---|---|---|---|---|\n| S001 | 1-50 | Introduction | [[intro-concept]] | | \n', 'utf-8');

    const res = spawnSync('node', [CLI_PATH, 'ledger', 'sync-source', tmpDir, 'raw/whitepaper.pdf'], { encoding: 'utf-8' });
    assert.equal(res.status, 0);

    const sourceNote = path.join(tmpDir, 'wiki', 'sources', 'whitepaper.md');
    assert.ok(fs.existsSync(sourceNote));
    const content = fs.readFileSync(sourceNote, 'utf-8');
    assert.match(content, /type: source/);
    assert.match(content, /\| S001 \| Introduction \| \[\[intro-concept\]\] \|/);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Lint: clean vault reports no issues', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-lint-clean-'));
  try {
    spawnSync('node', [CLI_PATH, 'init', tmpDir], { encoding: 'utf-8' });
    fs.writeFileSync(path.join(tmpDir, 'wiki', 'concept-a.md'), '---\ntitle: "Concept A"\ncreated: 2026-01-01\nupdated: 2026-01-01\ntags: [concept]\nsources: ["raw/source.pdf"]\n---\n\n# Concept A\n\nSee [[Concept B]] and [[Concept C]].\n', 'utf-8');
    fs.writeFileSync(path.join(tmpDir, 'wiki', 'concept-b.md'), '---\ntitle: "Concept B"\ncreated: 2026-01-01\nupdated: 2026-01-01\ntags: [concept]\nsources: ["raw/source.pdf"]\n---\n\n# Concept B\n\nSee [[Concept A]] and [[Concept C]].\n', 'utf-8');
    fs.writeFileSync(path.join(tmpDir, 'wiki', 'concept-c.md'), '---\ntitle: "Concept C"\ncreated: 2026-01-01\nupdated: 2026-01-01\ntags: [concept]\nsources: ["raw/source.pdf"]\n---\n\n# Concept C\n\nSee [[Concept A]] and [[Concept B]].\n', 'utf-8');

    const res = spawnSync('python3', [LINT_VAULT, tmpDir], { encoding: 'utf-8' });
    assert.equal(res.status, 0, `lint should be clean, got: ${res.stdout}`);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Lint: block list YAML frontmatter and aliases resolve cleanly', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-lint-yaml-'));
  try {
    spawnSync('node', [CLI_PATH, 'init', tmpDir], { encoding: 'utf-8' });
    // Article A uses block list YAML tags and defines aliases
    fs.writeFileSync(path.join(tmpDir, 'wiki', 'distributed-raft.md'), '---\ntitle: "Raft Algorithm"\ncreated: 2026-01-01\nupdated: 2026-01-01\ntags:\n  - concept\nsources:\n  - raw/paper.pdf\naliases:\n  - raft\n  - Consensus Protocol\n---\n\n# Raft Algorithm\n\nSee [[paxos|Paxos Comparison]] and [[distributed-raft#Mechanisms]].\n', 'utf-8');

    // Article B links to Article A using its alias [[raft]] and path [[wiki/distributed-raft]]
    fs.writeFileSync(path.join(tmpDir, 'wiki', 'paxos.md'), '---\ntitle: "Paxos"\ncreated: 2026-01-01\nupdated: 2026-01-01\ntags:\n  - concept\nsources:\n  - raw/paper.pdf\n---\n\n# Paxos\n\nAlternative to [[raft]] or [[distributed-raft|Direct]].\n', 'utf-8');

    const res = spawnSync('python3', [LINT_VAULT, tmpDir], { encoding: 'utf-8' });
    assert.equal(res.status, 0, `block YAML and aliases should resolve without error: ${res.stdout}`);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Ledger: recall heuristic emits warning when salient tokens are missing', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-recall-'));
  try {
    spawnSync('node', [CLI_PATH, 'init', tmpDir], { encoding: 'utf-8' });

    const rawFile = path.join(tmpDir, 'raw', 'performance.md');
    fs.writeFileSync(rawFile, '# Benchmark Report\n\nLatency dropped by 84.5% across 2026 runs under Paxos Protocol.\n', 'utf-8');

    spawnSync('node', [CLI_PATH, 'extract', rawFile], { encoding: 'utf-8' });
    const extractedFile = path.join(tmpDir, 'runs', 'extracted', 'performance.md.md');

    spawnSync('node', [CLI_PATH, 'ledger', 'init', extractedFile], { encoding: 'utf-8' });
    const ledgerFile = path.join(tmpDir, 'runs', 'ledger', 'performance.md.md');

    // Create target article that omits the specific numbers and dates
    const targetArticle = path.join(tmpDir, 'wiki', 'benchmark-summary.md');
    fs.writeFileSync(targetArticle, '---\ntitle: "Benchmark Summary"\ncreated: 2026-01-01\nupdated: 2026-01-01\ntags: [concept]\nsources: ["raw/performance.md"]\ntype: wiki-concept\n---\n\n# Benchmark Summary\n\nPerformance improved significantly.\n\nSee [[wiki/_master-index]] and [[wiki/sources/_index]].\n', 'utf-8');

    // Map to benchmark-summary
    let ledgerContent = fs.readFileSync(ledgerFile, 'utf-8');
    ledgerContent = ledgerContent.replace(/\| (S\d+) \| (\d+-\d+) \| ([^|]+) \| \| \|/g, '| $1 | $2 | $3 | [[benchmark-summary]] | |');
    fs.writeFileSync(ledgerFile, ledgerContent, 'utf-8');

    const checkRes = spawnSync('node', [CLI_PATH, 'ledger', 'check', tmpDir], { encoding: 'utf-8' });
    assert.equal(checkRes.status, 0); // warnings do not block digestion
    assert.match(checkRes.stderr, /Recall heuristic/);
    assert.match(checkRes.stderr, /84\.5%/);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Lint: raw folder pollution with .extracted.md is flagged as ERROR', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-pollution-'));
  try {
    spawnSync('node', [CLI_PATH, 'init', tmpDir], { encoding: 'utf-8' });
    // Accidentally put extracted file into raw/
    fs.writeFileSync(path.join(tmpDir, 'raw', 'sample.pdf.extracted.md'), '# Extracted\n', 'utf-8');

    const res = spawnSync('python3', [LINT_VAULT, tmpDir], { encoding: 'utf-8' });
    assert.notEqual(res.status, 0);
    assert.match(res.stdout, /extracted intermediate file found in raw/);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});
