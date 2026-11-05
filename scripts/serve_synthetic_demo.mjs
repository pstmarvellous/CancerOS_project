import { spawn } from 'node:child_process';
import { resolve } from 'node:path';

// Explicit opt-in applies to this child process only. The bundle contains no API
// credentials and the read-only adapter never connects to the backend.
const child = spawn(process.execPath,
  [resolve('node_modules/next/dist/bin/next'), 'start', '--hostname', '127.0.0.1'], {
    cwd: resolve('apps/web'), stdio: 'inherit',
    env: { ...process.env, CANCEROS_SYNTHETIC_DEMO: '1', EXTERNAL_INFERENCE_ENABLED: 'false' },
  });
child.on('exit', code => process.exit(code ?? 1));
child.on('error', () => { console.error('Could not start the local demo. Run npm run build, then retry.'); process.exit(1); });
