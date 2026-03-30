/**
 * Cross-platform backend starter for pnpm dev:full.
 * Resolves AGENT_DIR relative to repo root, then spawns `agentos run --dev`.
 */
import { spawn } from 'child_process';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { existsSync } from 'fs';

const scriptDir = dirname(fileURLToPath(import.meta.url)); // web/scripts/
const repoRoot = resolve(scriptDir, '..', '..'); // repo root
const agentDir = resolve(repoRoot, process.env.AGENT_DIR || 'my_agent');

if (!existsSync(agentDir)) {
  const dirName = process.env.AGENT_DIR || 'my_agent';
  console.error(`\n[backend] ERROR: Agent directory not found: ${agentDir}`);
  console.error(`[backend] Run the following command first:\n`);
  console.error(`    agentos init ${dirName}\n`);
  process.exit(1);
}

// Pass command as a single string (not args array) to avoid shell-escaping
// deprecation warning. Set PYTHONIOENCODING so Rich can render Unicode on
// Windows consoles that default to GBK/CP936.
const proc = spawn('agentos run --dev --port 8000', {
  cwd: agentDir,
  stdio: 'inherit',
  shell: true,
  env: {
    ...process.env,
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1',
  },
});

proc.on('exit', (code) => process.exit(code ?? 0));
