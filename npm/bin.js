#!/usr/bin/env node
/**
 * CLI wrapper for mcp-ariel-memory.
 * Finds Python and runs the MCP server.
 */
const { spawn, execSync } = require('child_process');

function findPython() {
  const candidates = ['python3', 'python', 'py'];
  
  for (const cmd of candidates) {
    try {
      const out = execSync(`"${cmd}" --version 2>&1`, { encoding: 'utf8', shell: true });
      const match = out.match(/Python (\d+\.\d+)/);
      if (match) {
        const version = parseFloat(match[1]);
        if (version >= 3.10) {
          const pathOut = execSync(`"${cmd}" -c "import sys; print(sys.executable)" 2>&1`, { encoding: 'utf8', shell: true });
          if (pathOut.includes('hermes') || pathOut.includes('venv') || pathOut.includes('.local') || pathOut.includes('conda')) {
            continue;
          }
          return cmd;
        }
      }
    } catch {}
  }
  
  const fullPaths = [
    'C:\\Python312\\python.exe',
    'C:\\Python311\\python.exe',
    'C:\\Python310\\python.exe',
    process.env.LOCALAPPDATA + '\\Programs\\Python\\Python312\\python.exe',
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

const python = findPython();
if (!python) {
  console.error('[mcp-ariel-memory] Python 3.10+ not found. Install Python first.');
  process.exit(1);
}

const args = process.argv.slice(2);

const child = spawn(python, ['-m', 'mcp_server', ...args], {
  stdio: 'inherit',
  env: { ...process.env },
});

child.on('exit', (code) => {
  process.exit(code || 0);
});
