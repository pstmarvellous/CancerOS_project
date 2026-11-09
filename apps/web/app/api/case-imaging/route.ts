import { NextResponse } from 'next/server';
import type { components } from '../../../../../packages/contracts/generated/api';
import { researchProxy } from '../../../lib/research-proxy';

export const dynamic = 'force-dynamic';
type StudyPage = components['schemas']['StudyPage'];
type Segmentation = components['schemas']['SegmentationDiscovery'];
const headers = { 'Cache-Control': 'private, no-store' };

function studies(value: unknown): StudyPage | null {
  const items = (value as { items?: unknown } | null)?.items;
  if (!Array.isArray(items)) return null;
  const selected = [];
  for (const item of items) {
    if (!item || typeof item.study_id !== 'string' || typeof item.status !== 'string' ||
      !Number.isSafeInteger(item.import_count) || item.import_count < 0 ||
      !Number.isSafeInteger(item.series_count) || item.series_count < 0 || typeof item.next_action !== 'string') return null;
    selected.push({ study_id: item.study_id, import_count: item.import_count,
      series_count: item.series_count, status: item.status, next_action: item.next_action });
  }
  return { items: selected };
}

function segmentations(value: unknown): Segmentation[] | null {
  if (!Array.isArray(value)) return null;
  const selected = [];
  for (const item of value) {
    if (!item || typeof item.segmentation_id !== 'string' || typeof item.batch_id !== 'string' ||
      !Number.isSafeInteger(item.label_value) || item.label_value < 0 || typeof item.mask_type !== 'string' ||
      typeof item.source_image_id !== 'string' || typeof item.study_id !== 'string' ||
      typeof item.qc_status !== 'string' || typeof item.next_action !== 'string') return null;
    selected.push({ segmentation_id: item.segmentation_id, batch_id: item.batch_id,
      source_image_id: item.source_image_id, study_id: item.study_id,
      label_value: item.label_value, mask_type: item.mask_type, qc_status: item.qc_status, next_action: item.next_action });
  }
  return selected;
}

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  if ([...params.keys()].some(key => !['project', 'patient'].includes(key))) {
    return NextResponse.json({ title: 'Choose a research project and case.' }, { status: 400, headers });
  }
  // Existing proxy and API retain session, project and patient authorization.
  const studyResponse = await researchProxy(request, 'studies', true);
  if (!studyResponse.ok) return studyResponse;
  try {
    const page = studies(await studyResponse.json());
    if (!page) throw new Error('Invalid discovery response');
    if (!page.items.length) return NextResponse.json({ studies: page, segmentations: null }, { headers });
    const segmentationResponse = await researchProxy(request, 'segmentation-discoveries', true);
    // This endpoint uses 404 for no accessible masks as well as hidden resources.
    // Keep that uncertainty explicit; never turn it into proof of zero masks.
    if (segmentationResponse.status === 404) return NextResponse.json({ studies: page, segmentations: null }, { headers });
    if (!segmentationResponse.ok) return segmentationResponse;
    const masks = segmentations(await segmentationResponse.json());
    if (!masks) throw new Error('Invalid discovery response');
    return NextResponse.json({ studies: page, segmentations: masks }, { headers });
  } catch {
    return NextResponse.json({ title: 'Imaging discovery is temporarily unavailable. Your saved case remains available.' }, { status: 502, headers });
  }
}
