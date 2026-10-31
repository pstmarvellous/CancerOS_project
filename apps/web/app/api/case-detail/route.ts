import { caseParams, caseUrl, missingSelection, proxyCase } from '../../../lib/case-proxy';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const { project, patient } = caseParams(request);
  const url = caseUrl(project, patient, '');
  if (!url) return missingSelection();
  return proxyCase(request, url, 'GET');
}
