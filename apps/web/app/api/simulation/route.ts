import { caseParams, caseUrl, missingSelection, proxyCase } from '../../../lib/case-proxy';

export const dynamic = 'force-dynamic';

function bad(message: string, status = 400): Response {
  return Response.json({ title: message }, { status });
}

export async function GET(request: Request) {
  const { project, patient } = caseParams(request);
  if (!project || !patient) return missingSelection();
  const incoming = new URL(request.url);
  const resource = incoming.searchParams.get('resource');
  const branch = incoming.searchParams.get('branch');
  const config = incoming.searchParams.get('config');
  const run = incoming.searchParams.get('run');
  const job = incoming.searchParams.get('job');
  const completion = incoming.searchParams.get('completion');

  if (resource === 'branches') {
    const url = caseUrl(project, patient, '/branches');
    if (!url) return missingSelection();
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'branch' && branch) {
    const url = caseUrl(project, patient, `/branches/${encodeURIComponent(branch)}`);
    if (!url) return missingSelection();
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'current' && branch) {
    const url = caseUrl(project, patient, `/branches/${encodeURIComponent(branch)}/current-simulation`);
    if (!url) return missingSelection();
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'config' && config) {
    const url = caseUrl(project, patient, `/simulation-configs/${encodeURIComponent(config)}`);
    if (!url) return missingSelection();
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'run' && run) {
    const url = caseUrl(project, patient, `/simulation-runs/${encodeURIComponent(run)}`);
    if (!url) return missingSelection();
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'job' && job) {
    const url = caseUrl(project, patient, `/imaging-jobs/${encodeURIComponent(job)}`);
    if (!url) return missingSelection();
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'completion' && completion) {
    const url = caseUrl(project, patient, `/simulation-completions/${encodeURIComponent(completion)}`);
    if (!url) return missingSelection();
    return proxyCase(request, url, 'GET');
  }
  return bad('Unknown simulation resource');
}

export async function POST(request: Request) {
  const { project, patient } = caseParams(request);
  if (!project || !patient) return missingSelection();
  const incoming = new URL(request.url);
  const resource = incoming.searchParams.get('resource');
  const branch = incoming.searchParams.get('branch');
  const bodyText = await request.text();
  const forward = (suffix: string) => {
    const url = caseUrl(project, patient, suffix);
    if (!url) return missingSelection();
    return proxyCase(request, url, 'POST', bodyText);
  };

  if (resource === 'config' && branch) return forward(`/branches/${encodeURIComponent(branch)}/simulation-configs`);
  if (resource === 'run' && branch) return forward(`/branches/${encodeURIComponent(branch)}/simulation-runs`);
  if (resource === 'preview') return forward('/schedule-preview');
  if (resource === 'eligibility') return forward('/eligibility-checks');
  if (resource === 'job') return forward('/imaging-jobs');
  if (resource === 'complete') {
    try {
      const parsed = JSON.parse(bodyText) as { completion_id?: string };
      if (typeof parsed.completion_id !== 'string' || !parsed.completion_id) return bad('Missing completion selection');
      return forward(`/simulation-completions/${encodeURIComponent(parsed.completion_id)}/publications`);
    } catch {
      return bad('Invalid publication request');
    }
  }
  return bad('Unknown simulation resource');
}
