'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { Suspense, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import type { MeasurementReport, MeshAsset, MeshQCReport } from './mesh-types';
import { ErrorSummary, LoadingState } from './research';
import styles from './mesh-preview.module.css';

const Renderer = dynamic(() => import('./mesh-renderer'), {
  ssr: false,
  loading: () => <p role="status">Loading geometry renderer…</p>,
});

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

type LesionListItem = { lesion_id: string };
type LoadError = { status: number; message: string };

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  return text ? (JSON.parse(text) as unknown) : null;
}

function explain(status: number): string {
  if (status === 401) return 'Sign in with an authorized session, then retry. A viewer cannot bypass project rights.';
  if (status === 403) return 'This case or geometry is restricted for your role. Ask an administrator for access.';
  if (status === 404) return 'The selected lesion or geometry is unavailable in this authorized case. Check the selection.';
  if (status === 409) return 'Current QC or source permission blocks display. Keep the source-mask measurement and inspect QC.';
  return `The authorized read failed (status ${status}).`;
}

type Loaded = {
  lesionId: string;
  report: MeshQCReport;
  asset: MeshAsset;
  measurement: MeasurementReport;
};

function initialSelection(params: URLSearchParams): { project: string | null; patient: string | null; lesion: string | null } {
  return { project: params.get('project'), patient: params.get('patient'), lesion: params.get('lesion') };
}

export function LesionViewer({ project: overrideProject, patient: overridePatient }: { project?: string | null; patient?: string | null } = {}) {
  return <Suspense fallback={<LoadingState/>}><LesionViewerFromQuery overrideProject={overrideProject} overridePatient={overridePatient} /></Suspense>;
}

function LesionViewerFromQuery({ overrideProject, overridePatient }: { overrideProject?: string | null; overridePatient?: string | null }) {
  const params = useSearchParams();
  const initial = initialSelection(params);
  return <LesionViewerBody key={[overrideProject ?? initial.project, overridePatient ?? initial.patient, initial.lesion, params.get('mesh_qc')].join('/')} initialProject={overrideProject ?? initial.project} initialPatient={overridePatient ?? initial.patient} initialLesion={initial.lesion} initialReport={params.get('mesh_qc')} />;
}

function LesionViewerBody({ initialProject, initialPatient, initialLesion, initialReport }: { initialProject: string | null; initialPatient: string | null; initialLesion: string | null; initialReport: string | null }) {
  const project = initialProject;
  const patient = initialPatient;
  const [lesions, setLesions] = useState<LesionListItem[] | null>(null);
  const [lesion, setLesion] = useState<string | null>(initialLesion);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [blockedMeasurement, setBlockedMeasurement] = useState<MeasurementReport | null>(null);
  const [selected, setSelected] = useState('');
  const [status, setStatus] = useState<'needs-selection' | 'loading-lesions' | 'loading' | 'ready' | 'failed'>(
    'needs-selection',
  );
  const [message, setMessage] = useState('Source region, origin and imaging time stay visible while the viewport loads.');
  const [failed3D, setFailed3D] = useState(false);
  const [retry, setRetry] = useState(0);
  const [measuresOpen, setMeasuresOpen] = useState(true);
  const [viewerOpen, setViewerOpen] = useState(true);
  const [transfer, setTransfer] = useState<{ bytes: number; started: number } | null>(null);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => {
    if (project && patient) {
      if (initialReport && UUID.test(initialReport)) {
        const controller = new AbortController();
        pending.current = controller;
        void loadGeometry(project, patient, '', controller, initialReport);
      } else void loadLesions(project, patient, lesion ?? initialLesion);
    }
    // Initial URL binding runs once; later selection changes use the lesion picker.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function authorized<T>(path: string, signal: AbortSignal): Promise<T> {
    const response = await fetch(path, { cache: 'no-store', signal });
    if (!response.ok) {
      const error = new Error(explain(response.status)) as Error & { status: number };
      error.status = response.status;
      throw error;
    }
    return (await readJson(response)) as T;
  }

  function lesionItems(body: unknown): LesionListItem[] {
    if (Array.isArray(body)) {
      return body
        .map(item => (item as { id?: unknown }).id)
        .filter((id): id is string => typeof id === 'string' && UUID.test(id))
        .map(id => ({ lesion_id: id }));
    }
    if (body && typeof body === 'object' && Array.isArray((body as { items?: unknown }).items)) {
      return ((body as { items: { lesion_id?: unknown }[] }).items ?? [])
        .map(item => item.lesion_id)
        .filter((id): id is string => typeof id === 'string' && UUID.test(id))
        .map(id => ({ lesion_id: id }));
    }
    return [];
  }

  async function loadLesions(nextProject: string, nextPatient: string, nextLesion: string | null) {
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setStatus('loading-lesions');
    try {
      const body = await authorized<unknown>(
        `/api/lesion-viewer?project=${encodeURIComponent(nextProject)}&patient=${encodeURIComponent(nextPatient)}&resource=lesions`,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      const items = lesionItems(body);
      setLesions(items);
      if (!items.length) {
        setStatus('ready');
        setLoaded(null);
        setBlockedMeasurement(null);
        setMessage('This case has no 3D model yet. Add an imaging study to continue.');
        return;
      }
      const target = nextLesion && UUID.test(nextLesion) ? nextLesion : items[0].lesion_id;
      setLesion(previous => previous ?? target);
      await loadGeometry(nextProject, nextPatient, target, controller);
    } catch (error) {
      if (controller.signal.aborted) return;
      const detail = error as LoadError & Error;
      setStatus('failed');
      setMessage(error instanceof Error ? error.message : 'The lesion list could not load.');
      void detail;
    }
  }

  async function loadGeometry(nextProject: string, nextPatient: string, lesionId: string, controller: AbortController, reportId?: string) {
    setStatus('loading');
    setLoaded(null);
    setBlockedMeasurement(null);
    setFailed3D(false);
    setMessage('Loading authorized QC, geometry and source-mask measurements…');
    const started = performance.now();
    try {
      const report = await authorized<MeshQCReport>(
        `/api/lesion-viewer?project=${encodeURIComponent(nextProject)}&patient=${encodeURIComponent(nextPatient)}${reportId ? `&resource=qc&report=${encodeURIComponent(reportId)}` : `&resource=geometry&lesion=${encodeURIComponent(lesionId)}`}`,
        controller.signal,
      );
      if (controller.signal.aborted) return;
      if (report.status !== 'validated' || !report.output_artifact_id) {
        const measurement = await authorized<MeasurementReport>(
          `/api/lesion-viewer?project=${encodeURIComponent(nextProject)}&patient=${encodeURIComponent(nextPatient)}&resource=measurement&report=${encodeURIComponent(report.measurement_id)}`,
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setBlockedMeasurement(measurement);
        setStatus('ready');
        setMessage('3D display is blocked by mesh QC. Source-mask measurements remain authoritative; inspect the mesh QC report before retrying.');
        return;
      }
      const [asset, measurement] = await Promise.all([
        authorized<MeshAsset>(
          `/api/lesion-viewer?project=${encodeURIComponent(nextProject)}&patient=${encodeURIComponent(nextPatient)}&resource=asset&report=${encodeURIComponent(report.id)}`,
          controller.signal,
        ),
        authorized<MeasurementReport>(
          `/api/lesion-viewer?project=${encodeURIComponent(nextProject)}&patient=${encodeURIComponent(nextPatient)}&resource=measurement&report=${encodeURIComponent(report.measurement_id)}`,
          controller.signal,
        ),
      ]);
      if (controller.signal.aborted) return;
      if (
        asset.format !== 'canceros-mesh-json/1' ||
        !Array.isArray(asset.objects) ||
        asset.objects.length === 0 ||
        measurement.id !== report.measurement_id ||
        measurement.input_revision !== report.input_revision
      ) {
        throw new Error('Geometry and measurement references do not agree. Inspect the source report.');
      }
      setLoaded({ lesionId, report, asset, measurement });
      setSelected(asset.objects[0].segmentation_id);
      setStatus('ready');
      setTransfer({ bytes: report.selected_byte_size ?? 0, started });
      const elapsed = ((performance.now() - started) / 1000).toFixed(1);
      setMessage(
        `Authorized geometry ready in ${elapsed}s · transfer ${Math.round((report.selected_byte_size ?? 0) / 1024)} KiB · budget ${report.budget_met ? 'met' : 'exceeded; validated detail retained'}. Source-mask measurements are authoritative.`,
      );
    } catch (error) {
      if (controller.signal.aborted) return;
      setStatus('failed');
      setMessage(error instanceof Error ? error.message : 'Unable to load this geometry. Retry the authorized read.');
    }
  }

  function switchLesion(next: string) {
    if (!project || !patient || !UUID.test(next) || next === lesion) return;
    setLesion(next);
    setSelected('');
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    void loadGeometry(project, patient, next, controller);
  }

  if (!project || !patient) {
    return (
      <section className="card">
        <h2>Open a case to inspect its source region</h2>
        <p>
          The viewer binds to the active case selection. <Link href="/cases">Open an authorized case</Link>, then
          open its Imaging & 3D tab. The browser never guesses a project or patient, and no UUID entry is needed.
        </p>
      </section>
    );
  }

  const object = loaded?.asset.objects.find(item => item.segmentation_id === selected);
  const qc = loaded?.report.objects.find(item => item.segmentation_id === selected);
  const elapsed = transfer ? (performance.now() - transfer.started) / 1000 : null;

  return (
    <div className={styles.preview}>
      <p role="status" aria-live="polite">
        {message}
      </p>
      {project && patient ? (
        <p>
          Case: {patient.slice(0, 8)}… · {initialReport ? `Geometry report: ${initialReport.slice(0, 8)}…` : `Lesion: ${lesion ? `${lesion.slice(0, 8)}…` : 'select below'}`} ·{' '}
          <Link
            href={`/cases/detail?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&tab=overview`}
          >
            Back to case workspace
          </Link>
        </p>
      ) : null}
      {status === 'loading' || status === 'loading-lesions' ? <LoadingState /> : null}
      {status === 'failed' && !loaded && !blockedMeasurement ? (
        <section className="card">
          <ErrorSummary message={message} />
          <p>
            No UUID entry is needed: reopen this case from the{' '}
            <Link href={project ? `/cases?project=${encodeURIComponent(project)}` : '/cases'}>case library</Link>{' '}
            and return to its Imaging & 3D tab. If imaging is genuinely absent, the source-mask measurement below
            stays authoritative.
          </p>
          <p>
            <button
              type="button"
              onClick={() => {
                if (project && patient) {
                  setStatus('loading-lesions');
                  if (initialReport && UUID.test(initialReport)) {
                    const controller = new AbortController(); pending.current?.abort(); pending.current = controller;
                    void loadGeometry(project, patient, '', controller, initialReport);
                  } else void loadLesions(project, patient, lesion);
                }
              }}
            >
              Retry authorized load
            </button>
          </p>
        </section>
      ) : null}
      {lesions && lesions.length > 1 ? (
        <p>
          <label htmlFor="lesion-picker">Lesion in this case </label>
          <select id="lesion-picker" value={lesion ?? ''} onChange={event => switchLesion(event.target.value)} aria-label="Lesion in this case">
            {lesions.map((item, index) => (
              <option key={item.lesion_id} value={item.lesion_id}>
                Lesion {index + 1} · {item.lesion_id.slice(0, 8)}…
              </option>
            ))}
          </select>
          <span className="field-hint"> Authorized lesions only; the list comes from the case, not manual entry.</span>
        </p>
      ) : null}
      {blockedMeasurement ? (
        <div className={styles.notice}>
          <h2>Source-mask measurement</h2>
          <p>3D geometry is unavailable for this selection. No substitute shape is displayed.</p>
          <p>
            <strong>Mask volume: {blockedMeasurement.values.volume_mm3 ?? 'Unavailable'} mm³</strong>{' '}
            ({blockedMeasurement.values.volume_cm3 ?? 'Unavailable'} cm³). Centroid, RAS:{' '}
            {blockedMeasurement.values.centroid_ras_mm?.join(', ') ?? 'Unavailable'} mm. Origin:{' '}
            {blockedMeasurement.origin}. Scientific review: pending.
          </p>
        </div>
      ) : null}
      {loaded ? (
        <section aria-label="Authorized source-region geometry" className={styles.twinGrid}>
      <div className={styles.twinSide}>
          <div className={styles.controls} role="toolbar" aria-label="Viewer panels" style={{marginBottom:12}}>
            <button type="button" aria-pressed={viewerOpen} onClick={() => setViewerOpen(open => !open)}>{viewerOpen ? 'Collapse 3D viewer' : 'Show 3D viewer'}</button>
            <button type="button" aria-pressed={measuresOpen} onClick={() => setMeasuresOpen(open => !open)}>{measuresOpen ? 'Collapse measurements' : 'Show measurements'}</button>
          </div>
          <div className={styles.measureBadge} role="status" aria-label="Server measurement">
            <strong>
              Server measurement {loaded.measurement.values.volume_mm3 ?? qc?.mask_volume_mm3 ?? 'Unavailable'} mm³
            </strong>{' '}
            <span>
              server mask measurement · origin {loaded.measurement.origin} ·{' '}
              {loaded.measurement.source_time_basis === 'not_recorded' ? 'time not recorded' : 'source time private'}
            </span>
          </div>
          <div className={styles.notice}>
            <strong>Research geometry · origin {loaded.measurement.origin}</strong>
            <p>
              No eligible patient-specific breast anatomy is available. Context is omitted; this region view cannot
              establish anatomical placement, invasion, distances or surgery.
            </p>
          </div>
          <p>
            <strong>Observation time:</strong>{' '}
            {loaded.measurement.source_time_basis === 'not_recorded'
              ? 'Not recorded'
              : 'Source time is private; actual date is not exposed'}
            . No follow-up time is inferred.
          </p>
          <label className={styles.selector}>
            Selected annotation
            <select value={selected} onChange={event => setSelected(event.target.value)}>
              {loaded.asset.objects.map(item => (
                <option key={item.segmentation_id} value={item.segmentation_id}>
                  Label {item.label} · {item.annotation_class.replaceAll('_', ' ')} · {item.segmentation_id.slice(0, 8)}
                </option>
              ))}
            </select>
          </label>
          {object ? (
            <p>
              <strong>Annotation class:</strong> {object.annotation_class.replaceAll('_', ' ')} · label {object.label}.
              Region geometry does not establish an anatomical tumor. Physical frame: RAS; units: mm.
            </p>
          ) : null}
          {!failed3D && viewerOpen ? (
            <Renderer
              key={`${loaded.lesionId}-${retry}`}
              asset={loaded.asset}
              selected={selected}
              onFailure={() => setFailed3D(true)}
            />
          ) : !viewerOpen ? (
            <div className={styles.notice}><strong>3D viewer collapsed.</strong><p>Measurements stay available. Expand the viewer above to inspect geometry.</p></div>
          ) : (
            <div className={styles.notice} role="alert">
              <strong>3D is unavailable on this device or the graphics context was lost.</strong>
              <p>Use the measurement table below. No substitute region is displayed. This fallback is not interactive release evidence.</p>
              <button type="button" onClick={() => { setFailed3D(false); setRetry(value => value + 1); }}>
                Retry 3D
              </button>
            </div>
          )}
          </div>
          {measuresOpen ? <div className={styles.twinSide}>
          <div className={styles.tableWrap}>
            <table>
              <caption>Server measurements and physical geometry · source mask is authoritative</caption>
              <thead>
                <tr>
                  <th scope="col">Quantity</th>
                  <th scope="col">Value</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row">Selected label mask volume</th>
                  <td>{qc?.mask_volume_mm3 ?? 'Unavailable'} mm³</td>
                </tr>
                <tr>
                  <th scope="row">Explicit selected-label union mask volume</th>
                  <td>
                    {loaded.measurement.values.volume_mm3 ?? 'Unavailable'} mm³ (
                    {loaded.measurement.values.volume_cm3 ?? 'Unavailable'} cm³)
                  </td>
                </tr>
                <tr>
                  <th scope="row">Union mask centroid, RAS</th>
                  <td>{loaded.measurement.values.centroid_ras_mm?.join(', ') ?? 'Unavailable'} mm</td>
                </tr>
                <tr>
                  <th scope="row">Selected surface bounds, RAS</th>
                  <td>
                    {object?.surface.bounds_min_mm.join(', ')} to {object?.surface.bounds_max_mm.join(', ')} mm
                  </td>
                </tr>
                <tr>
                  <th scope="row">Input revision</th>
                  <td>{loaded.report.input_revision}</td>
                </tr>
                {elapsed !== null && transfer ? (
                  <tr>
                    <th scope="row">Transfer and first usable mesh</th>
                    <td>
                      {Math.round(transfer.bytes / 1024)} KiB · {elapsed.toFixed(1)}s on this device and network
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
          <details>
            <summary>Geometry and QC details</summary>
            <p>
              Selected format: {loaded.asset.format}. Transfer: {loaded.report.selected_byte_size} bytes. Triangles:{' '}
              {loaded.report.selected_triangles}. Budget: {loaded.report.budget_met ? 'met' : 'not met; validated higher detail retained'}.
            </p>
            <p>
              GPU coordinates use one common translation around the full asset bounds, restored by the shared model
              position. No per-region scaling is applied. Display coordinates preserve the patient-space frame. No
              anatomical direction marker or screen-pixel ruler is asserted. Mask quantities are not RECIST or a
              clinical response classification.
            </p>
          </details>
          {lesions && lesions.length > 1 ? (
            <p>
              <label htmlFor="lesion-picker-bottom">Compare another lesion in this case </label>
              <select
                id="lesion-picker-bottom"
                value={lesion ?? ''}
                onChange={event => switchLesion(event.target.value)}
                aria-label="Compare another lesion in this case"
              >
                {lesions.map((item, index) => (
                  <option key={item.lesion_id} value={item.lesion_id}>
                    Lesion {index + 1} · {item.lesion_id.slice(0, 8)}…
                  </option>
                ))}
              </select>
            </p>
          ) : null}
          </div> : null}
        </section>
      ) : null}
    </div>
  );
}
