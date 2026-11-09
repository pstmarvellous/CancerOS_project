// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GET, POST } from './route';

const project = '00000000-0000-4000-8000-000000000001';
const patient = '00000000-0000-4000-8000-000000000002';
const base = `http://127.0.0.1:3001/api/case-imaging-workflow?project=${project}&patient=${patient}`;
const backend = `http://127.0.0.1:8000/api/v1/projects/${project}/patients/${patient}`;
const fetch = vi.fn();
const request = (url = base, init?: RequestInit) =>
  new Request(url, { ...init, headers: { authorization: '******', ...init?.headers } });
beforeEach(() => { fetch.mockReset(); vi.stubGlobal('fetch', fetch); vi.stubEnv('API_BASE_URL', 'http://127.0.0.1:8000'); });
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe('case imaging workflow proxy', () => {
  it('rejects unknown or ambiguous resources without contacting the backend', async () => {
    for (const url of [`${base}&resource=other`, `${base}&resource=acquisition`, base.replace(patient, 'invalid'), `${base}&id=one&id=two&resource=acquisition`]) {
      expect((await GET(request(url))).status).toBe(400);
    }
    expect((await POST(request(`${base}&resource=other`, { method: 'POST', body: '{}' }))).status).toBe(400);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('proxies the owned import list and acquisition read with session authorization', async () => {
    fetch.mockResolvedValue(Response.json({ items: [] }));
    const listed = await GET(request(`${base}&resource=imports`));
    expect(listed.status).toBe(200);
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(String(fetch.mock.calls[0][0])).toBe(`${backend}/imaging-imports`);

    fetch.mockReset();
    fetch.mockResolvedValue(Response.json({ import_id: 'import-1' }));
    const detail = await GET(request(`${base}&resource=acquisition&id=import-1`));
    expect(detail.status).toBe(200);
    expect(String(fetch.mock.calls[0][0])).toBe(`${backend}/acquisitions/import-1`);
    for (const call of fetch.mock.calls) {
      expect(call[1]).toMatchObject({ method: 'GET', headers: { authorization: '******' }, cache: 'no-store' });
    }
  });

  it('proxies geometry, job and QC writes with the caller body, never inventing endpoints', async () => {
    fetch.mockResolvedValue(Response.json({ id: 'job-1' }));
    const created = await POST(request(`${base}&resource=job`, { method: 'POST', headers: { 'content-type': 'application/json', 'idempotency-key': 'key-1' }, body: '{"expected_revision":1}' }));
    expect(created.status).toBe(200);
    expect(String(fetch.mock.calls[0][0])).toBe(`${backend}/imaging-jobs`);
    expect(fetch.mock.calls[0][1]).toMatchObject({ method: 'POST' });
    expect(fetch.mock.calls[0][1].headers['idempotency-key']).toBe('key-1');
    expect(fetch.mock.calls[0][1].body).toBe('{"expected_revision":1}');
  });

  it('preserves backend denial rather than presenting an empty workflow', async () => {
    fetch.mockResolvedValue(Response.json({}, { status: 403 }));
    expect((await GET(request(`${base}&resource=imports`))).status).toBe(403);
  });
});
