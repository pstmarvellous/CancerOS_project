import { spawn, spawnSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, unlinkSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:net';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Dedicated loopback preview. Existing services on 3000/8000 remain untouched.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const ownerFile = resolve(root, '.local/product-workspace-process.json');
const next = resolve(root, 'node_modules/next/dist/bin/next');
const args = [next, 'start', '--hostname', '127.0.0.1', '--port', '3001'];
const python = [resolve(root, '.venv/Scripts/python.exe'), resolve(root, '.venv/bin/python')].find(existsSync);

// Node has no portable process-birth identity API. Reuse existing psutil to
// protect against PID reuse. Do not print private process environments or args.
const processCheck = `
import json, os, sys
import psutil
mode, pid, birth, executable, expected = sys.argv[1:]
try:
    process = psutil.Process(int(pid))
    if birth != '-' and abs(process.create_time() - float(birth)) > 0.01:
        print(json.dumps({'state':'stale'})); sys.exit(0)
    same_executable = os.path.normcase(os.path.realpath(process.exe())) == os.path.normcase(os.path.realpath(executable))
    if not same_executable or process.cmdline()[1:] != json.loads(expected):
        print(json.dumps({'state':'mismatch'})); sys.exit(0)
    created = process.create_time()
    if mode == 'stop':
        process.terminate()
        try:
            process.wait(timeout=10)
        except psutil.TimeoutExpired:
            if abs(process.create_time() - created) <= 0.01:
                process.kill(); process.wait(timeout=5)
    print(json.dumps({'state':'matched', 'pid':process.pid, 'create_time':created}))
except psutil.NoSuchProcess:
    print(json.dumps({'state':'stale'}))
except Exception:
    print(json.dumps({'state':'unavailable'}))
`;

function inspectProcess(mode, pid, birth = '-') {
  if (!python) throw new Error('Project Python runtime required for safe process ownership.');
  const result = spawnSync(python, ['-c', processCheck, mode, String(pid), String(birth), process.execPath, JSON.stringify(args)],
    { cwd: root, encoding: 'utf8', windowsHide: true, timeout: 20000 });
  if (result.status !== 0) throw new Error('Could not verify preview process ownership.');
  const value = JSON.parse(result.stdout);
  if (!['matched', 'stale'].includes(value.state)) throw new Error('Preview process ownership mismatch; no process was stopped.');
  return value;
}

function readOwner() {
  if (!existsSync(ownerFile)) return null;
  const value = JSON.parse(readFileSync(ownerFile, 'utf8'));
  if (!Number.isSafeInteger(value.pid) || !Number.isFinite(value.create_time) || typeof value.run_id !== 'string') throw new Error('Invalid preview ownership record.');
  return value;
}

function removeOwner(runId) {
  const value = readOwner();
  if (value?.run_id === runId) unlinkSync(ownerFile);
}

function stopRecorded() {
  const owner = readOwner();
  if (!owner) { console.log('No owned product preview process recorded.'); return; }
  inspectProcess('stop', owner.pid, owner.create_time);
  removeOwner(owner.run_id);
  console.log('Stopped owned product preview. Other services were left running.');
}

async function requireFreePort() {
  await new Promise((accept, reject) => {
    const probe = createServer();
    probe.once('error', () => reject(new Error('Product preview port 3001 is occupied; existing service was left running.')));
    probe.listen({ host: '127.0.0.1', port: 3001, exclusive: true }, () => probe.close(accept));
  });
}

async function start() {
  const previous = readOwner();
  if (previous) {
    const state = inspectProcess('inspect', previous.pid, previous.create_time);
    if (state.state === 'matched') throw new Error('Owned product preview is already running; use --stop before restarting.');
    removeOwner(previous.run_id);
  }
  await requireFreePort();
  if (!python) throw new Error('Project Python runtime required for safe preview lifecycle.');
  const runId = randomUUID();
  let owned = false;
  let stopping = false;
  let stopTimer;
  const child = spawn(process.execPath, args, {
    cwd: resolve(root, 'apps/web'), stdio: 'inherit', windowsHide: true,
    env: { ...process.env, API_BASE_URL: 'http://127.0.0.1:8001',
      CANCEROS_SYNTHETIC_DEMO: '1', EXTERNAL_INFERENCE_ENABLED: 'false' },
  });
  function cleanup() {
    if (child.exitCode === null && child.signalCode === null) child.kill('SIGTERM');
    // Forced wrapper termination cannot run hooks. Keep its durable ownership
    // record until child exit or explicit --stop, so the orphan can be stopped.
  }
  function stop() {
    if (stopping) return;
    stopping = true;
    cleanup();
    stopTimer = setTimeout(() => {
      if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
    }, 10000);
    stopTimer.unref();
  }
  process.on('SIGINT', stop);
  process.on('SIGTERM', stop);
  process.on('SIGHUP', stop);
  process.on('exit', cleanup);
  child.once('exit', (code, signal) => {
    clearTimeout(stopTimer);
    if (owned) {
      try { removeOwner(runId); } catch { /* Preserve ambiguous metadata. */ }
    }
    process.exitCode = stopping ? 0 : code ?? (signal ? 1 : 0);
  });
  child.once('error', () => {
    console.error('Could not start product preview. Build the application first.');
    process.exitCode = 1;
  });
  try {
    const identity = inspectProcess('inspect', child.pid);
    if (identity.state !== 'matched') throw new Error('Preview exited before process ownership could be recorded.');
    mkdirSync(dirname(ownerFile), { recursive: true });
    writeFileSync(ownerFile, JSON.stringify({ pid: identity.pid, create_time: identity.create_time, run_id: runId }), { flag: 'wx', mode: 0o600 });
    owned = true;
  } catch (error) {
    stop();
    throw error;
  }
}

try {
  if (process.argv.slice(2).length && process.argv[2] !== '--stop') throw new Error('Use this script with no arguments or --stop.');
  if (process.argv[2] === '--stop') stopRecorded();
  else await start();
} catch (error) {
  console.error(error instanceof Error ? error.message : 'Product preview could not complete safely.');
  process.exitCode = 1;
}
