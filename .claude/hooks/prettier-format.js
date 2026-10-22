// PostToolUse hook for Edit|Write: run the client's Prettier on the edited file.
// Prettier is only installed in client/, so files elsewhere are skipped.
const path = require('path');
const { spawnSync } = require('child_process');

const EXTENSIONS = new Set(['.vue', '.js', '.json', '.css', '.html', '.md']);
const clientDir = path.resolve(__dirname, '..', '..', 'client');
const prettierBin = path.join(clientDir, 'node_modules', 'prettier', 'bin', 'prettier.cjs');

let input = '';
process.stdin.on('data', (chunk) => (input += chunk));
process.stdin.on('end', () => {
  let payload;
  try {
    payload = JSON.parse(input);
  } catch {
    return;
  }

  const filePath = payload?.tool_response?.filePath ?? payload?.tool_input?.file_path;
  if (!filePath) return;

  const resolved = path.resolve(filePath);
  const rel = path.relative(clientDir, resolved);
  if (rel.startsWith('..') || path.isAbsolute(rel)) return;
  if (rel.split(path.sep).includes('node_modules')) return;
  if (!EXTENSIONS.has(path.extname(resolved).toLowerCase())) return;

  spawnSync(process.execPath, [prettierBin, '--write', resolved], { cwd: clientDir, stdio: 'ignore' });
});
