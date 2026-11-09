import { caseParams, caseUrl, missingSelection, proxyCase } from '../../../lib/case-proxy';
import { researchSession } from '../../../lib/research-session';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  const { project, patient } = caseParams(request);
  const url = caseUrl(project, patient, '');
  if (!url) return missingSelection();
  const response = await proxyCase(request, url, 'GET');
  const session = researchSession(request);
  // Remember only a successful, backend-authorized cookie-session read.
  // Explicit bearer clients must not alter a different cookie's selection.
  if (response.ok && session && !request.headers.has('authorization')) session.lastCase = { project, patient };
  return response;
}
