#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

const destDir = path.join(os.homedir(), '.gemini', 'config', 'plugins', 'lava-extruder-plugin');
const srcDir = __dirname;

console.log('\n🌋 Installing Lava Extruder Antigravity Plugin...');
console.log('Target directory: ' + destDir + '\n');

try {
  // Ensure the target directory exists
  if (!fs.existsSync(destDir)) {
    fs.mkdirSync(destDir, { recursive: true });
  }

  // Copy files
  fs.cpSync(srcDir, destDir, { 
    recursive: true, 
    filter: (src) => {
      // Exclude unnecessary files from being copied
      const basename = path.basename(src);
      return !['node_modules', '.git', 'package.json', 'package-lock.json', 'install.js'].includes(basename);
    }
  });

  console.log('✅ Installation complete!');
  console.log('The lava-extruder skill is now available to your agents.');
} catch (err) {
  console.error('❌ Installation failed:', err.message);
  process.exit(1);
}
