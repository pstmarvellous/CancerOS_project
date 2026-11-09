'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import type { components } from '../../../packages/contracts/generated/api';
import { ErrorSummary, LoadingState } from './research';

type S = components['schemas'];
type StudySummary = S['StudySummary'];
type Segmentation = S['SegmentationDiscovery'];
type ImportSummary = S['ImportSummary'];
type Acquisition = S['AcquisitionSummary'];
type Geometry = S['GeometryReport'];
type Job = S['ImagingJobRecord'];
type SegQC = S['SegmentationQCReport'];
type Measurement = S['MeasurementReport'];
type MeshQC = S['MeshQCReport'];

type Step = 'study' | 'provenance' | 'geometry' | 'mask' | 'qc' | 'model';

const STEPS: { id: Step; label: string }[] = [
  { id: 'study', label: 'Select study' },
  { id: 'provenance', label: 'Review source' },
  { id: 'geometry', label: 'Check geometry' },
  { id: 'mask', label: 'Select region mask' },
  { id: 'qc', label: 'View QC results' },
  { id: 'model', label: 'Open 3D model' },
];

const NO_MASK_MESSAGE =
  'This imaging study has no compatible verified region mask. A 3D tumor measurement is not yet available.';

function explain(status: number): string {
  if (status === 401) return 'Sign in with an authorized research session, then retry.';
  if (status === 403) return 'This action needs an administrator or editor role for this case. The study list stays available.';
  if (status === 404) return 'The selected study or mask is not available in this authorized case. Reselect from the current list.';
  if (status === 409) return 'The case revision or resource state changed. Reload the workflow step and retry; nothing was overwritten.';
  if (status === 422) return 'The server rejected the request. Check the selected study and mask, then retry.';
  return `The authorized request failed (status ${status}).`;
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  return text ? (JSON.parse(text) as unknown) : null;
}

async function authorized<T>(path: string, signal: AbortSignal, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { cache: 'no-store', credentials: 'same-origin', signal, ...init });
  if (!response.ok) throw new Error(explain(response.status));
  return (await readJson(response)) as T;
}

export function CaseImagingWorkflow({ project, patient }: { project: string; patient: string }) {
  const params = useSearchParams();
  const urlStudy = params.get('imaging_study');
  const urlImport = params.get('imaging_import');
  return <CaseImagingWorkflowBody key={`${project}:${patient}`} project={project} patient={patient} urlStudy={urlStudy} urlImport={urlImport} />;
}

function CaseImagingWorkflowBody({ project, patient, urlStudy, urlImport }: { project: string; patient: string; urlStudy: string | null; urlImport: string | null }) {
  const selection = `${project}:${patient}`;
  const [studies, setStudies] = useState<StudySummary[] | null>(null);
  const [imports, setImports] = useState<ImportSummary[] | null>(null);
  const [masks, setMasks] = useState<Segmentation[] | null>(null);
  const [studyId, setStudyId] = useState<string | null>(null);
  const [importId, setImportId] = useState<string | null>(null);
  const [acquisition, setAcquisition] = useState<Acquisition | null>(null);
  const [geometry, setGeometry] = useState<Geometry | null>(null);
  const [maskId, setMaskId] = useState<string | null>(null);
  const [segQc, setSegQc] = useState<SegQC | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [measurement, setMeasurement] = useState<Measurement | null>(null);
  const [meshQc, setMeshQc] = useState<MeshQC | null>(null);
  const [reload, setReload] = useState(0);
  const [step, setStep] = useState<Step>('study');
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>('loading');
  const [message, setMessage] = useState('Loading authorized studies for this case…');
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState<number | null>(null);
  const [restored, setRestored] = useState(false);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  const workflow = useCallback(
    async <T,>(resource: string, id: string | null, signal: AbortSignal, init?: RequestInit): Promise<T> => {
      const suffix = id
        ? `/api/case-imaging-workflow?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=${resource}&id=${encodeURIComponent(id)}`
        : `/api/case-imaging-workflow?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=${resource}`;
      return authorized<T>(suffix, signal, init);
    },
    [project, patient],
  );

  useEffect(() => {
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    void (async () => {
      setStatus('loading');
      setRestored(false);
      setMessage('Loading authorized studies for this case…');
      try {
        const page = await authorized<{ studies: { items: StudySummary[] }; segmentations: Segmentation[] | null }>(
          `/api/case-imaging?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`,
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setStudies(page.studies.items);
        setMasks(page.segmentations ?? null);
        const detail = await authorized<{ data_revision: number }>(
          `/api/case-detail?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`,
          controller.signal,
        ).catch(() => null);
        if (controller.signal.aborted) return;
        if (detail) setRevision(detail.data_revision);
        let importList: ImportSummary[] | null = null;
        try {
          const listed = await authorized<{ items: ImportSummary[] }>(
            `/api/case-imaging-workflow?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=imports`,
            controller.signal,
          );
          importList = listed.items;
        } catch {
          importList = null;
        }
        if (controller.signal.aborted) return;
        setImports(importList);
        setStatus('ready');
        setMessage('Select an authorized study to begin the guided import review.');
      } catch (cause) {
        if (controller.signal.aborted) return;
        setStatus('failed');
        setMessage(cause instanceof Error ? cause.message : 'The study list could not load.');
      }
    })();
    return () => controller.abort();
  }, [selection, project, patient, reload]);

  const remember = useCallback((study: string | null, imp: string | null) => {
    const url = new URL(window.location.href);
    if (study) url.searchParams.set('imaging_study', study);
    else url.searchParams.delete('imaging_study');
    if (imp) url.searchParams.set('imaging_import', imp);
    else url.searchParams.delete('imaging_import');
    window.history.replaceState(null, '', url.toString());
  }, []);

  async function loadAcquisition(nextImportId: string, forStudy?: string) {
    const controller = new AbortController();
    pending.current?.abort();
    pending.current = controller;
    setBusy(true);
    setMessage('Associated study selected. Loading source and provenance…');
    try {
      const detail = await workflow<Acquisition>('acquisition', nextImportId, controller.signal);
      if (controller.signal.aborted) return;
      const ownerStudy = forStudy ?? detail.study_id;
      setStudyId(ownerStudy);
      setImportId(detail.import_id);
      setAcquisition(detail);
      setGeometry(null);
      setMaskId(null);
      setSegQc(null);
      setMeasurement(null);
      setMeshQc(null);
      setJob(null);
      setStep('geometry');
      remember(ownerStudy, detail.import_id);
      setMessage('Associated study selected. Source and provenance are shown; geometry check is next.');
    } catch (cause) {
      if (!controller.signal.aborted) setMessage(cause instanceof Error ? cause.message : 'The acquisition could not load.');
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  useEffect(() => {
    if (restored || status !== 'ready' || !studies || !imports) return;
    void (async () => {
      if (urlStudy && studies.some((item) => item.study_id === urlStudy)) {
        const candidates = imports.filter((item) => item.study_id === urlStudy);
        const target = (urlImport && candidates.some((item) => item.import_id === urlImport) ? urlImport : candidates[0]?.import_id) ?? null;
        if (target) {
          setStudyId(urlStudy);
          setRestored(true);
          await loadAcquisition(target, urlStudy);
          return;
        }
        setStudyId(urlStudy);
        setStep('provenance');
      }
      setRestored(true);
    })();
    // One-shot URL restore after refresh; later selection flows through the pickers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [restored, status, studies, imports, urlStudy, urlImport]);

  async function selectStudy(next: StudySummary) {
    pending.current?.abort();
    setStudyId(next.study_id);
    setImportId(null);
    setAcquisition(null);
    setGeometry(null);
    setMaskId(null);
    setSegQc(null);
    setMeasurement(null);
    setMeshQc(null);
    setJob(null);
    setStep('provenance');
    remember(next.study_id, null);
    setMessage('Study selected. Choose one of its imports to review source and provenance.');
  }

  async function checkGeometry() {
    if (!importId) return;
    setMaskId(null); setSegQc(null); setMeasurement(null); setMeshQc(null);
    const controller = new AbortController();
    pending.current?.abort();
    pending.current = controller;
    setBusy(true);
    setMessage('Checking image geometry against verified spacing and units…');
    try {
      const report = await workflow<Geometry>(
        'geometry',
        null,
        controller.signal,
        { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ import_id: importId }) },
      );
      if (controller.signal.aborted) return;
      setGeometry(report);
      setStep('mask');
      setMessage(
        report.status === 'valid'
          ? 'Segmentation and measurements path is open: geometry is valid. Select a compatible region mask.'
          : 'Geometry check failed safely. Original bytes are unchanged; supply verified spatial metadata or reject this source.',
      );
    } catch (cause) {
      if (!controller.signal.aborted) setMessage(cause instanceof Error ? cause.message : 'Geometry validation failed.');
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  async function checkSegmentationQc(nextMaskId: string) {
    setMaskId(nextMaskId);
    setSegQc(null);
    setMeasurement(null);
    setMeshQc(null);
    const controller = new AbortController();
    pending.current?.abort();
    pending.current = controller;
    setBusy(true);
    setMessage('Reviewing segmentation QC for the selected mask…');
    try {
      const report = await workflow<SegQC>(
        'segqc',
        null,
        controller.signal,
        { method: 'POST', headers: { 'content-type': 'application/json', 'idempotency-key': crypto.randomUUID() }, body: JSON.stringify({ segmentation_id: nextMaskId }) },
      );
      if (controller.signal.aborted) return;
      setSegQc(report);
      setStep(report.technical.technical_status === 'pass' ? 'model' : 'qc');
      setMessage(
        report.technical.technical_status === 'pass'
          ? 'Mask technical QC passed. Calculate a deterministic region measurement next; 3D reconstruction has not run.'
          : 'Segmentation QC did not pass. Measurements stay unavailable; the source mask is unchanged.',
      );
    } catch (cause) {
      if (!controller.signal.aborted) setMessage(cause instanceof Error ? cause.message : 'Segmentation QC failed.');
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  async function pollJob(jobId: string, signal: AbortSignal) {
    for (let attempt = 0; attempt < 60; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 5000));
      if (signal.aborted) return;
      try {
        const record = await workflow<Job>('job', jobId, signal);
        if (signal.aborted) return;
        setJob(record);
        if (record.status === 'succeeded' || record.status === 'failed' || record.status === 'cancelled') {
          setMessage(
            record.status === 'succeeded'
              ? `Processing ${record.operation} completed. Inspect the report below.`
              : `Processing ${record.operation} ended with status ${record.status}. Error: ${record.error_code ?? 'see report'}.`,
          );
          return record;
        }
        setMessage(`Processing ${record.operation}: ${record.stage}. This status comes from the backend worker; no percentage is inferred.`);
      } catch {
        return;
      }
    }
    setMessage('Processing is still running. Retry the status check to refresh from the backend.');
  }

  async function enqueueJob(operation: 'preprocessing' | 'segmentation_qc', payload: Record<string, unknown>) {
    if (revision === null) {
      setMessage('The case revision is still loading. Retry once the study list is ready.');
      return;
    }
    const controller = new AbortController();
    pending.current?.abort();
    pending.current = controller;
    setBusy(true);
    setMessage(`Submitting ${operation} to the backend worker…`);
    try {
      const record = await workflow<Job>(
        'job',
        null,
        controller.signal,
        {
          method: 'POST',
          headers: { 'content-type': 'application/json', 'idempotency-key': crypto.randomUUID() },
          body: JSON.stringify({ expected_revision: revision, command: { operation, input: payload } }),
        },
      );
      if (controller.signal.aborted) return;
      setJob(record);
      setBusy(false);
      if (record.status === 'queued' || record.status === 'running') {
        setMessage(`Processing ${record.operation}: ${record.stage}. This status comes from the backend worker; no percentage is inferred.`);
        void pollJob(record.id, controller.signal);
      } else {
        setMessage(`Processing ${record.operation} ended with status ${record.status}.`);
      }
    } catch (cause) {
      if (!controller.signal.aborted) {
        setBusy(false);
        setMessage(cause instanceof Error ? cause.message : 'The processing job could not start.');
      }
    }
  }

  async function reconstruct() {
    if (!maskId || !segQc || segQc.technical.technical_status !== 'pass' || revision === null) return;
    const controller = new AbortController();
    pending.current?.abort(); pending.current = controller;
    setBusy(true); setMeshQc(null); setMeasurement(null);
    const post = <T,>(resource: string, body: unknown) => workflow<T>(resource, null, controller.signal, { method: 'POST', headers: { 'content-type': 'application/json', 'idempotency-key': crypto.randomUUID() }, body: JSON.stringify(body) });
    try {
      setMessage('Calculating physical region measurements from the selected verified mask grid…');
      const measured = await post<Measurement>('measurement', { segmentation_ids: [maskId], expected_revision: revision, definition: 'numerical_region_volume' });
      if (controller.signal.aborted) return;
      setMeasurement(measured);
      if (measured.values.availability !== 'available') throw new Error('Measurement is unavailable. Review the server eligibility and QC results.');
      async function run(operation: 'mesh' | 'mesh_qc', input: unknown) {
        const queued = await post<Job>('job', { expected_revision: revision, command: { operation, input } });
        if (controller.signal.aborted) throw new Error('Processing selection changed.');
        setJob(queued);
        const completed = queued.status === 'queued' || queued.status === 'running' ? await pollJob(queued.id, controller.signal) : queued;
        if (!completed || completed.status !== 'succeeded' || !completed.result_report_id) throw new Error('Processing has not succeeded. Inspect backend status before retrying.');
        return completed.result_report_id;
      }
      const mesh = await run('mesh', { measurement_id: measured.id });
      const qcId = await run('mesh_qc', { mesh_run_id: mesh });
      const report = await workflow<MeshQC>('meshqc', qcId, controller.signal);
      if (controller.signal.aborted) return;
      if (report.measurement_id !== measured.id) throw new Error('Mesh and measurement references do not agree.');
      setMeshQc(report); setStep('model');
      setMessage(report.status === 'validated' ? 'Deterministic measurement and QC-validated mesh are available. Open the exact reconstructed model below.' : 'Mesh QC blocked display. Source-mask measurements remain available.');
    } catch (cause) {
      if (!controller.signal.aborted) setMessage(cause instanceof Error ? cause.message : 'Reconstruction failed safely.');
    } finally { if (!controller.signal.aborted) setBusy(false); }
  }

  const studyImports = studyId && imports ? imports.filter((item) => item.study_id === studyId) : [];
  const compatibleMasks = masks?.filter(mask => mask.source_image_id === geometry?.volume_artifact_id && mask.study_id === acquisition?.study_id) ?? [];
  const selectedMask = masks && maskId ? masks.find((mask) => mask.segmentation_id === maskId) ?? null : null;

  return (
    <section className="card workspace-section" aria-label="Add imaging study workflow">
      <h2>Add Imaging Study</h2>
      <p role="status" aria-live="polite">{message}</p>
      <ol className="step-list" aria-label="Import progress">
        {STEPS.map((item, index) => (
          <li key={item.id} aria-current={step === item.id ? 'step' : undefined}>
            Step {index + 1}: {item.label}{step === item.id ? ' — current' : ''}
          </li>
        ))}
      </ol>

      {status === 'loading' ? <LoadingState /> : null}
      {status === 'failed' ? (
        <div>
          <ErrorSummary message={message} />
          <p><button type="button" className="button-ghost" onClick={() => window.location.reload()}>Retry loading studies</button></p>
        </div>
      ) : null}

      {status === 'ready' && studies ? (
        <>
          {!studies.length ? (
            <p>No imaging studies are associated with this case. Use the authorized import form below to add an eligible synthetic engineering file.</p>
          ) : (
            <fieldset disabled={busy} style={{ border: 0, padding: 0 }}>
              <legend>1. Select a supported study in this case</legend>
              <label>Study
                <select
                  aria-label="Associated study"
                  value={studyId ?? ''}
                  onChange={(event) => {
                    const next = studies.find((item) => item.study_id === event.target.value);
                    if (next) void selectStudy(next);
                  }}
                >
                  <option value="" disabled>Choose a study…</option>
                  {studies.map((item, index) => (
                    <option key={item.study_id} value={item.study_id}>
                      Study {index + 1} · {item.series_count} series · {item.import_count} imports · {item.status.replaceAll('_', ' ')}
                    </option>
                  ))}
                </select>
              </label>
              {studyId ? (
                <label>Study import
                  <select
                    aria-label="Study import"
                    value={importId ?? ''}
                    onChange={(event) => { if (event.target.value) void loadAcquisition(event.target.value, studyId); }}
                  >
                    <option value="" disabled>Choose an import…</option>
                    {studyImports.map((item) => (
                      <option key={item.import_id} value={item.import_id}>
                        {item.sequence} · {item.format} · {item.status.replaceAll('_', ' ')}
                        {item.issue_codes.length ? ` · ${item.issue_codes.length} issue(s)` : ''}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
            </fieldset>
          )}

          {acquisition ? (
            <section aria-label="Source and provenance review">
              <h3>2. Review source and provenance</h3>
              <dl className="profile-facts">
                <div><dt>Sequence</dt><dd>{studyImports.find((item) => item.import_id === acquisition.import_id)?.sequence.replaceAll('_', ' ') ?? 'Unknown'}</dd></div>
                <div><dt>Format</dt><dd>{studyImports.find((item) => item.import_id === acquisition.import_id)?.format ?? 'Unknown'}</dd></div>
                <div><dt>Frame shape</dt><dd>{acquisition.frame_shape.length ? acquisition.frame_shape.join(' × ') : 'Not established'}</dd></div>
                <div><dt>Files</dt><dd>{acquisition.file_count}</dd></div>
                <div><dt>Status</dt><dd>{acquisition.status.replaceAll('_', ' ')}</dd></div>
              </dl>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="button-primary" disabled={busy} onClick={() => void checkGeometry()}>
                  {busy ? 'Checking…' : geometry ? 'Re-check image geometry' : 'Check image geometry'}
                </button>
              </div>
            </section>
          ) : null}

          {geometry ? (
            <section aria-label="Geometry result">
              <h3>3. Image geometry</h3>
              {geometry.status === 'valid' && geometry.geometry ? (
                <dl className="profile-facts">
                  <div><dt>Grid shape</dt><dd>{geometry.geometry.shape_xyz.join(' × ')} voxels</dd></div>
                  <div><dt>Spacing</dt><dd>{geometry.geometry.spacing_mm.join(' × ')} mm</dd></div>
                  <div><dt>Frame</dt><dd>{geometry.geometry.coordinate_frame}</dd></div>
                  <div><dt>Voxel volume</dt><dd>{geometry.geometry.voxel_volume_mm3} mm³</dd></div>
                </dl>
              ) : (
                <ErrorSummary message={`Geometry is ${geometry.status}. ${(geometry.issue_codes ?? []).join(', ') || 'No further detail.'} Original bytes are unchanged.`} />
              )}
              <p className="field-hint">{geometry.next_action}</p>
            </section>
          ) : null}

          {geometry?.status === 'valid' ? (
            <section aria-label="Mask selection">
              <h3>4. Select an authorized region mask</h3>
              {!compatibleMasks.length ? (
                <div>
                  <p role="alert">{NO_MASK_MESSAGE}</p>
                  <p className="field-hint">No mask is synthesized. Ask an administrator to associate a verified mask, then reselect it here.</p>
                </div>
              ) : (
                <label>Region mask
                  <select disabled={busy} aria-label="Authorized region mask" value={maskId ?? ''} onChange={(event) => { if (event.target.value) void checkSegmentationQc(event.target.value); }}>
                    <option value="" disabled>Choose a mask…</option>
                    {compatibleMasks.map((mask, index) => (
                      <option key={mask.segmentation_id} value={mask.segmentation_id}>
                        Mask {index + 1} · {mask.mask_type.replaceAll('_', ' ')} · label {mask.label_value} · QC {mask.qc_status}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {selectedMask ? <p className="field-hint">Selected meaning: {selectedMask.mask_type.replaceAll('_', ' ')}. A technical QC pass does not establish a clinically reviewed lesion contour.</p> : null}
            </section>
          ) : null}

          <PrivateImagingInput project={project} patient={patient} geometry={geometry} acquisition={acquisition} onImported={() => { setReload(value => value + 1); }} />
          {segQc ? (
            <section aria-label="QC results">
              <h3>5. QC results</h3>
              <dl className="profile-facts">
                <div><dt>Technical status</dt><dd>{segQc.technical.technical_status}</dd></div>
                <div><dt>Foreground voxels</dt><dd>{segQc.technical.foreground_voxels ?? 'Unavailable'}</dd></div>
                <div><dt>Reference basis</dt><dd>{segQc.reference_eligibility_reason.replaceAll('_', ' ')}</dd></div>
                <div><dt>Scientific review</dt><dd>{segQc.scientific_review}</dd></div>
              </dl>
              {segQc.technical.technical_status === 'pass' ? (
                <div>
                  <p>Technical QC permits a numerical region calculation; anatomical and scientific approval remain pending.</p>
                  <button type="button" disabled={busy || revision === null} className="button-primary" onClick={() => void reconstruct()}>Calculate measurement and reconstruct 3D</button>
                </div>
              ) : (
                <p className="field-hint">3D measurement stays unavailable until QC passes. No substitute shape is displayed.</p>
              )}
              <p className="field-hint">{segQc.next_action}</p>
            </section>
          ) : null}

          {measurement ? <section aria-label="Deterministic measurement"><h3>Deterministic source-mask measurement</h3><p>Region volume: {measurement.values.volume_mm3 ?? 'Unavailable'} mm³. Origin: {measurement.origin}. Scientific review: {measurement.scientific_review}.</p><p>{measurement.next_action}</p></section> : null}
          {meshQc ? <section aria-label="Reconstructed mesh QC"><h3>3D reconstruction QC: {meshQc.status}</h3><p>{meshQc.next_action}</p>{meshQc.status === 'validated' && meshQc.output_artifact_id ? <><p><Link className="button-secondary" href={`/twin?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&mesh_qc=${meshQc.id}`}>Open 3D Model</Link></p><p><Link href={`/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&baseline_measurement=${meshQc.measurement_id}&baseline_mesh_qc=${meshQc.id}`}>Create a hypothetical branch from this synthetic engineering baseline</Link></p></> : null}</section> : null}
          {job ? (
            <section aria-label="Processing progress">
              <h3>Processing progress (backend status)</h3>
              <dl className="profile-facts">
                <div><dt>Operation</dt><dd>{job.operation}</dd></div>
                <div><dt>Stage</dt><dd>{job.stage}</dd></div>
                <div><dt>Status</dt><dd>{job.status}</dd></div>
                {job.error_code ? <div><dt>Error</dt><dd>{job.error_code}</dd></div> : null}
              </dl>
              <p className="field-hint">{job.next_action}</p>
            </section>
          ) : null}

          {acquisition && revision !== null ? (
            <details>
              <summary>Advanced processing (administrator or editor)</summary>
              <p className="field-hint">Long operations run on the backend worker. Status above always reflects the worker; nothing here simulates progress.</p>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" className="button-ghost" disabled={busy || !geometry?.volume_artifact_id} onClick={() => {
                  if (!geometry?.volume_artifact_id || !acquisition) return;
                  const sequence = studyImports.find((item) => item.import_id === acquisition.import_id)?.sequence ?? 'other_mr';
                  void enqueueJob('preprocessing', { volume_artifact_id: geometry.volume_artifact_id, config: { expected_sequence: sequence === 'unknown' ? 'other_mr' : sequence } });
                }}>Run preprocessing job</button>
                {maskId ? (
                  <button type="button" className="button-ghost" disabled={busy} onClick={() => void enqueueJob('segmentation_qc', { segmentation_id: maskId })}>Run segmentation QC job</button>
                ) : null}
              </div>
            </details>
          ) : null}
        </>
      ) : null}
      <p className="field-hint">Imaging imports remain administrator-only synthetic engineering fixtures. Source rights and identity checks execute on the backend. Authentic MRI onboarding is blocked pending verified rights, de-identification and annotation review. No masks or spacing are invented; contrast phases are not visits.</p>
    </section>
  );
}


function PrivateImagingInput({ project, patient, geometry, acquisition, onImported }: { project: string; patient: string; geometry: Geometry | null; acquisition: Acquisition | null; onImported: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [manifest, setManifest] = useState('');
  const [kind, setKind] = useState<'study' | 'mask'>('study');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('Choose an eligible registered synthetic NIfTI file and its administrator manifest. Original bytes remain unchanged.');
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  async function submit() {
    if (!file) return;
    const controller = new AbortController(); pending.current?.abort(); pending.current = controller; setBusy(true);
    try {
      if (file.size < 1 || file.size > 675000) throw new Error('This bounded uploader supports NIfTI files up to 675,000 bytes. Larger studies require the reviewed administrator ingestion path.');
      const value = JSON.parse(manifest) as Record<string, unknown>;
      if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Provide an administrator manifest object.');
      const raw = new Uint8Array(await file.arrayBuffer());
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', raw))).map(byte => byte.toString(16).padStart(2, '0')).join('');
      let binary = ''; for (const byte of raw) binary += String.fromCharCode(byte);
      const post = async <T,>(resource: string, body: unknown, id?: string): Promise<T> => authorized<T>(`/api/case-imaging-workflow?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=${resource}${id ? `&id=${encodeURIComponent(id)}` : ''}`, controller.signal, { method: 'POST', headers: { 'content-type': 'application/json', 'idempotency-key': crypto.randomUUID() }, body: JSON.stringify(body) });
      if (kind === 'mask' && (!geometry?.volume_artifact_id || !acquisition)) throw new Error('Select the target study and validate its geometry before associating a mask.');
      setMessage('Uploading original bytes to private storage; checking source rights, registered checksum and patient mapping…');
      const staged = await post<S['ImagingStageReceipt']>('file', { source_version_id: value.source_version_id, mapping_id: value.mapping_id, format: 'nifti', sha256: digest, content_base64: btoa(binary) });
      if (controller.signal.aborted) return;
      if (kind === 'study') {
        if (!value.association || typeof value.association !== 'object') throw new Error('The study manifest needs an explicit association object. The uploaded bytes remain private.');
        setMessage('Checking import integrity and the explicit case/study/series association…');
        const preview = await post<S['ImagingImportReport']>('preview', { file_ids: [staged.artifact_id], association: value.association });
        if (preview.status !== 'awaiting_confirmation') throw new Error(`Import is ${preview.status}. ${preview.issue_codes.join(', ')} Original bytes remain unchanged.`);
        await post<S['ImagingImportReport']>('confirmation', {}, preview.id);
        if (controller.signal.aborted) return;
        setMessage('Study imported and associated with this case. Select it above to validate geometry.');
      } else {
        const labels = value.labels as S['LabelDefinition'][];
        if (!Array.isArray(labels) || !labels.length) throw new Error('The mask manifest requires explicit positive labels and their meanings.');
        const target = geometry!.volume_artifact_id!;
        const study = acquisition!.study_id;
        setMessage('Checking the explicit mask/image binding and exact-grid physical alignment…');
        const binding = await post<S['MaskAssociation']>('binding', { mask_file_id: staged.artifact_id, target_image_id: target, expected_study_id: study, evidence_sha256: value.evidence_sha256 });
        const aligned = await post<S['AlignmentRun']>('alignment', { association_id: binding.id, mask_file_id: staged.artifact_id, target_image_id: target, mask_study_id: study, association_evidence_sha256: value.evidence_sha256, config: { expected_labels: labels.map(label => label.label), mode: 'exact_grid' } });
        if (aligned.status !== 'aligned_pending_review') throw new Error(`Mask alignment is ${aligned.status}: ${aligned.issue_codes.join(', ')}. No mask was repaired or substituted.`);
        await post<S['AnnotationBatch']>('annotation', { alignment_run_id: aligned.id, annotation_class: value.annotation_class, authorship: value.authorship, method_reference: value.method_reference ?? null, labels, source_annotation_evidence_sha256: value.evidence_sha256 });
        if (controller.signal.aborted) return;
        setMessage('Source mask associated and alignment checked. Select the compatible mask above and run technical QC; scientific review remains pending.');
      }
      onImported();
    } catch (cause) { if (!controller.signal.aborted) setMessage(cause instanceof SyntaxError ? 'The administrator manifest must be valid JSON.' : cause instanceof Error ? cause.message : 'Import failed safely.'); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <details><summary>Import authorized imaging or associate a source mask (administrator)</summary>
    <p>This bounded upload supports registered synthetic engineering NIfTI files only. Authentic MRI remains blocked. The backend requires existing source rights, the exact registered file checksum and a mapping to this case. DICOM ingestion remains available through the reviewed administrator API.</p>
    <fieldset disabled={busy}><legend>Review source and provenance before import</legend>
      <label>Import purpose<select aria-label="Import purpose" value={kind} onChange={event => setKind(event.target.value as 'study' | 'mask')}><option value="study">Add imaging study</option><option value="mask">Associate existing region mask</option></select></label>
      <label>NIfTI source file<input aria-label="NIfTI source file" type="file" accept=".nii,.nii.gz" onChange={event => setFile(event.target.files?.[0] ?? null)} /></label>
      <label>Administrator source manifest<textarea aria-label="Administrator source manifest" rows={8} value={manifest} onChange={event => setManifest(event.target.value)} /></label>
      <p className="field-hint">Both manifests require source_version_id and mapping_id. Study association requires mapping_id, study_id, series_id, source_study_key, source_series_key, sequence, acquisition_time_status, association_basis and evidence_sha256. Mask manifests require evidence_sha256, annotation_class, authorship and labels with explicit label/meaning values. Source identifiers stay private; no default anatomical annotation is assumed.</p>
      <button type="button" className="button-secondary" disabled={!file || !manifest.trim() || (kind === 'mask' && !geometry?.volume_artifact_id)} onClick={() => void submit()}>Review complete — submit {kind === 'study' ? 'study import' : 'source mask'}</button>
    </fieldset><p role="status" aria-live="polite">{message}</p>
  </details>;
}
