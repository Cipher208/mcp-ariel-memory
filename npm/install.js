#!/usr/bin/env node
/**
 * Post-install script: installs mcp-ariel-memory Python package via pip.
 */
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const PACKAGE_NAME = 'mcp-ariel-memory';
const MIN_VERSION = '1.0.0';

function findPython() {
  // Try to find system Python, skip venv/conda
  const candidates = [
    'python3',
    'python',
    'py',
  ];
  
  for (const cmd of candidates) {
    try {
      const out = execSync(`"${cmd}" --version 2>&1`, { encoding: 'utf8', shell: true });
      const match = out.match(/Python (\d+\.\d+)/);
      if (match) {
        const version = parseFloat(match[1]);
        if (version >= 3.10) {
          // Check if it's a venv
          const pathOut = execSync(`"${cmd}" -c "import sys; print(sys.executable)" 2>&1`, { encoding: 'utf8', shell: true });
          if (pathOut.includes('hermes') || pathOut.includes('venv') || pathOut.includes('.local') || pathOut.includes('conda')) {
            continue;
          }
          return cmd;
        }
      }
    } catch {}
  }
  
  // Fallback: try Windows store and common paths
  const fullPaths = [
    'C:\\Python312\\python.exe',
    'C:\\Python311\\python.exe', 
    'C:\\Python310\\python.exe',
    process.env.LOCALAPPDATA + '\\Programs\\Python\\Python312\\python.exe',
    process.env.LOCALAPPDATA + '\\Programs\\Python\\Python311\\python.exe',
  ];
  
  for (const p of fullPaths) {
    if (!p) continue;
    try {
      const out = execSync(`"${p}" --version 2>&1`, { encoding: 'utf8' });
      if (out.includes('Python 3.')) {
        return `"${p}"`;
      }
    } catch {}
  }
  
  return null;
}

function isInstalled(python) {
  try {
    const out = execSync(`${python} -m pip show ${PACKAGE_NAME}`, { encoding: 'utf8' });
    const versionMatch = out.match(/Version:\s*(.+)/);
    if (versionMatch) {
      const installed = versionMatch[1].trim();
      console.log(`[mcp-ariel-memory] Found ${PACKAGE_NAME} ${installed}`);
      return true;
    }
  } catch {}
  return false;
}

function install(python) {
  console.log(`[mcp-ariel-memory] Installing ${PACKAGE_NAME} via pip...`);
  try {
    // Try PyPI first
    execSync(`${python} -m pip install --user "${PACKAGE_NAME}>=${MIN_VERSION}" 2>&1`, {
      stdio: 'inherit',
    });
    console.log(`[mcp-ariel-memory] Installation complete.`);
  } catch (e) {
    // Fallback: install from GitHub
    console.log(`[mcp-ariel-memory] PyPI install failed, installing from GitHub...`);
    try {
      execSync(`${python} -m pip install --user "git+https://github.com/faustovo2003-commits/mcp-ariel-memory.git@master"`, {
        stdio: 'inherit',
      });
      console.log(`[mcp-ariel-memory] Installation complete (from GitHub).`);
    } catch (e2) {
      console.error(`[mcp-ariel-memory] Failed to install. Install manually:`);
      console.error(`  pip install ${PACKAGE_NAME}`);
      console.error(`  or: pip install git+https://github.com/faustovo2003-commits/mcp-ariel-memory.git`);
      process.exit(1);
    }
  }
}

// Main
const python = findPython();
if (!python) {
  console.error('[mcp-ariel-memory] Python not found. Install Python 3.10+ first.');
  console.error('  https://www.python.org/downloads/');
  process.exit(1);
}

console.log(`[mcp-ariel-memory] Using Python: ${python}`);

if (!isInstalled(python)) {
  install(python);
} else {
  console.log('[mcp-ariel-memory] Already installed. Skipping.');
}
