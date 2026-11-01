import { caseParams, caseUrl, proxyCase } from '../../../lib/case-proxy';

export const dynamic = 'force-dynamic';

function bad(message: string, status = 400): Response {
  return Response.json({ title: message }, { status });
}

function stateUrl(project: string, patient: string, state: string, suffix: string): URL | null {
  return caseUrl(project, patient, `/states/${encodeURIComponent(state)}${suffix}`);
}

export async function POST(request: Request) {
  const { project, patient } = caseParams(request);
  if (!project || !patient) return bad('Missing project or patient');
  const incoming = new URL(request.url);
  const action = incoming.searchParams.get('action');
  const state = incoming.searchParams.get('state');
  const bodyText = await request.text();

  if (action === 'context') {
    if (!state) return bad('Missing state selection');
    const url = caseUrl(project, patient, '/interpretation-contexts');
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'POST', bodyText || '{}');
  }
  if (action === 'interpret') {
    if (!state) return bad('Missing state selection');
    const url = stateUrl(project, patient, state, '/interpretations');
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'POST', bodyText || '{}');
  }
  if (action === 'ground') {
    if (!state) return bad('Missing state selection');
    let interpretationId: string | null = null;
    try {
      interpretationId = (JSON.parse(bodyText) as { interpretation?: { context_snapshot_id?: string } }).interpretation?.context_snapshot_id ?? null;
    } catch {
      interpretationId = null;
    }
    if (!interpretationId) return bad('Missing interpretation identity');
    const url = stateUrl(project, patient, state, `/interpretations/${encodeURIComponent(interpretationId)}/grounding`);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'POST', bodyText);
  }
  if (action === 'save') {
    if (!state) return bad('Missing state selection');
    let interpretationId: string | null = null;
    try {
      interpretationId = (JSON.parse(bodyText) as { interpretation?: { context_snapshot_id?: string } }).interpretation?.context_snapshot_id ?? null;
    } catch {
      interpretationId = null;
    }
    if (!interpretationId) return bad('Missing interpretation identity');
    const url = stateUrl(project, patient, state, `/interpretations/${encodeURIComponent(interpretationId)}/saved-results`);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'POST', bodyText);
  }
  return bad('Unknown insights action');
}
