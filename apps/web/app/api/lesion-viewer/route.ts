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
  const lesion = incoming.searchParams.get('lesion');
  const report = incoming.searchParams.get('report');

  if (resource === 'lesions') {
    const url = caseUrl(project, patient, '/lesions');
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'geometry') {
    if (!lesion) return bad('Missing lesion selection');
    const url = caseUrl(project, patient, `/lesions/${encodeURIComponent(lesion)}/geometry`);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'GET');
  }

  if (resource === 'qc' && report) {
    const url = caseUrl(project, patient, `/mesh-qc-reports/${encodeURIComponent(report)}`);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'asset' && report) {
    const url = caseUrl(project, patient, `/mesh-qc-reports/${encodeURIComponent(report)}/asset`);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'GET');
  }
  if (resource === 'measurement' && report) {
    const url = caseUrl(project, patient, `/physical-measurements/${encodeURIComponent(report)}`);
    if (!url) return bad('Missing project or patient');
    return proxyCase(request, url, 'GET');
  }
  return bad('Unknown lesion viewer resource');
}
