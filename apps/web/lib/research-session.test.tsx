// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DELETE, GET, POST } from '../app/api/research-session/route';
import { proxyCase } from './case-proxy';
import { credentialExpiry, RESEARCH_COOKIE, researchAuthorization, researchSession, secureResearchTransport } from './research-session';

const project = { project_id: '00000000-0000-4000-8000-000000000001', name: 'Authorized study', role: 'editor' };
const workspace = { user_id: 'internal-user', projects: [{ ...project, private_extra: 'must-not-return' }] };
const origin = 'http://127.0.0.1:3000';
const upstream = new URL('http://127.0.0.1:8000/api/v1/projects/project/patients/patient');
// Metadata fixture only. The mocked backend stands in for signature verification;
// these tests do not certify authentic credentials or bypass the real API.
const token = (seconds = 3600, alg = 'RS256') => [
  Buffer.from(JSON.stringify({ alg })).toString('base64url'),
  Buffer.from(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + seconds })).toString('base64url'),
  'signature',
].join('.');
function request(method = 'GET', body?: unknown, headers: Record<string, string> = {}) {
  return new Request(`${origin}/api/research-session`, { method,
    headers: { ...(method !== 'GET' ? { origin, 'content-type': 'application/json' } : {}), ...headers },
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}) });
}
const sessionCookie = (response: Response) => response.headers.get('set-cookie')!.split(';')[0];
const fetchMock = vi.fn();
beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () => Response.json(workspace));
  (globalThis as unknown as { cancerosResearchSessions?: Map<string, unknown> }).cancerosResearchSessions?.clear();
});
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

describe('authorized research sessions', () => {
  it('creates a random HttpOnly strict cookie after backend validation and returns safe projects', async () => {
    const credential = token();
    const response = await POST(request('POST', { token: credential }));
    expect(response.status).toBe(200);
    const cookie = response.headers.get('set-cookie')!;
    expect(cookie).toContain('HttpOnly'); expect(cookie).toContain('SameSite=strict'); expect(cookie).toContain('Path=/');
    expect(cookie).not.toContain(credential);
    const body = await response.json();
    expect(body).toEqual({ authenticated: true, projects: [project], expiresAt: expect.any(String) });
    expect(JSON.stringify(body)).not.toMatch(/token|internal-user|private_extra/);
    expect(Date.parse(body.expiresAt) - Date.now()).toBeLessThanOrEqual(30 * 60 * 1000);
    const call = fetchMock.mock.calls[0];
    expect(String(call[0])).toBe('http://127.0.0.1:8000/api/v1/workspace');
    expect(call[1]).toMatchObject({ headers: { authorization: `Bearer ${credential}` }, cache: 'no-store', redirect: 'error' });
    expect(researchAuthorization(request('GET', undefined, { cookie: sessionCookie(response) }))).toBe(`Bearer ${credential}`);
  });

  it('sets Secure on HTTPS sessions', async () => {
    const response = await POST(new Request('https://research.example/api/research-session', {
      method: 'POST', headers: { origin: 'https://research.example', 'content-type': 'application/json' }, body: JSON.stringify({ token: token() }),
    }));
    expect(response.status).toBe(200); expect(response.headers.get('set-cookie')).toContain('Secure');
  });

  it('allows HTTP only for loopback development and denies remote HTTP login', async () => {
    expect(secureResearchTransport('http://localhost:3000')).toBe(true);
    expect(secureResearchTransport('http://[::1]:3000')).toBe(true);
    expect(secureResearchTransport('http://localhost.attacker.example:3000')).toBe(false);
    const response = await POST(new Request('http://research.example/api/research-session', {
      method: 'POST', headers: { origin: 'http://research.example', 'content-type': 'application/json' }, body: JSON.stringify({ token: token() }),
    }));
    expect(response.status).toBe(403); expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each(['https://attacker.example', 'null', `${origin}.attacker.example`])('denies login from %s without contacting backend', async badOrigin => {
    expect((await POST(request('POST', { token: token() }, { origin: badOrigin }))).status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('denies login without Origin or with cross-site metadata', async () => {
    const withoutOrigin = request('POST', { token: token() }); withoutOrigin.headers.delete('origin');
    expect((await POST(withoutOrigin)).status).toBe(403);
    expect((await POST(request('POST', { token: token() }, { 'sec-fetch-site': 'cross-site' }))).status).toBe(403);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each([undefined, '', 'Bearer token', 'not.a.jwt', token(-1), token(3600, 'none'), token(3600, 'HS256')])('rejects invalid metadata before API access (%s)', async credential => {
    expect((await POST(request('POST', { token: credential }))).status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('requires JSON, bounded request size and only the credential field', async () => {
    expect((await POST(request('POST', { token: token() }, { 'content-type': 'text/plain' }))).status).toBe(415);
    expect((await POST(request('POST', { token: 'x'.repeat(20001) }))).status).toBe(413);
    expect((await POST(request('POST', { token: token(), role: 'admin' }))).status).toBe(400);
    const malformed = new Request(`${origin}/api/research-session`, { method: 'POST', headers: { origin, 'content-type': 'application/json' }, body: '{' });
    expect((await POST(malformed)).status).toBe(400);
  });

  it('does not accept an unverified credential when backend denies it', async () => {
    fetchMock.mockResolvedValue(Response.json({ detail: 'Unauthorized' }, { status: 401 }));
    const response = await POST(request('POST', { token: token() }));
    expect(response.status).toBe(401); expect(response.headers.has('set-cookie')).toBe(false);
  });

  it('does not save credentials on backend outage or invalid workspace', async () => {
    fetchMock.mockRejectedValueOnce(new Error('sensitive upstream error'));
    const response = await POST(request('POST', { token: token() }));
    expect(response.status).toBe(502); expect(await response.text()).not.toContain('sensitive');
    expect(response.headers.has('set-cookie')).toBe(false);
    fetchMock.mockResolvedValueOnce(Response.json({ projects: [{ ...project, role: 'superuser' }] }));
    expect((await POST(request('POST', { token: token() }))).status).toBe(502);
  });

  it('expires at the credential lifetime and denies the cookie after expiry', async () => {
    vi.useFakeTimers(); vi.setSystemTime(new Date('2026-11-05T12:00:00Z'));
    const credential = token(60);
    const response = await POST(request('POST', { token: credential }));
    const browser = request('GET', undefined, { cookie: sessionCookie(response) });
    expect(Date.parse((await response.json()).expiresAt)).toBe(credentialExpiry(credential));
    expect(researchSession(browser)).not.toBeNull();
    vi.advanceTimersByTime(60001);
    expect(researchSession(browser)).toBeNull();
    expect(await (await GET(browser)).json()).toEqual({ authenticated: false, projects: [] });
  });

  it('rechecks current project membership on session GET and clears revoked access', async () => {
    const response = await POST(request('POST', { token: token() }));
    const browser = request('GET', undefined, { cookie: sessionCookie(response) });
    fetchMock.mockResolvedValueOnce(Response.json({ projects: [{ ...project, role: 'viewer' }] }));
    expect((await (await GET(browser)).json()).projects).toEqual([{ ...project, role: 'viewer' }]);
    fetchMock.mockResolvedValueOnce(Response.json({}, { status: 401 }));
    expect(await (await GET(browser)).json()).toEqual({ authenticated: false, projects: [] });
    expect(researchAuthorization(browser)).toBeNull();
  });

  it('rotates session IDs after sign-in and invalidates the previous session', async () => {
    const first = await POST(request('POST', { token: token() }));
    const oldCookie = sessionCookie(first);
    const second = await POST(request('POST', { token: token() }, { cookie: oldCookie }));
    expect(sessionCookie(second)).not.toBe(oldCookie);
    expect(researchSession(request('GET', undefined, { cookie: oldCookie }))).toBeNull();
  });

  it('requires same-origin logout then invalidates both memory and cookie', async () => {
    const response = await POST(request('POST', { token: token() }));
    const cookie = sessionCookie(response);
    expect((await DELETE(request('DELETE', undefined, { cookie, origin: 'https://attacker.example' }))).status).toBe(403);
    expect(researchSession(request('GET', undefined, { cookie }))).not.toBeNull();
    const logout = await DELETE(request('DELETE', undefined, { cookie }));
    expect(logout.headers.get('set-cookie')).toContain('Max-Age=0');
    expect(researchSession(request('GET', undefined, { cookie }))).toBeNull();
  });

  it('never treats demo cookies, arbitrary IDs or duplicate cookies as research sessions', async () => {
    const response = await POST(request('POST', { token: token() }));
    for (const cookie of ['canceros-synthetic-demo=valid-demo-id', `${RESEARCH_COOKIE}=guessed`, `${sessionCookie(response)}; ${sessionCookie(response)}`]) {
      expect(researchAuthorization(request('GET', undefined, { cookie }))).toBeNull();
      expect(await (await GET(request('GET', undefined, { cookie }))).json()).toEqual({ authenticated: false, projects: [] });
    }
  });
});

describe('research case proxy authentication and CSRF', () => {
  it('denies anonymous and synthetic-demo requests before backend access', async () => {
    for (const cookie of ['', 'canceros-synthetic-demo=demo']) {
      expect((await proxyCase(request('GET', undefined, { cookie }), upstream, 'GET')).status).toBe(401);
    }
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('forwards the session credential, idempotency/precondition and backend ETag', async () => {
    const credential = token();
    const session = await POST(request('POST', { token: credential }));
    fetchMock.mockResolvedValueOnce(Response.json({ saved: true }, { status: 201, headers: { etag: '"patient-2"', location: '/saved' } }));
    const response = await proxyCase(request('POST', undefined, { cookie: sessionCookie(session), 'if-match': '"patient-1"', 'idempotency-key': 'request-key' }), upstream, 'POST', '{"source":"record"}');
    expect(response.status).toBe(201); expect(response.headers.get('etag')).toBe('"patient-2"');
    expect(response.headers.get('cache-control')).toBe('private, no-store');
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ headers: { authorization: `Bearer ${credential}`, 'if-match': '"patient-1"', 'idempotency-key': 'request-key', 'content-type': 'application/json' }, redirect: 'error' });
  });

  it('denies cookie writes without exact origin, including same-site siblings', async () => {
    const session = await POST(request('POST', { token: token() }));
    fetchMock.mockClear();
    for (const originHeader of [null, 'null', 'http://localhost:3000', 'https://attacker.example']) {
      const browser = request('POST', undefined, { cookie: sessionCookie(session) });
      if (originHeader === null) browser.headers.delete('origin'); else browser.headers.set('origin', originHeader);
      expect((await proxyCase(browser, upstream, 'POST', '{}')).status).toBe(403);
    }
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('preserves explicit bearer API clients and denies explicit cross-origin requests', async () => {
    const api = new Request(`${origin}/api/case-batch`, { method: 'POST', headers: { authorization: 'Bearer explicit-token' } });
    expect((await proxyCase(api, upstream, 'POST', '{}')).status).toBe(200);
    expect(fetchMock.mock.calls[0][1].headers.authorization).toBe('Bearer explicit-token');
    api.headers.set('origin', 'https://attacker.example');
    expect((await proxyCase(api, upstream, 'POST', '{}')).status).toBe(403);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('invalidates an expired backend credential instead of silently falling back', async () => {
    const session = await POST(request('POST', { token: token() }));
    const browser = request('GET', undefined, { cookie: sessionCookie(session) });
    fetchMock.mockResolvedValueOnce(Response.json({}, { status: 401 }));
    expect((await proxyCase(browser, upstream, 'GET')).status).toBe(401);
    expect(researchAuthorization(browser)).toBeNull();
  });
});
