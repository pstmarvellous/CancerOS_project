import { caseParams, caseUrl, missingSelection, proxyCase } from '../../../lib/case-proxy';

export const dynamic = 'force-dynamic';

export async function POST(request: Request) {
  const { project, patient } = caseParams(request);
  const action = new URL(request.url).searchParams.get('action');
  const suffix =
    action === 'validate' ? '/observation-batches/validations' : '/observation-batches';
  const url = caseUrl(project, patient, suffix);
  if (!url) return missingSelection();
  return proxyCase(request, url, 'POST', await request.text());
}
