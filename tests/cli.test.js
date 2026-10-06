const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

const CLI_PATH = path.join(__dirname, '..', 'bin', 'cli.js');
const SCRIPT_DIR = path.join(__dirname, '..', 'skills', 'lava-extruder', 'scripts');
const EXTRACT_RAW = path.join(SCRIPT_DIR, 'extract_raw.py');

test('CLI: --help returns usage information', () => {
  const res = spawnSync('node', [CLI_PATH, '--help'], { encoding: 'utf-8' });
  assert.equal(res.status, 0);
  assert.match(res.stdout, /Lava Extruder CLI/);
  assert.match(res.stdout, /lava-extruder init/);
});

test('CLI: init creates complete Karpathy RAG vault structure', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-vault-'));
  try {
    const res = spawnSync('node', [CLI_PATH, 'init', tmpDir], { encoding: 'utf-8' });
    assert.equal(res.status, 0);

    // Verify directories
    for (const dir of ['raw', 'wiki', 'outputs', 'runs']) {
      assert.ok(fs.existsSync(path.join(tmpDir, dir)), `Directory ${dir} should exist`);
    }

    // Verify navigation and agent files
    assert.ok(fs.existsSync(path.join(tmpDir, 'index.md')), 'index.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'wiki', '_master-index.md')), 'wiki/_master-index.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'runs', 'logs.md')), 'runs/logs.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'runs', 'digested_index.md')), 'runs/digested_index.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'AGENTS.md')), 'AGENTS.md should exist');
    assert.ok(fs.existsSync(path.join(tmpDir, 'CLAUDE.md')), 'CLAUDE.md should exist');
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Extractor: CSV to Markdown table conversion', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-csv-'));
  try {
    const csvFile = path.join(tmpDir, 'sample.csv');
    const outFile = path.join(tmpDir, 'sample.extracted.md');
    fs.writeFileSync(csvFile, 'Name,Age,Role\nAlice,30,Engineer\nBob,25,Designer\n', 'utf-8');

    const res = spawnSync('python3', [EXTRACT_RAW, csvFile, outFile], { encoding: 'utf-8' });
    assert.equal(res.status, 0);
    assert.ok(fs.existsSync(outFile));

    const content = fs.readFileSync(outFile, 'utf-8');
    assert.match(content, /\| Name/);
    assert.match(content, /\| Alice/);
    assert.match(content, /\| Designer/);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Extractor: Jupyter Notebook (.ipynb) to Markdown', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-ipynb-'));
  try {
    const ipynbFile = path.join(tmpDir, 'sample.ipynb');
    const outFile = path.join(tmpDir, 'sample.extracted.md');
    const notebookJson = {
      cells: [
        { cell_type: 'markdown', source: ['# Title of Notebook\n', 'Notebook intro.'] },
        { cell_type: 'code', source: ['print("hello world")'], outputs: [] }
      ],
      metadata: {}
    };
    fs.writeFileSync(ipynbFile, JSON.stringify(notebookJson), 'utf-8');

    const res = spawnSync('python3', [EXTRACT_RAW, ipynbFile, outFile], { encoding: 'utf-8' });
    assert.equal(res.status, 0);
    assert.ok(fs.existsSync(outFile));

    const content = fs.readFileSync(outFile, 'utf-8');
    assert.match(content, /# Title of Notebook/);
    assert.match(content, /```python\nprint\("hello world"\)\n```/);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});

test('Security Regression: Filenames with single quotes handle safely without injection', () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'lava-test-quote-'));
  try {
    const trickyName = path.join(tmpDir, "O'Reilly_Guide.csv");
    const outFile = path.join(tmpDir, "O'Reilly_Guide.extracted.md");
    fs.writeFileSync(trickyName, 'Item,Price\nBook,29\n', 'utf-8');

    const res = spawnSync('python3', [EXTRACT_RAW, trickyName, outFile], { encoding: 'utf-8' });
    assert.equal(res.status, 0);
    assert.ok(fs.existsSync(outFile));

    const content = fs.readFileSync(outFile, 'utf-8');
    assert.match(content, /\| Book/);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
});
