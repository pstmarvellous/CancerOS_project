import { spawn, spawnSync } from 'node:child_process';
import { readFileSync, statSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

// Preparation and serving must apply the same artifact/provenance validator.
// TypeScript is already a locked build dependency. This isolated CLI process
// transpiles only repository-owned TS modules; bundle contents remain plain JSON.
if (process.argv[2] === '--validate-bundle') {
  try {
    const require = createRequire(import.meta.url);
    const ts = require('typescript');
    require.extensions['.ts'] = (module, filename) => {
      const source = readFileSync(filename, 'utf8');
      module._compile(ts.transpileModule(source, { compilerOptions: {
        module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
      } }).outputText, filename);
    };
    const { validateDemoBundle } = require(resolve(root, 'apps/web/lib/synthetic-demo.ts'));
    const file = resolve(process.argv[3] ?? resolve(root, '.local/synthetic-demo.json'));
    if (statSync(file).size > 20 * 1024 * 1024) {
      console.log(JSON.stringify({ state: 'invalid', message: 'Bundle exceeds the 20 MiB serving limit; prepare again.' }));
      process.exit(1);
    }
    const value = JSON.parse(readFileSync(file, 'utf8'));
    if (value && typeof value.expiresAt === 'string' && Date.parse(value.expiresAt) <= Date.now()) {
      console.log(JSON.stringify({ state: 'expired', message: 'Bundle expired; prepare again to refresh the 7-day window.' }));
      process.exit(1);
    }
    const valid = validateDemoBundle(value);
    console.log(JSON.stringify({ state: valid ? 'valid' : 'invalid',
      message: valid ? 'Bundle passed the serving validator.' : 'Bundle failed serving schema, expiry, provenance or artifact integrity checks.' }));
    process.exit(valid ? 0 : 1);
  } catch (error) {
    const missing = error?.code === 'ENOENT';
    console.log(JSON.stringify({ state: missing ? 'missing' : 'invalid', message: missing ? 'Prepared bundle is missing.' : error instanceof SyntaxError ? 'Bundle is not valid JSON; prepare again.' : 'Bundle validator unavailable; check file access and installed npm dependencies.' }));
    process.exit(1);
  }
}

// The supported demo launcher performs idempotent preparation before serving.
const preparation = spawnSync(process.platform === 'win32' ? 'uv.exe' : 'uv',
  ['run', 'python', 'scripts/prepare_synthetic_demo.py'], { cwd: root, stdio: 'inherit', windowsHide: true });
if (preparation.error || preparation.status !== 0) {
  console.error('Demo preparation failed. Start the foundation dependencies as documented in infrastructure/README.md, then retry npm run demo.');
  process.exit(1);
}

// Explicit opt-in applies to this child process only. The bundle contains no API
// credentials and the read-only adapter never connects to the backend.
const child = spawn(process.execPath,
  [resolve(root, 'node_modules/next/dist/bin/next'), 'start', '--hostname', '127.0.0.1'], {
    cwd: resolve(root, 'apps/web'), stdio: 'inherit', windowsHide: true,
    env: { ...process.env, CANCEROS_SYNTHETIC_DEMO: '1', EXTERNAL_INFERENCE_ENABLED: 'false' },
  });
child.on('exit', code => process.exit(code ?? 1));
child.on('error', () => { console.error('Could not start the local demo. Run npm run build, then retry.'); process.exit(1); });
