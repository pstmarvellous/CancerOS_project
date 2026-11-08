import { caseParams, caseUrl, proxyCase } from '../../../lib/case-proxy';

export const dynamic = 'force-dynamic';

function bad(message: string, status = 400): Response {
  return Response.json({ title: message }, { status });
}

function interpretationIdOf(bodyText: string): string | null {
  try {
    const parsed = JSON.parse(bodyText) as {
      interpretation_snapshot_id?: unknown;
      interpretation?: { context_snapshot_id?: unknown };
    };
    const direct = parsed.interpretation_snapshot_id;
    if (typeof direct === 'string' && direct) return direct;
    const nested = parsed.interpretation?.context_snapshot_id;
    return typeof nested === 'string' && nested ? nested : null;
  } catch {
    return null;
  }
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
    const interpretationId = interpretationIdOf(bodyText);
    if (!interpretationId) return bad('Missing interpretation identity');
    const url = stateUrl(project, patient, state, `/interpretations/${encodeURIComponent(interpretationId)}/grounding`);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'POST', JSON.stringify({ interpretation_snapshot_id: interpretationId }));
  }
  if (action === 'save') {
    if (!state) return bad('Missing state selection');
    const interpretationId = interpretationIdOf(bodyText);
    if (!interpretationId) return bad('Missing interpretation identity');
    const url = stateUrl(project, patient, state, `/interpretations/${encodeURIComponent(interpretationId)}/saved-results`);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'POST', bodyText);
  }
  return bad('Unknown insights action');
}
