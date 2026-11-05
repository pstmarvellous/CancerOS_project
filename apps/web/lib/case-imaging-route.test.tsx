// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GET } from '../app/api/case-imaging/route';

const project = '00000000-0000-4000-8000-000000000001';
const patient = '00000000-0000-4000-8000-000000000002';
const base = `http://127.0.0.1:3001/api/case-imaging?project=${project}&patient=${patient}`;
const study = { study_id: 'study', import_count: 2, series_count: 3, status: 'associated', next_action: 'review' };
const mask = { segmentation_id: 'mask', batch_id: 'batch', label_value: 1, mask_type: 'verified_lesion', qc_status: 'pending', next_action: 'review' };
const fetch = vi.fn();
const request = (url = base, authorized = true) => new Request(url, { headers: authorized ? { authorization: 'Bearer test-credential' } : {} });
beforeEach(() => { fetch.mockReset(); vi.stubGlobal('fetch', fetch); vi.stubEnv('API_BASE_URL', 'http://127.0.0.1:8000'); });
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); });
describe('authorized imaging discovery proxy', () => {
  it('denies absent authorization without contacting the backend', async () => {
    expect((await GET(request(base, false))).status).toBe(401);
    expect(fetch).not.toHaveBeenCalled();
  });
  it.each([`${base}&project=${project}`, `${base}&resource=other`, base.replace(patient, 'invalid')])('rejects invalid or ambiguous scope %s', async url => {
    expect((await GET(request(url))).status).toBe(400);
    expect(fetch).not.toHaveBeenCalled();
  });
  it('returns an empty authorized study page without claiming zero masks', async () => {
    fetch.mockResolvedValue(Response.json({ items: [] }));
    const response = await GET(request());
    expect(response.status).toBe(200);
    expect(response.headers.get('cache-control')).toContain('no-store');
    expect(await response.json()).toEqual({ studies: { items: [] }, segmentations: null });
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it('forwards only the two fixed patient-owned reads and projects their approved fields', async () => {
    fetch.mockResolvedValueOnce(Response.json({ items: [{ ...study, restricted_extra: 'excluded' }] }))
      .mockResolvedValueOnce(Response.json([{ ...mask, restricted_extra: 'excluded' }]));
    const response = await GET(request());
    expect(await response.json()).toEqual({ studies: { items: [study] }, segmentations: [mask] });
    expect(fetch.mock.calls.map(call => String(call[0]))).toEqual([
      `http://127.0.0.1:8000/api/v1/projects/${project}/patients/${patient}/studies`,
      `http://127.0.0.1:8000/api/v1/projects/${project}/patients/${patient}/segmentation-discoveries`,
    ]);
    for (const call of fetch.mock.calls) expect(call[1]).toMatchObject({ method: 'GET', headers: { authorization: 'Bearer test-credential' }, cache: 'no-store', redirect: 'error' });
  });
  it('preserves unavailable segmentation status after an authorized study read', async () => {
    fetch.mockResolvedValueOnce(Response.json({ items: [study] })).mockResolvedValueOnce(Response.json({}, { status: 404 }));
    const response = await GET(request());
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ studies: { items: [study] }, segmentations: null });
  });
  it.each([401, 403])('preserves backend denial %s rather than presenting an empty case', async status => {
    fetch.mockResolvedValueOnce(Response.json({ items: [study] })).mockResolvedValueOnce(Response.json({}, { status }));
    expect((await GET(request())).status).toBe(status);
  });
  it('rejects malformed discovery counts instead of displaying fabricated values', async () => {
    fetch.mockResolvedValue(Response.json({ items: [{ ...study, series_count: -1 }] }));
    expect((await GET(request())).status).toBe(502);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
