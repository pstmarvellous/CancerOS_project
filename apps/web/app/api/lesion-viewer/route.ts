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
    const url = caseUrl(project, patient, `/lesions/${encodeURIComponent(lesion)}`);
    if (!url) return bad('Missing project or patient');
    try {
      const headers: Record<string, string> = {};
      const authorization = request.headers.get('authorization');
      if (authorization) headers.authorization = authorization;
      const lesionResponse = await fetch(url, { headers, cache: 'no-store', signal: AbortSignal.timeout(15000) });
      const body = await lesionResponse.text();
      if (!lesionResponse.ok) {
        return new Response(body, {
          status: lesionResponse.status,
          headers: { 'content-type': 'application/json', 'Cache-Control': 'private, no-store' },
        });
      }
      const parsed = JSON.parse(body) as {
        id?: string;
        baseline_segmentation_id?: string;
        input_revision?: number;
      };
      const candidates = [
        parsed.baseline_segmentation_id,
        typeof parsed.id === 'string' ? parsed.id : null,
      ].filter((value): value is string => !!value);
      for (const candidate of candidates) {
        const qc = caseUrl(project, patient, `/mesh-qc-reports/${encodeURIComponent(candidate)}`);
        if (!qc) continue;
        try {
          const qcResponse = await fetch(qc, {
            headers,
            cache: 'no-store',
            signal: AbortSignal.timeout(15000),
          });
          const qcBody = await qcResponse.text();
          if (qcResponse.ok) {
            return new Response(qcBody, {
              status: 200,
              headers: { 'content-type': 'application/json', 'Cache-Control': 'private, no-store' },
            });
          }
        } catch {
          continue;
        }
      }
      return Response.json({ title: 'No validated geometry is linked to this lesion identity' }, { status: 409 });
    } catch {
      return Response.json({ title: 'API process unavailable' }, { status: 502 });
    }
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
