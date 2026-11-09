// @vitest-environment node
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { GET as detail } from '../app/api/case-detail/route';
import { GET as selection } from '../app/api/research-selection/route';
import { deleteResearchSession, newResearchSession, RESEARCH_COOKIE, researchSession } from './research-session';

const project = '00000000-0000-4000-8000-000000000001';
const patient = '00000000-0000-4000-8000-000000000002';
const fetchMock = vi.fn();
let cookie: string;
function request(path: string, headers: Record<string, string> = {}) {
  return new Request(`http://127.0.0.1:3000${path}`, { headers: { cookie, ...headers } });
}
const detailPath = `/api/case-detail?project=${project}&patient=${patient}`;
beforeEach(() => {
  const session = newResearchSession('artificial-private-token', Date.now() + 60000);
  cookie = `${RESEARCH_COOKIE}=${session.id}`;
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  fetchMock.mockImplementation(async () => Response.json({ patient_id: patient, private_note: 'must not escape selection' }));
});
afterEach(() => { deleteResearchSession(request('/')); vi.unstubAllGlobals(); });

it('restores only identifiers from a successful authorized case read and rechecks access', async () => {
  expect((await detail(request(detailPath))).status).toBe(200);
  const response = await selection(request('/api/research-selection'));
  expect(await response.json()).toEqual({ project, patient });
  expect(response.headers.get('cache-control')).toBe('private, no-store');
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(fetchMock.mock.calls[1][1]).toMatchObject({ cache: 'no-store', redirect: 'error', headers: { authorization: 'Bearer artificial-private-token' } });
});

it('does not remember denied reads or allow an explicit bearer to alter cookie selection', async () => {
  fetchMock.mockResolvedValueOnce(Response.json({}, { status: 404 }));
  await detail(request(detailPath));
  expect(researchSession(request('/'))?.lastCase).toBeUndefined();
  await detail(request(detailPath, { authorization: 'Bearer another-session' }));
  expect(researchSession(request('/'))?.lastCase).toBeUndefined();
});

it('forgets revoked selections without disclosing result content', async () => {
  await detail(request(detailPath));
  fetchMock.mockResolvedValueOnce(Response.json({ private_note: 'hidden' }, { status: 404 }));
  const response = await selection(request('/api/research-selection'));
  expect(response.status).toBe(404);
  expect(await response.json()).toEqual({});
  expect(researchSession(request('/'))?.lastCase).toBeUndefined();
});

it('does not disclose identifiers after sign-out or to bearer-only clients', async () => {
  await detail(request(detailPath));
  expect((await selection(request('/api/research-selection', { authorization: 'Bearer other' }))).status).toBe(401);
  deleteResearchSession(request('/'));
  const response = await selection(request('/api/research-selection'));
  expect(response.status).toBe(401);
  expect(await response.json()).toEqual({});
});
