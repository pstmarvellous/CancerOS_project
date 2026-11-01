import { caseParams, caseUrl, proxyCase } from '../../../lib/case-proxy';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  const { project, patient } = caseParams(request);
  const url = caseUrl(project, patient, '/observation-queries');
  if (!url) {
    return Response.json({ title: 'Missing project or patient' }, { status: 400 });
  }
  return proxyCase(request, url, 'POST', await request.text());
}
