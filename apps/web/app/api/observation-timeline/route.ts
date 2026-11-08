import { caseParams, caseUrl, proxyCase } from '../../../lib/case-proxy';

export const dynamic = 'force-dynamic';

function bad(message: string, status = 400): Response {
  return Response.json({ title: message }, { status });
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(request: Request) {
  const { project, patient } = caseParams(request);
  if (!project || !patient) return bad('Missing project or patient');
  const incoming = new URL(request.url);
  const action = incoming.searchParams.get('action');
  const mesh = incoming.searchParams.get('mesh');
  if (action === 'updates-latest') {
    const branchId = incoming.searchParams.get('branch_id');
    const url = caseUrl(project, patient, '/dependent-updates/latest' + (branchId ? '?branch_id=' + encodeURIComponent(branchId) : ''));
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'GET');
  }
  if (action === 'job') {
    const jobId = incoming.searchParams.get('job');
    if (!jobId || !UUID.test(jobId)) return bad('Missing job selection');
    const url = caseUrl(project, patient, '/imaging-jobs/' + encodeURIComponent(jobId));
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'GET');
  }
  if (mesh && UUID.test(mesh)) {
    const url = caseUrl(project, patient, `/synthetic-geometry-results/${encodeURIComponent(mesh)}/mesh`);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'GET');
  }
  return bad('Unknown observation timeline resource');
}

export async function POST(request: Request) {
  const { project, patient } = caseParams(request);
  if (!project || !patient) return bad('Missing project or patient');
  const incoming = new URL(request.url);
  const action = incoming.searchParams.get('action');
  const bodyText = await request.text();
  const forward = (suffix: string) => {
    const url = caseUrl(project, patient, suffix);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'POST', bodyText);
  };
  if (action === 'timeline') return forward('/timeline-queries');
  if (action === 'trends') return forward('/trend-queries');
  if (action === 'fusion') return forward('/fusion-queries');
  if (action === 'updates') return forward('/dependent-updates');
  if (action === 'job-cancel') {
    const jobId = incoming.searchParams.get('job');
    if (!jobId || !UUID.test(jobId)) return bad('Missing job selection');
    const url = caseUrl(project, patient, '/imaging-jobs/' + encodeURIComponent(jobId) + '/cancellations');
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'POST', bodyText);
  }
  return bad('Unknown observation timeline action');
}
