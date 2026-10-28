'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import type { MeasurementReport, MeshAsset, MeshQCReport } from './mesh-types';
import styles from './mesh-preview.module.css';

const Renderer = dynamic(() => import('./mesh-renderer'), {ssr: false, loading: () => <p role="status">Loading 3D renderer…</p>});
const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
type Loaded = {report: MeshQCReport; asset: MeshAsset; measurement: MeasurementReport};

export function MeshPreview() {
  const [project, setProject] = useState('');
  const [patient, setPatient] = useState('');
  const [reportId, setReportId] = useState('');
  const [token, setToken] = useState('');
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const [blockedMeasurement, setBlockedMeasurement] = useState<MeasurementReport | null>(null);
  const [selected, setSelected] = useState('');
  const [message, setMessage] = useState('Enter authorized fixture identifiers to load a private mesh.');
  const [busy, setBusy] = useState(false);
  const [failed3D, setFailed3D] = useState(false);
  const [retry, setRetry] = useState(0);
  const pending = useRef<AbortController | null>(null);
  const failed = useCallback(() => setFailed3D(true), []);
  useEffect(() => () => pending.current?.abort(), []);

  function clear() {
    pending.current?.abort(); setLoaded(null); setBlockedMeasurement(null); setSelected(''); setBusy(false);
    setMessage('Selection changed. Load the selected authorized context.');
  }
  async function load(event: FormEvent) {
    event.preventDefault();
    pending.current?.abort(); setLoaded(null); setBlockedMeasurement(null); setSelected(''); setFailed3D(false);
    if (![project, patient, reportId].every(value => UUID.test(value)) || !token.trim()) {
      setMessage('Enter three valid UUIDs and an authorized access token.'); return;
    }
    const controller = new AbortController(); pending.current = controller;
    setBusy(true); setMessage('Loading authorized QC, geometry and source-mask measurements…');
    const root = `${API}/api/v1/projects/${project}/patients/${patient}`;
    async function get<T>(path: string): Promise<T> {
      const response = await fetch(root + path, {headers: {Authorization: `Bearer ${token.trim()}`}, signal: controller.signal, cache: 'no-store', credentials: 'omit', redirect: 'error'});
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) throw new Error('Access denied. Use an authorized editor token for this project and patient.');
        if (response.status === 404) throw new Error('This record is unavailable in the selected context. Check the identifiers.');
        if (response.status === 409) throw new Error('Current evidence or source permission blocks display. Keep the source-mask measurement and inspect QC.');
        throw new Error('The authorized read failed. Check the local API and retry.');
      }
      return response.json();
    }
    try {
      const report = await get<MeshQCReport>(`/mesh-qc-reports/${reportId}`);
      if (controller.signal.aborted) return;
      if (report.id !== reportId || !UUID.test(report.measurement_id)) throw new Error('The returned report does not match the selected context.');
      if (report.status !== 'validated' || !report.output_artifact_id) {
        const measurement = await get<MeasurementReport>(`/physical-measurements/${report.measurement_id}`);
        if (controller.signal.aborted) return;
        if (measurement.id === report.measurement_id) setBlockedMeasurement(measurement);
        setMessage('3D display is blocked by mesh QC. Source-mask measurements remain authoritative; inspect the mesh QC report before retrying.'); return;
      }
      const [asset, measurement] = await Promise.all([get<MeshAsset>(`/mesh-qc-reports/${reportId}/asset`), get<MeasurementReport>(`/physical-measurements/${report.measurement_id}`)]);
      if (controller.signal.aborted) return;
      if (asset.format !== 'canceros-mesh-json/1' || !Array.isArray(asset.objects) || asset.objects.length === 0) throw new Error('No supported 3D geometry is available. Inspect the source mask and QC.');
      if (measurement.id !== report.measurement_id || measurement.values.availability !== 'available' || measurement.input_revision !== report.input_revision || asset.objects.length !== measurement.selections.length || new Set(asset.objects.map(object => object.segmentation_id)).size !== asset.objects.length || asset.objects.some(object => !measurement.selections.some(selection => selection.segmentation_id === object.segmentation_id && selection.label === object.label && selection.mask_sha256 === object.mask_sha256))) throw new Error('Geometry and measurement references do not agree. Inspect the source report.');
      setLoaded({report, asset, measurement}); setSelected(asset.objects[0].segmentation_id);
      setMessage('Authorized private engineering geometry loaded. Scientific review and publication remain pending.');
    } catch (error) {
      if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : 'Unable to load this geometry. Retry the authorized read.');
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  const object = loaded?.asset.objects.find(item => item.segmentation_id === selected);
  const qc = loaded?.report.objects.find(item => item.segmentation_id === selected);
  return <div className={styles.preview}>
    <details open={!loaded}><summary>Private connection</summary><form className={styles.form} onSubmit={load} autoComplete="off">
      <label>Project UUID<input value={project} onChange={event => {clear(); setProject(event.target.value.trim());}} required spellCheck={false}/></label>
      <label>Patient UUID<input value={patient} onChange={event => {clear(); setPatient(event.target.value.trim());}} required spellCheck={false}/></label>
      <label>Mesh QC report UUID<input value={reportId} onChange={event => {clear(); setReportId(event.target.value.trim());}} required spellCheck={false}/></label>
      <label>Access token<input type="password" autoComplete="off" value={token} onChange={event => {clear(); setToken(event.target.value);}} required spellCheck={false}/></label>
      <p className={styles.note}>Use an authorized local editor access token. Use Clear private view when finished; nothing is stored in browser storage. No source names or clinical uploads are requested.</p>
      <div className={styles.controls}><button disabled={busy} type="submit">{busy ? 'Loading…' : 'Load private mesh'}</button><button type="button" onClick={() => {clear(); setToken(''); setMessage('Private geometry and access token cleared.');}}>Clear private view</button></div>
    </form></details>
    <p role="status" aria-live="polite">{message}</p>
    {blockedMeasurement && <div className={styles.notice}><h2>Source-mask measurement</h2><p>3D geometry is unavailable for this selection. No substitute shape is displayed.</p><p>Mask volume: {blockedMeasurement.values.volume_mm3 ?? 'Unavailable'} mm³. Centroid, RAS: {blockedMeasurement.values.centroid_ras_mm?.join(', ') ?? 'Unavailable'} mm. Origin: {blockedMeasurement.origin}. Source time: {blockedMeasurement.source_time_basis === 'not_recorded' ? 'Not recorded' : 'Private source timing is unavailable in this view'}. Scientific review: pending.</p></div>}
    {loaded && <section aria-label="Authorized engineering mesh">
      <div className={styles.notice}><strong>Synthetic engineering fixture · private draft · scientific review pending</strong><p>No eligible patient-specific breast anatomy is available. Context is omitted; this region view cannot establish anatomical placement, invasion, distances or surgery.</p></div>
      <p><strong>Observation time:</strong> {loaded.measurement.source_time_basis === 'not_recorded' ? 'Not recorded' : loaded.measurement.source_time_basis === 'shifted_source_private' ? 'Shifted source time is private; actual date is not exposed' : 'Source time is private; actual date is not exposed'}. No follow-up time is inferred.</p>
      <label className={styles.selector}>Selected annotation<select value={selected} onChange={event => setSelected(event.target.value)}>{loaded.asset.objects.map(item => <option key={item.segmentation_id} value={item.segmentation_id}>Label {item.label} · {item.annotation_class.replaceAll('_', ' ')} · {item.segmentation_id.slice(0, 8)}</option>)}</select></label>
      {object && <p><strong>Annotation class:</strong> {object.annotation_class.replaceAll('_', ' ')} · label {object.label}. Region geometry does not establish an anatomical tumor. Physical frame: RAS; units: mm.</p>}
      {!failed3D ? <Renderer key={retry} asset={loaded.asset} selected={selected} onFailure={failed}/> : <div className={styles.notice} role="alert"><strong>3D is unavailable on this device or the graphics context was lost.</strong><p>Use the measurement table below. No substitute tumor is displayed.</p><button onClick={() => {setFailed3D(false); setRetry(value => value + 1);}}>Retry 3D</button></div>}
      <div className={styles.tableWrap}><table><caption>Server measurements and physical geometry · source mask is authoritative</caption><thead><tr><th scope="col">Quantity</th><th scope="col">Value</th></tr></thead><tbody>
        <tr><th scope="row">Selected label mask volume</th><td>{qc?.mask_volume_mm3 ?? 'Unavailable'} mm³</td></tr>
        <tr><th scope="row">Explicit selected-label union mask volume</th><td>{loaded.measurement.values.volume_mm3 ?? 'Unavailable'} mm³ ({loaded.measurement.values.volume_cm3 ?? 'Unavailable'} cm³)</td></tr>
        <tr><th scope="row">Union mask centroid, RAS</th><td>{loaded.measurement.values.centroid_ras_mm?.join(', ') ?? 'Unavailable'} mm</td></tr>
        <tr><th scope="row">Selected surface bounds, RAS</th><td>{object?.surface.bounds_min_mm.join(', ')} to {object?.surface.bounds_max_mm.join(', ')} mm</td></tr>
        <tr><th scope="row">Input revision</th><td>{loaded.report.input_revision}</td></tr>
      </tbody></table></div>
      <details><summary>Geometry and QC details</summary><p>Selected format: {loaded.asset.format}. Display selection: {loaded.report.selection}. Transfer: {loaded.report.selected_byte_size} bytes. Triangles: {loaded.report.selected_triangles}. Requested budget: {loaded.report.budget_met ? 'met' : 'not met; validated higher detail retained'}.</p><p>GPU coordinates use one common translation around the full asset bounds, restored by the shared model position. No per-region scaling is applied. Display coordinates preserve the patient-space frame. No anatomical direction marker or screen-pixel ruler is asserted. Mask quantities are not RECIST or a clinical response classification.</p></details>
    </section>}
  </div>;
}
