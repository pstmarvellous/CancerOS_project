// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GET } from './route';

const project = '00000000-0000-4000-8000-000000000001';
const base = `http://127.0.0.1:3001/api/provider-capabilities?project=${project}`;
const fetch = vi.fn();
const request = (url = base) => new Request(url, { headers: { authorization: '******' } });
beforeEach(() => { fetch.mockReset(); vi.stubGlobal('fetch', fetch); vi.stubEnv('API_BASE_URL', 'http://127.0.0.1:8000'); });
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe('provider capabilities proxy', () => {
  it('denies absent authorization without contacting the backend', async () => {
    expect((await GET(new Request(base))).status).toBe(401);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('rejects invalid project scope without contacting the backend', async () => {
    expect((await GET(request(base.replace(project, 'invalid')))).status).toBe(400);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('forwards the project-scoped capabilities read with session authorization', async () => {
    const body = { schema_version: 'provider-capabilities/1', local_summary_available: true, external_model_available: false };
    fetch.mockResolvedValue(Response.json(body));
    const response = await GET(request());
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(body);
    expect(String(fetch.mock.calls[0][0])).toBe(`http://127.0.0.1:8000/api/v1/projects/${project}/ai/capabilities`);
    expect(fetch.mock.calls[0][1]).toMatchObject({ method: 'GET', headers: { authorization: '******' }, cache: 'no-store' });
  });

  it('preserves backend denial rather than claiming availability', async () => {
    fetch.mockResolvedValue(Response.json({}, { status: 403 }));
    expect((await GET(request())).status).toBe(403);
  });
});
