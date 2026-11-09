import { caseParams, caseUrl, missingSelection, proxyCase } from '../../../lib/case-proxy';

export const dynamic = 'force-dynamic';

const READ_RESOURCES: Record<string, (id: string) => string> = {
  acquisition: (id) => `/acquisitions/${id}`,
  geometry: (id) => `/geometry-validations/${id}`,
  job: (id) => `/imaging-jobs/${id}`,
  measurement: (id) => `/physical-measurements/${id}`,
  meshqc: (id) => `/mesh-qc-reports/${id}`,
  segqc: (id) => `/segmentation-qc-reports/${id}`,
};

const LIST_RESOURCES: Record<string, string> = {
  imports: '/imaging-imports',
};

const WRITE_RESOURCES: Record<string, string> = {
  geometry: '/geometry-validations',
  job: '/imaging-jobs',
  segqc: '/segmentation-qc-reports',
  measurement: '/physical-measurements',
  file: '/imaging-files',
  preview: '/imaging-import-previews',
  binding: '/mask-associations',
  alignment: '/mask-alignments',
  annotation: '/annotation-batches',
};

function bad(message: string, status = 400): Response {
  return Response.json({ title: message }, { status });
}

const UUID = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;

function selection(request: Request): { project: string; patient: string } | null {
  const { project, patient } = caseParams(request);
  if (!project || !patient) return null;
  if (!UUID.test(project) || !UUID.test(patient)) return null;
  const incoming = new URL(request.url);
  if ([...incoming.searchParams.keys()].some((key) => incoming.searchParams.getAll(key).length > 1)) return null;
  return { project, patient };
}

export async function GET(request: Request) {
  const selected = selection(request);
  if (!selected) return missingSelection();
  const incoming = new URL(request.url);
  const resource = incoming.searchParams.get('resource');
  const id = incoming.searchParams.get('id');
  if (!resource || (!(Object.hasOwn(READ_RESOURCES, resource)) && !(Object.hasOwn(LIST_RESOURCES, resource))) || ((Object.hasOwn(READ_RESOURCES, resource)) && !id)) return bad('Unknown imaging workflow resource');
  const suffix = Object.hasOwn(LIST_RESOURCES, resource)
    ? LIST_RESOURCES[resource]
    : READ_RESOURCES[resource](encodeURIComponent(id as string));
  const url = caseUrl(selected.project, selected.patient, suffix);
  if (!url) return missingSelection();
  return proxyCase(request, url, 'GET');
}

export async function POST(request: Request) {
  const selected = selection(request);
  if (!selected) return missingSelection();
  const incoming = new URL(request.url);
  const resource = incoming.searchParams.get('resource');
  const id = incoming.searchParams.get('id');
  if (!resource || (!(Object.hasOwn(WRITE_RESOURCES, resource)) && resource !== 'confirmation')) return bad('Unknown imaging workflow resource');
  if (resource === 'confirmation' && (!id || !UUID.test(id))) return bad('Choose an import to confirm');
  const url = caseUrl(selected.project, selected.patient, resource === 'confirmation' ? `/imaging-imports/${encodeURIComponent(id!)}/confirmations` : WRITE_RESOURCES[resource]);
  if (!url) return missingSelection();
  return proxyCase(request, url, 'POST', await request.text());
}
