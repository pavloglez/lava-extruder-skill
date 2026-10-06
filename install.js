#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

const srcDir = __dirname;
const geminiPluginDir = path.join(os.homedir(), '.gemini', 'config', 'plugins', 'lava-extruder-plugin');
const geminiSkillDir = path.join(os.homedir(), '.gemini', 'config', 'skills', 'lava-extruder');
const claudeSkillsDir = path.join(os.homedir(), '.claude', 'skills', 'lava-extruder');
const localBinDir = path.join(os.homedir(), '.local', 'bin');

console.log('\n🌋 Installing Lava Extruder Plugin & Multi-Agent Skill...\n');

try {
  // 1. Install to Gemini plugin directory
  if (!fs.existsSync(geminiPluginDir)) {
    fs.mkdirSync(geminiPluginDir, { recursive: true });
  }

  fs.cpSync(srcDir, geminiPluginDir, {
    recursive: true,
    filter: (src) => {
      const basename = path.basename(src);
      return !['node_modules', '.git'].includes(basename);
    }
  });
  console.log(`✓ Installed Gemini Plugin: ${geminiPluginDir}`);

  // 2. Install/update standalone skill in ~/.gemini/config/skills/lava-extruder
  fs.mkdirSync(geminiSkillDir, { recursive: true });
  fs.cpSync(path.join(srcDir, 'skills', 'lava-extruder'), geminiSkillDir, { recursive: true });
  console.log(`✓ Installed Gemini Skill: ${geminiSkillDir}`);

  // 3. Install for Claude Code if ~/.claude directory exists
  if (fs.existsSync(path.join(os.homedir(), '.claude'))) {
    fs.mkdirSync(claudeSkillsDir, { recursive: true });
    fs.cpSync(path.join(srcDir, 'skills', 'lava-extruder'), claudeSkillsDir, { recursive: true });
    console.log(`✓ Installed Claude Code Skill: ${claudeSkillsDir}`);
  }

  // 4. Make all scripts executable
  const targetScriptDirs = [
    path.join(geminiPluginDir, 'skills', 'lava-extruder', 'scripts'),
    path.join(geminiPluginDir, 'bin'),
    path.join(geminiSkillDir, 'scripts')
  ];

  for (const sDir of targetScriptDirs) {
    if (fs.existsSync(sDir)) {
      const files = fs.readdirSync(sDir);
      for (const f of files) {
        if (f.endsWith('.sh') || f.endsWith('.py') || f.endsWith('.js')) {
          fs.chmodSync(path.join(sDir, f), 0o755);
        }
      }
    }
  }

  // 5. Expose globally via ~/.local/bin symlinks
  if (!fs.existsSync(localBinDir)) {
    fs.mkdirSync(localBinDir, { recursive: true });
  }

  const cliBinSrc = path.join(geminiPluginDir, 'bin', 'cli.js');
  const extractBinSrc = path.join(geminiPluginDir, 'skills', 'lava-extruder', 'scripts', 'extract_raw.py');

  const cliSymlink = path.join(localBinDir, 'lava-extruder');
  const extractSymlink = path.join(localBinDir, 'lava-extract');

  try {
    if (fs.existsSync(cliSymlink)) fs.unlinkSync(cliSymlink);
    fs.symlinkSync(cliBinSrc, cliSymlink);
    fs.chmodSync(cliSymlink, 0o755);
    console.log(`✓ Global CLI linked: ${cliSymlink}`);
  } catch (err) {
    console.warn(`! Notice: Could not link ${cliSymlink}: ${err.message}`);
  }

  try {
    if (fs.existsSync(extractSymlink)) fs.unlinkSync(extractSymlink);
    fs.symlinkSync(extractBinSrc, extractSymlink);
    fs.chmodSync(extractSymlink, 0o755);
    console.log(`✓ Global Extractor linked: ${extractSymlink}`);
  } catch (err) {
    console.warn(`! Notice: Could not link ${extractSymlink}: ${err.message}`);
  }

  console.log('\n✅ Installation successful!');
  console.log('You can now run "lava-extruder" or "lava-extract <file>" anywhere on your system.\n');
} catch (err) {
  console.error('❌ Installation failed:', err.message);
  process.exit(1);
}
