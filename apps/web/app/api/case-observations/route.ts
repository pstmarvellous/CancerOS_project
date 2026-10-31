import { caseParams, caseUrl, missingSelection, proxyCase } from '../../../lib/case-proxy';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  const { project, patient } = caseParams(request);
  const url = caseUrl(project, patient, '/observation-queries');
  if (!url) return missingSelection();
  return proxyCase(request, url, 'POST', await request.text());
}
