import { randomBytes } from 'node:crypto';

export const RESEARCH_COOKIE = 'canceros-research-session';
const SESSION_DURATION_MS = 30 * 60 * 1000;
const MAX_SESSIONS = 512;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
export type ResearchProject = { project_id: string; name: string; role: 'viewer' | 'editor' | 'admin' };
export type ResearchWorkspace = { projects: ResearchProject[] };
type Session = { token: string; expires: number };
const memory = globalThis as unknown as { cancerosResearchSessions?: Map<string, Session> };
const sessions = () => memory.cancerosResearchSessions ??= new Map();

// This reads only expiry metadata. The API independently verifies the RS256
// signature, issuer, audience, time claims and current database memberships.
export function credentialExpiry(token: unknown): number | null {
  if (typeof token !== 'string' || token.length > 16384 || !/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(token)) return null;
  try {
    const [header, payload] = token.split('.').slice(0, 2).map(part => JSON.parse(Buffer.from(part, 'base64url').toString('utf8')));
    if (header?.alg !== 'RS256' || typeof payload?.exp !== 'number' || !Number.isFinite(payload.exp)) return null;
    const expires = payload.exp * 1000;
    return Number.isFinite(expires) && expires > Date.now() ? expires : null;
  } catch { return null; }
}

export function researchCookieId(request: Request): string | undefined {
  const entries = (request.headers.get('cookie') ?? '').split(';')
    .map(part => part.trim()).filter(part => part.startsWith(`${RESEARCH_COOKIE}=`));
  if (entries.length !== 1) return undefined;
  const id = entries[0].slice(RESEARCH_COOKIE.length + 1);
  return /^[A-Za-z0-9_-]{43}$/.test(id) ? id : undefined;
}

export function newResearchSession(token: string, credentialExpires: number) {
  for (const [id, session] of sessions()) if (session.expires <= Date.now()) sessions().delete(id);
  if (sessions().size >= MAX_SESSIONS) sessions().delete(sessions().keys().next().value!);
  const id = randomBytes(32).toString('base64url');
  const expires = Math.min(Date.now() + SESSION_DURATION_MS, credentialExpires);
  sessions().set(id, { token, expires });
  return { id, expires };
}

export function researchSession(request: Request): Session | null {
  const id = researchCookieId(request);
  if (!id) return null;
  const session = sessions().get(id);
  if (!session) return null;
  if (session.expires <= Date.now()) { sessions().delete(id); return null; }
  return session;
}

export function deleteResearchSession(request: Request) {
  const id = researchCookieId(request);
  if (id) sessions().delete(id);
}

export function researchAuthorization(request: Request): string | null {
  const explicit = request.headers.get('authorization');
  if (explicit) return explicit;
  const session = researchSession(request);
  return session ? `Bearer ${session.token}` : null;
}

export function isSameResearchOrigin(request: Request): boolean {
  if (request.headers.get('sec-fetch-site') === 'cross-site') return false;
  try {
    const incoming = new URL(request.url);
    // Next may canonicalize loopback addresses. Host is the original browser
    // authority; never accept an untrusted forwarded-host header as that authority.
    const host = request.headers.get('host') ?? incoming.host;
    return request.headers.get('origin') === `${incoming.protocol}//${host}`;
  } catch { return false; }
}

export function allowedResearchWrite(request: Request): boolean {
  // An explicitly supplied bearer is retained for API clients. Browsers still
  // cannot attach it cross-origin through this proxy; cookie writes need Origin.
  if (request.headers.has('origin') || request.headers.get('sec-fetch-site') === 'cross-site') return isSameResearchOrigin(request);
  return !!request.headers.get('authorization') && !request.headers.has('sec-fetch-site');
}

export function secureResearchTransport(value: string | URL): boolean {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' || (url.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname));
  } catch { return false; }
}

export async function checkResearchWorkspace(token: string): Promise<
  { ok: true; workspace: ResearchWorkspace } | { ok: false; status: number }
> {
  try {
    const base = process.env.API_BASE_URL ?? 'http://127.0.0.1:8000';
    const url = new URL('/api/v1/workspace', base);
    if (!secureResearchTransport(url) || url.username || url.password) return { ok: false, status: 502 };
    const response = await fetch(url, { headers: { authorization: `Bearer ${token}` },
      cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(15000) });
    if (!response.ok) return { ok: false, status: [401, 403].includes(response.status) ? response.status : 502 };
    const body = await response.json() as { projects?: unknown };
    if (!Array.isArray(body.projects) || body.projects.length > 1000) return { ok: false, status: 502 };
    const seen = new Set<string>();
    const projects: ResearchProject[] = [];
    for (const item of body.projects) {
      if (!item || typeof item !== 'object' || !UUID.test(item.project_id) || typeof item.name !== 'string' ||
        item.name.length < 1 || item.name.length > 300 || !['viewer', 'editor', 'admin'].includes(item.role) || seen.has(item.project_id)) return { ok: false, status: 502 };
      seen.add(item.project_id);
      projects.push({ project_id: item.project_id, name: item.name, role: item.role });
    }
    return { ok: true, workspace: { projects } };
  } catch { return { ok: false, status: 502 }; }
}
