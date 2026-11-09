import { webcrypto } from 'node:crypto';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CaseImagingWorkflow } from './case-imaging-workflow';

const query = vi.hoisted(() => ({ search: '' }));
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(query.search),
}));

const STUDIES = { studies: { items: [{ study_id: 'study-1', import_count: 1, series_count: 1, status: 'associated', next_action: 'select' }] }, segmentations: [] };
const IMPORTS = { items: [{ import_id: 'import-1', study_id: 'study-1', series_id: 'series-1', sequence: 't1', format: 'nifti', status: 'staged_pending_geometry', issue_codes: [] }] };
const ACQUISITION = { import_id: 'import-1', study_id: 'study-1', series_id: 'series-1', file_count: 1, status: 'staged_pending_geometry', frame_shape: [3, 4, 2], orientation: 'unknown' };
const GEOMETRY = { id: 'geo-1', import_id: 'import-1', source_file_ids: ['file-1'], volume_artifact_id: 'vol-1', volume_sha256: 'a'.repeat(64), geometry: { shape_xyz: [3, 4, 2], spacing_mm: ['2', '3', '4'], coordinate_frame: 'RAS', voxel_volume_mm3: '24' }, status: 'valid', issue_codes: [], next_action: 'continue' };
const SEQC = { id: 'qc-1', segmentation_id: 'seg-1', technical: { technical_status: 'pass', foreground_voxels: 2 }, reference_eligibility_reason: 'no_independent_reference', scientific_review: 'pending', next_action: 'open 3d' };

function stubFetch(handlers: Record<string, unknown>) {
  return vi.fn(async (input: unknown, init?: RequestInit) => {
    const url = String(input);
    for (const [key, body] of Object.entries(handlers)) {
      if (url.includes(key)) {
        if (init?.method === 'POST' && key === 'resource=geometry' && (body as { __fail?: boolean }).__fail) {
          return { ok: false, status: 409, text: async () => '' };
        }
        return { ok: true, text: async () => JSON.stringify(typeof body === 'function' ? body(init) : body), json: async () => body };
      }
    }
    return { ok: false, status: 404, text: async () => '' };
  });
}

afterEach(() => { vi.unstubAllGlobals(); query.search = ''; });

describe('case imaging import workflow', () => {
  it('guides study, import, geometry, mask and QC with real backend status', async () => {
    vi.stubGlobal('fetch', stubFetch({
      'case-imaging?': STUDIES,
      'case-detail?': { data_revision: 1 },
      'resource=imports': IMPORTS,
      'resource=acquisition': ACQUISITION,
      'resource=geometry': GEOMETRY,
      'resource=segqc': SEQC,
    }));
    render(<CaseImagingWorkflow project="project" patient="patient" />);
    expect(await screen.findByRole('heading', { name: 'Add Imaging Study' })).toBeVisible();
    fireEvent.change(await screen.findByLabelText('Associated study'), { target: { value: 'study-1' } });
    fireEvent.change(await screen.findByLabelText('Study import'), { target: { value: 'import-1' } });
    expect(await screen.findByText('Associated study selected. Source and provenance are shown; geometry check is next.')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Check image geometry' }));
    expect(await screen.findByText(/geometry is valid/)).toBeVisible();
    expect(screen.getByText(/This imaging study has no compatible verified region mask/)).toBeVisible();
    expect(screen.getByRole('alert')).toHaveTextContent('A 3D tumor measurement is not yet available.');
    expect(screen.getByRole('button', { name: 'Re-check image geometry' })).toBeVisible();
  });

  it('shows QC pass and opens the 3D model link when a mask exists', async () => {
    const masks = [{ segmentation_id: 'seg-1', batch_id: 'batch-1', source_image_id: 'vol-1', study_id: 'study-1', label_value: 1, mask_type: 'anatomical_tumor_contour', qc_status: 'pending', next_action: 'select' }];
    vi.stubGlobal('fetch', stubFetch({
      'case-imaging?': { studies: STUDIES.studies, segmentations: masks },
      'case-detail?': { data_revision: 1 },
      'resource=imports': IMPORTS,
      'resource=acquisition': ACQUISITION,
      'resource=geometry': GEOMETRY,
      'resource=segqc': SEQC,
      'resource=measurement': { id: 'measure-1', values: { availability: 'available', volume_mm3: '24' }, origin: 'SYNTHETIC_GENERATED', scientific_review: 'pending' },
      'resource=job': (init: RequestInit) => ({ id: 'job-1', status: 'succeeded', result_report_id: JSON.parse(String(init.body)).command.operation === 'mesh' ? 'mesh-1' : 'qc-1' }),
      'resource=meshqc': { id: 'qc-1', measurement_id: 'measure-1', status: 'validated', output_artifact_id: 'asset-1' },
    }));
    render(<CaseImagingWorkflow project="project" patient="patient" />);
    fireEvent.change(await screen.findByLabelText('Associated study'), { target: { value: 'study-1' } });
    fireEvent.change(await screen.findByLabelText('Study import'), { target: { value: 'import-1' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Check image geometry' }));
    fireEvent.change(await screen.findByLabelText('Authorized region mask'), { target: { value: 'seg-1' } });
    expect(await screen.findByText(/Mask technical QC passed/)).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Open 3D Model' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Calculate measurement and reconstruct 3D' }));
    expect(await screen.findByRole('link', { name: 'Open 3D Model' })).toHaveAttribute('href', '/twin?project=project&patient=patient&mesh_qc=qc-1');
    expect(screen.getByText(/Region volume: 24 mm/)).toBeVisible();
  });

  it('fails geometry safely without touching original bytes', async () => {
    vi.stubGlobal('fetch', stubFetch({
      'case-imaging?': STUDIES,
      'case-detail?': { data_revision: 1 },
      'resource=imports': IMPORTS,
      'resource=acquisition': ACQUISITION,
      'resource=geometry': { __fail: true },
    }));
    render(<CaseImagingWorkflow project="project" patient="patient" />);
    fireEvent.change(await screen.findByLabelText('Associated study'), { target: { value: 'study-1' } });
    fireEvent.change(await screen.findByLabelText('Study import'), { target: { value: 'import-1' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Check image geometry' }));
    await waitFor(() => expect(screen.getByText(/Geometry validation failed|revision or resource state changed/)).toBeVisible());
    expect(screen.queryByLabelText('Authorized region mask')).toBeNull();
  });

  it('denies cross-case access with scoped fetches only', async () => {
    const fetch = stubFetch({
      'case-imaging?': STUDIES,
      'case-detail?': { data_revision: 1 },
      'resource=imports': IMPORTS,
    });
    vi.stubGlobal('fetch', fetch);
    const { rerender } = render(<CaseImagingWorkflow project="project" patient="first" />);
    await screen.findByRole('heading', { name: 'Add Imaging Study' });
    const before = fetch.mock.calls.length;
    rerender(<CaseImagingWorkflow project="project" patient="second" />);
    await waitFor(() => {
      const fresh = fetch.mock.calls.slice(before).map((call) => String(call[0]));
      expect(fresh.length).toBeGreaterThan(0);
      expect(fresh.some((url) => url.includes('patient=second'))).toBe(true);
      expect(fresh.every((url) => !url.includes('patient=first'))).toBe(true);
    });
  });

  it('explains denied writes without changing the case', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: unknown) => {
      const url = String(input);
      if (url.includes('case-imaging?')) return { ok: true, text: async () => JSON.stringify(STUDIES), json: async () => STUDIES };
      if (url.includes('case-detail?')) return { ok: true, text: async () => JSON.stringify({ data_revision: 1 }) };
      if (url.includes('resource=imports')) return { ok: true, text: async () => JSON.stringify(IMPORTS) };
      if (url.includes('resource=acquisition')) return { ok: true, text: async () => JSON.stringify(ACQUISITION) };
      return { ok: false, status: 403, text: async () => '' };
    }));
    render(<CaseImagingWorkflow project="project" patient="patient" />);
    fireEvent.change(await screen.findByLabelText('Associated study'), { target: { value: 'study-1' } });
    fireEvent.change(await screen.findByLabelText('Study import'), { target: { value: 'import-1' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Check image geometry' }));
    expect(await screen.findByText(/administrator or editor role/)).toBeVisible();
  });
  it('offers only masks bound to the selected study and exact volume', async () => {
    vi.stubGlobal('fetch', stubFetch({
      'case-imaging?': { studies: STUDIES.studies, segmentations: [
        { segmentation_id: 'wrong-study', study_id: 'other-study', source_image_id: 'vol-1', mask_type: 'unknown', label_value: 1, qc_status: 'pass' },
        { segmentation_id: 'wrong-volume', study_id: 'study-1', source_image_id: 'other-volume', mask_type: 'unknown', label_value: 1, qc_status: 'pass' },
      ] },
      'case-detail?': { data_revision: 1 }, 'resource=imports': IMPORTS,
      'resource=acquisition': ACQUISITION, 'resource=geometry': GEOMETRY,
    }));
    render(<CaseImagingWorkflow project="project" patient="patient" />);
    fireEvent.change(await screen.findByLabelText('Associated study'), { target: { value: 'study-1' } });
    fireEvent.change(await screen.findByLabelText('Study import'), { target: { value: 'import-1' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Check image geometry' }));
    expect(await screen.findByText(/This imaging study has no compatible verified region mask/)).toBeVisible();
    expect(screen.queryByLabelText('Authorized region mask')).toBeNull();
  });

  it('clears prior case study, geometry and QC on case changes', async () => {
    vi.stubGlobal('fetch', stubFetch({ 'case-imaging?': STUDIES, 'case-detail?': { data_revision: 1 }, 'resource=imports': IMPORTS, 'resource=acquisition': ACQUISITION, 'resource=geometry': GEOMETRY }));
    const { rerender } = render(<CaseImagingWorkflow project="project" patient="first" />);
    fireEvent.change(await screen.findByLabelText('Associated study'), { target: { value: 'study-1' } });
    fireEvent.change(await screen.findByLabelText('Study import'), { target: { value: 'import-1' } });
    fireEvent.click(await screen.findByRole('button', { name: 'Check image geometry' }));
    await screen.findByText(/Grid shape/);
    rerender(<CaseImagingWorkflow project="project" patient="second" />);
    await screen.findByLabelText('Associated study');
    expect(screen.queryByText('Grid shape')).toBeNull();
    expect(screen.queryByRole('heading', { name: '2. Review source and provenance' })).toBeNull();
  });

  it('stages original registered bytes and explicitly confirms the case association', async () => {
    let confirmed = false;
    const fetch = stubFetch({ 'case-imaging?': () => confirmed ? STUDIES : { studies: { items: [] }, segmentations: [] }, 'case-detail?': { data_revision: 1 }, 'resource=imports': () => confirmed ? IMPORTS : { items: [] }, 'resource=file': { artifact_id: 'staged-1' }, 'resource=preview': { id: '00000000-0000-4000-8000-000000000003', status: 'awaiting_confirmation', issue_codes: [] }, 'resource=confirmation': () => { confirmed = true; return { status: 'staged_pending_geometry' }; } });
    vi.stubGlobal('fetch', fetch); vi.stubGlobal('crypto', webcrypto);
    render(<CaseImagingWorkflow project="project" patient="patient" />);
    await screen.findByText(/No imaging studies are associated with this case/);
    fireEvent.click(screen.getByText('Import authorized imaging or associate a source mask (administrator)'));
    const bytes = new TextEncoder().encode('unchanged fixture bytes');
    const file = new File([bytes], 'synthetic.nii', { type: 'application/octet-stream' });
    Object.defineProperty(file, 'arrayBuffer', { value: async () => bytes.buffer });
    fireEvent.change(screen.getByLabelText('NIfTI source file'), { target: { files: [file] } });
    const association = { mapping_id: 'mapping-1', study_id: 'study-1', series_id: 'series-1', source_study_key: 'private-study', source_series_key: 'private-series', sequence: 't1', acquisition_time_status: 'not_recorded', association_basis: 'administrator_manifest_attestation', evidence_sha256: 'a'.repeat(64) };
    fireEvent.change(screen.getByLabelText('Administrator source manifest'), { target: { value: JSON.stringify({ source_version_id: 'source-1', mapping_id: 'mapping-1', association }) } });
    fireEvent.click(screen.getByRole('button', { name: 'Review complete — submit study import' }));
    await waitFor(() => expect(fetch.mock.calls.some(call => String(call[0]).includes('resource=confirmation'))).toBe(true));
    await screen.findByLabelText('Associated study');
    const stages = fetch.mock.calls.filter(call => String(call[0]).includes('resource=file'));
    expect(stages).toHaveLength(1);
    const staged = JSON.parse(String(stages[0][1]?.body));
    expect(atob(staged.content_base64)).toBe('unchanged fixture bytes');
    expect(staged.source_version_id).toBe('source-1'); expect(staged.mapping_id).toBe('mapping-1');
    expect(staged.sha256).toMatch(/^[a-f0-9]{64}$/);
    const preview = fetch.mock.calls.find(call => String(call[0]).includes('resource=preview'))!;
    expect(JSON.parse(String(preview[1]?.body))).toEqual({ file_ids: ['staged-1'], association });
  });

  it('blocks files outside the bounded upload before sending bytes', async () => {
    const fetch = stubFetch({ 'case-imaging?': STUDIES, 'case-detail?': { data_revision: 1 }, 'resource=imports': IMPORTS });
    vi.stubGlobal('fetch', fetch);
    render(<CaseImagingWorkflow project="project" patient="patient" />);
    await screen.findByLabelText('Associated study');
    fireEvent.click(screen.getByText('Import authorized imaging or associate a source mask (administrator)'));
    const file = new File([new Uint8Array(675001)], 'too-large.nii');
    fireEvent.change(screen.getByLabelText('NIfTI source file'), { target: { files: [file] } });
    fireEvent.change(screen.getByLabelText('Administrator source manifest'), { target: { value: '{}' } });
    fireEvent.click(screen.getByRole('button', { name: 'Review complete — submit study import' }));
    expect(await screen.findByText(/up to 675,000 bytes/)).toBeVisible();
    expect(fetch.mock.calls.every(call => call[1]?.method !== 'POST')).toBe(true);
  });

  it('associates an existing mask through explicit exact-grid alignment and declared annotation meaning', async () => {
    const fetch = stubFetch({ 'case-imaging?': STUDIES, 'case-detail?': { data_revision: 1 }, 'resource=imports': IMPORTS, 'resource=acquisition': ACQUISITION, 'resource=geometry': GEOMETRY, 'resource=file': { artifact_id: 'mask-file' }, 'resource=binding': { id: 'binding-1' }, 'resource=alignment': { id: 'alignment-1', status: 'aligned_pending_review', issue_codes: [] }, 'resource=annotation': { segmentation_ids: ['seg-1'] } });
    vi.stubGlobal('fetch', fetch); vi.stubGlobal('crypto', webcrypto);
    query.search = '?imaging_study=study-1&imaging_import=import-1';
    render(<CaseImagingWorkflow project="project" patient="patient" />);
    fireEvent.click(await screen.findByRole('button', { name: 'Check image geometry' }));
    await screen.findByText(/Grid shape/);
    fireEvent.click(screen.getByText('Import authorized imaging or associate a source mask (administrator)'));
    fireEvent.change(screen.getByLabelText('Import purpose'), { target: { value: 'mask' } });
    const bytes = new Uint8Array([1, 2, 3]); const file = new File([bytes], 'mask.nii');
    Object.defineProperty(file, 'arrayBuffer', { value: async () => bytes.buffer });
    fireEvent.change(screen.getByLabelText('NIfTI source file'), { target: { files: [file] } });
    fireEvent.change(screen.getByLabelText('Administrator source manifest'), { target: { value: JSON.stringify({ source_version_id: 'mask-source', mapping_id: 'mapping-1', evidence_sha256: 'b'.repeat(64), annotation_class: 'functional_enhancement_region', authorship: 'unknown', labels: [{ label: 1, meaning: 'functional_region' }] }) } });
    fireEvent.click(screen.getByRole('button', { name: 'Review complete — submit source mask' }));
    await waitFor(() => expect(fetch.mock.calls.some(call => String(call[0]).includes('resource=annotation'))).toBe(true));
    const body = (resource: string) => JSON.parse(String(fetch.mock.calls.find(call => String(call[0]).includes(`resource=${resource}`))![1]?.body));
    expect(body('binding')).toEqual({ mask_file_id: 'mask-file', target_image_id: 'vol-1', expected_study_id: 'study-1', evidence_sha256: 'b'.repeat(64) });
    expect(body('alignment').config).toEqual({ expected_labels: [1], mode: 'exact_grid' });
    expect(body('annotation').annotation_class).toBe('functional_enhancement_region');
    expect(body('annotation').labels).toEqual([{ label: 1, meaning: 'functional_region' }]);
    expect(await screen.findByRole('button', { name: 'Check image geometry' })).toBeVisible();
  });

});
