import { caseParams, caseUrl, proxyCase } from '../../../lib/case-proxy';

export const dynamic = 'force-dynamic';

function bad(message: string, status = 400): Response {
  return Response.json({ title: message }, { status });
}

export async function GET(request: Request) {
  const { project, patient } = caseParams(request);
  if (!project || !patient) return bad('Missing project or patient');
  const incoming = new URL(request.url);
  const resource = incoming.searchParams.get('resource');
  const branch = incoming.searchParams.get('branch');
  const state = incoming.searchParams.get('state');
  const cursor = incoming.searchParams.get('cursor');

  if (resource === 'branches') {
    const url = caseUrl(project, patient, '/branches');
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'states') {
    if (!branch) return bad('Missing branch selection');
    const url = caseUrl(project, patient, `/states?branch_id=${encodeURIComponent(branch)}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'state') {
    if (!state) return bad('Missing state selection');
    const url = caseUrl(project, patient, `/states/${encodeURIComponent(state)}`);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'fusion') {
    if (!state) return bad('Missing state selection');
    const url = caseUrl(project, patient, '/fusion-queries');
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'POST', JSON.stringify({ state_id: state }));
  }
  return bad('Unknown state timeline resource');
}
