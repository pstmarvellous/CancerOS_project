import { caseParams, caseUrl, missingSelection, proxyCase } from '../../../lib/case-proxy';

export const dynamic = 'force-dynamic';

function recordPath(request: Request): string | null {
  const record = new URL(request.url).searchParams.get('record');
  if (!record) return null;
  return `/observations/${encodeURIComponent(record)}`;
}

export async function GET(request: Request) {
  const { project, patient } = caseParams(request);
  const suffix = recordPath(request);
  const url = suffix ? caseUrl(project, patient, suffix) : null;
  if (!url) return missingSelection();
  return proxyCase(request, url, 'GET');
}

export async function POST(request: Request) {
  const { project, patient } = caseParams(request);
  const action = new URL(request.url).searchParams.get('action');
  const record = new URL(request.url).searchParams.get('record');
  const suffix =
    action === 'retract' && record ? `/observations/${encodeURIComponent(record)}/retractions` : null;
  const url = suffix ? caseUrl(project, patient, suffix) : null;
  if (!url) return missingSelection();
  return proxyCase(request, url, 'POST', await request.text());
}
