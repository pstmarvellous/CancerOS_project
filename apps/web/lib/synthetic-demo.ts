import { createHash, randomUUID } from 'node:crypto';
import { readFileSync, statSync } from 'node:fs';
import { basename, dirname, resolve } from 'node:path';
import type { DemoBundle } from './demo-contracts';
import { onlyKeys, surfaceDigest, validScenario } from './demo-integrity';
export { surfaceDigest } from './demo-integrity';

export const DEMO_COOKIE = 'canceros-synthetic-demo';
export function bundleFile(): string {
  // Next may start with the repository root or apps/web as the working
  // directory depending on the launcher. Prefer an explicit override, then
  // probe both layouts so normal startup always finds the prepared bundle.
  const override = process.env.CANCEROS_SYNTHETIC_DEMO_FILE;
  if (override) return resolve(override);
  const candidates = [
    resolve(process.cwd(), '.local', 'synthetic-demo.json'),
    resolve(process.cwd(), '..', '..', '.local', 'synthetic-demo.json'),
  ];
  for (const candidate of candidates) {
    try {
      if (statSync(candidate).isFile()) return candidate;
    } catch {
      /* try the next layout */
    }
  }
  // The repository layout is stable even when preparation happens after startup.
  const cwd = process.cwd();
  return resolve(basename(cwd) === 'web' && basename(dirname(cwd)) === 'apps' ? resolve(cwd, '../..') : cwd, '.local', 'synthetic-demo.json');
}
const FAMILIES = ['SC-01', 'SC-02', 'SC-03', 'SC-04', 'SC-05'];
const memory = globalThis as unknown as {
  cancerosDemoSessions?: Map<string, { expires: number; fingerprint: string }>;
};
let cached: { stamp: string; bundle: DemoBundle; fingerprint: string } | undefined;

export function validateDemoBundle(value: unknown): value is DemoBundle {
  try {
    const bundle = value as DemoBundle;
    if (!onlyKeys(bundle, 'version syntheticOnly sourceOrigin caseLabel preparedAt expiresAt scenarios') || bundle.version !== 'synthetic-demo/2' || bundle.syntheticOnly !== true ||
      bundle.sourceOrigin !== 'synthetic_engineering_fixture' || bundle.caseLabel !== 'Research Demo 01' ||
      typeof bundle.preparedAt !== 'string' || !/(?:Z|[+-]\d{2}:\d{2})$/.test(bundle.preparedAt) ||
      typeof bundle.expiresAt !== 'string' || !/(?:Z|[+-]\d{2}:\d{2})$/.test(bundle.expiresAt) ||
      !Number.isFinite(Date.parse(bundle.preparedAt)) || Date.parse(bundle.preparedAt) > Date.now() + 60000 ||
      !Number.isFinite(Date.parse(bundle.expiresAt)) || Date.parse(bundle.expiresAt) <= Date.now() ||
      Date.parse(bundle.expiresAt) <= Date.parse(bundle.preparedAt) ||
      Date.parse(bundle.expiresAt) - Date.parse(bundle.preparedAt) > 7 * 86400000 ||
      Object.keys(bundle.scenarios).sort().join(',') !== FAMILIES.join(',')) return false;
    const raw = JSON.stringify(bundle);
    if (/https?:\/\/|file:\/\/|Bearer |"(?:token|authorization|object_key|mapping_id|linkage_keys|secret)"/i.test(raw)) return false;
    for (const id of FAMILIES) {
      const scenario = bundle.scenarios[id];
      if (!validScenario(scenario, id)) return false;
    }
    const scenarios = Object.values(bundle.scenarios);
    if (new Set(scenarios.map(s => s.timeline.window.scope.branch_id)).size !== 5 || new Set(scenarios.map(s => s.timeline.window.scope.run_id)).size !== 5) return false;
    const baselineOf = (scenario: typeof scenarios[number]) => scenario.timeline.items.find(p => p.measurement_basis === 'baseline_reference')!;
    const first = baselineOf(scenarios[0]);
    const surface = surfaceDigest(scenarios[0].meshes[first.id]);
    for (const scenario of scenarios.slice(1)) {
      const point = baselineOf(scenario);
      if (point.patient_id !== first.patient_id || point.lesion_id !== first.lesion_id || point.source_hash !== first.source_hash || point.source_ids[0] !== first.source_ids[0] ||
        point.exact_value !== first.exact_value || surfaceDigest(scenario.meshes[point.id]) !== surface) return false;
    }
    return true;
  } catch { return false; }
}
let lastDiagnostic = '';
function unavailable(reason: string) {
  if (lastDiagnostic !== reason) console.warn(`[synthetic-demo] ${reason}; run npm run demo:prepare, then retry.`);
  lastDiagnostic = reason;
  return null;
}
export function demoBundle() {
  if (process.env.CANCEROS_SYNTHETIC_DEMO !== '1') return unavailable('disabled: use the supported demo or foundation launcher');
  try {
    const file = bundleFile();
    const info = statSync(file);
    if (info.size > 20 * 1024 * 1024) return unavailable('oversized bundle');
    const stamp = `${file}:${info.mtimeMs}:${info.size}`;
    if (cached?.stamp === stamp) return Date.parse(cached.bundle.expiresAt) > Date.now() ? cached : unavailable('expired bundle');
    const raw = readFileSync(file, 'utf8');
    const bundle: unknown = JSON.parse(raw);
    if (bundle && typeof bundle === 'object' && 'expiresAt' in bundle && typeof bundle.expiresAt === 'string' && Date.parse(bundle.expiresAt) <= Date.now()) return unavailable('expired bundle');
    if (!validateDemoBundle(bundle)) return unavailable('invalid bundle schema, provenance or artifact integrity');
    cached = { stamp, bundle, fingerprint: createHash('sha256').update(raw).digest('hex') };
    lastDiagnostic = '';
    return cached;
  } catch (error) {
    return unavailable(error instanceof SyntaxError ? 'invalid JSON' : (error as NodeJS.ErrnoException)?.code === 'ENOENT' ? 'missing bundle' : 'unreadable bundle');
  }
}
function sessions() { return memory.cancerosDemoSessions ??= new Map(); }
export function newDemoSession(fingerprint: string, expiresAt: string) {
  for (const [id, entry] of sessions()) if (entry.expires <= Date.now()) sessions().delete(id);
  if (sessions().size >= 512) sessions().delete(sessions().keys().next().value!);
  const id = randomUUID();
  const expires = Math.min(Date.now() + 2 * 3600000, Date.parse(expiresAt));
  sessions().set(id, { expires, fingerprint });
  return { id, expires };
}
export function hasDemoSession(id: string | undefined, fingerprint: string) {
  const entry = id ? sessions().get(id) : undefined;
  return !!entry && entry.expires > Date.now() && entry.fingerprint === fingerprint;
}
