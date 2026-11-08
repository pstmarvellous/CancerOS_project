'use client';

import dynamic from 'next/dynamic';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { components } from '../../../packages/contracts/generated/api';
import { ProvenanceBadge, TimeLabel } from './research';
import type { RenderableMesh } from './mesh-renderer';
import styles from './simulation-workflow.module.css';
import { TrendView } from './trend-view';
import type { TrendReport } from './trend-view';
import { StateFusionView } from './state-fusion-view';
import { RevisionUpdatePanel } from './revision-update-panel';

type S = components['schemas'];
export type TimelinePoint = S['TimelinePoint'];
type Scope = S['TimelineScope'];
type Query = S['TimelineQuery'];
type Page = S['TimelinePage'];
const Renderer = dynamic(() => import('./mesh-renderer'), {ssr: false, loading: () => <p role="status">Loading geometry renderer…</p>});
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function pointValue(point: TimelinePoint) {
  if (point.numeric_result?.form === 'exact') return `${point.exact_value ?? point.numeric_result.quantity.value} ${point.numeric_result.quantity.unit}`;
  if (point.numeric_result?.form === 'censored') return `${point.numeric_result.comparator}${point.numeric_result.threshold.value} ${point.numeric_result.threshold.unit} (censored)`;
  if (point.ordinal_value != null) return `${point.ordinal_value} · ${point.instrument}/${point.instrument_version} · ${point.symptom_presence ?? 'presence unknown'}`;
  return point.missing_reason ?? (point.numeric_result?.form === 'missing' ? point.numeric_result.missing_reason : point.summary ?? `No numeric value · ${point.availability}`);
}

export function ObservationTimeline({ project: overrideProject, patient: overridePatient }: { project?: string | null; patient?: string | null } = {}) {
  const [selection] = useState<{ project: string; patient: string } | null>(
    overrideProject && overridePatient ? { project: overrideProject, patient: overridePatient } : null,
  );
  const timelineBase = selection
    ? '/api/observation-timeline?project=' + encodeURIComponent(selection.project) + '&patient=' + encodeURIComponent(selection.patient)
    : '';
  const [mode, setMode] = useState<Scope['mode']>('observed'); const [revision, setRevision] = useState('1');
  const [branch, setBranch] = useState(''); const [run, setRun] = useState(''); const [completion, setCompletion] = useState('');
  const [knowledge, setKnowledge] = useState(''); const [cutoff, setCutoff] = useState(''); const [origin, setOrigin] = useState('');
  const [page, setPage] = useState<Page | null>(null); const [items, setItems] = useState<TimelinePoint[]>([]);
  const [query, setQuery] = useState<Query | null>(null); const [selected, setSelected] = useState<TimelinePoint | null>(null);
  const [trends, setTrends] = useState<TrendReport | null>(null);
  const [fusion, setFusion] = useState<S['FusionReport'] | null>(null);
  const [fusionState, setFusionState] = useState(''); const [fusionBusy, setFusionBusy] = useState(false);
  const [fusionMessage, setFusionMessage] = useState('Load an exact state overview to inspect its retained membership.');
  const [mesh, setMesh] = useState<RenderableMesh | null>(null); const [meshMessage, setMeshMessage] = useState('Select an observation to inspect its available view.');
  const [busy, setBusy] = useState(false); const [message, setMessage] = useState('Choose an exact revision, source context and knowledge cutoff.');
  const pending = useRef<AbortController | null>(null); const meshPending = useRef<AbortController | null>(null);
  const fusionPending = useRef<AbortController | null>(null);
  const failed = useCallback(() => {setMesh(null); setMeshMessage('3D is unavailable. The selected observation and measurement remain available below.');}, []);
  useEffect(() => () => {pending.current?.abort(); meshPending.current?.abort(); fusionPending.current?.abort();}, []);
  function clearFusion() {fusionPending.current?.abort(); setFusion(null); setFusionState(''); setFusionBusy(false); setFusionMessage('Load an exact state overview to inspect its retained membership.');}
  function changed() {pending.current?.abort(); meshPending.current?.abort(); clearFusion(); setBusy(false); setPage(null); setItems([]); setQuery(null); setTrends(null); setSelected(null); setMesh(null); setMessage('Selection changed. Reload the exact timeline window.');}
  async function request<T>(action: string, signal: AbortSignal, body?: unknown, meshId?: string): Promise<T> {
    if (!selection || !timelineBase) throw new Error('Open a case first.');
    const response = await fetch(body === undefined ? `${timelineBase}&mesh=${encodeURIComponent(meshId ?? '')}` : `${timelineBase}&action=${action}`, {method: body === undefined ? 'GET' : 'POST', headers: body === undefined ? {} : {'Content-Type': 'application/json'}, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store', credentials: 'omit', redirect: 'error', signal});
    if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? 'Access denied for this timeline context.' : response.status === 409 ? 'Timeline revision, publication, permissions or cursor changed. Reload this exact window; no partial page is added.' : response.status === 422 ? 'Check revision, context identifiers and timezone-aware knowledge cutoff.' : 'Timeline unavailable. Check the local API and retry.');
    return response.json();
  }
  async function load(next = false) {
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller;
    if (!selection) { setMessage('Open a case first; the browser never guesses a project or patient.'); return; }
    if (!next) {setTrends(null); clearFusion();}
    setBusy(true);
    try {
      let body: Query;
      if (next && query && page?.next_cursor) body = {...query, cursor: page.next_cursor};
      else {
        const dataRevision = Number(revision);
        if (!Number.isSafeInteger(dataRevision) || dataRevision < 1) throw new Error('Enter a positive exact data revision.');
        if (!/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(knowledge) || Number.isNaN(Date.parse(knowledge))) throw new Error('Enter a timezone-aware knowledge cutoff, such as an ISO timestamp ending in Z.');
        if (mode === 'simulation' && ![branch, run, completion].every(value => UUID.test(value))) throw new Error('Simulation requires exact branch, run and published completion UUIDs.');
        if (cutoff && (mode !== 'simulation' || !UUID.test(origin) || !/^-?\d+(\.\d{1,4})?$/.test(cutoff))) throw new Error('A simulation-day cutoff requires an explicit timeline-origin UUID and a valid relative day.');
        body = {window: {scope: {mode, data_revision: dataRevision, ...(mode === 'simulation' ? {branch_id: branch, run_id: run} : {})}, knowledge_as_of: knowledge, event_cutoff: cutoff ? {basis: 'relative_day', value: cutoff, time_domain: 'simulation', timeline_origin_id: origin, anchor_state_id: null} : null}, completion_id: mode === 'simulation' ? completion : null, limit: 25};
      }
      const result = await request<Page>('timeline', controller.signal, body);
      if (controller.signal.aborted) return;
      if (next) setItems(previous => [...previous, ...result.items.filter(point => !previous.some(existing => existing.id === point.id))]);
      else {meshPending.current?.abort(); setSelected(null); setMesh(null); setItems(result.items); setQuery(body);}
      setPage(result); setMessage(result.next_action);
    } catch (error) {if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : 'Timeline request failed. Retry the same window.');}
    finally {if (!controller.signal.aborted) setBusy(false);}
  }
  async function select(point: TimelinePoint) {
    meshPending.current?.abort(); clearFusion(); setSelected(point); setMesh(null);
    if (!point.geometry_result_id) {setMeshMessage('No geometry at this observation. No previous observation geometry is carried forward.'); return;}
    const controller = new AbortController(); meshPending.current = controller; setMeshMessage('Loading geometry for this exact selected observation…');
    try {
      const result = await request<S['GeneratedMesh']>('mesh', controller.signal, undefined, point.geometry_result_id);
      if (controller.signal.aborted) return;
      if (result.geometry_id !== point.id || result.origin !== 'SYNTHETIC_GENERATED') throw new Error('Geometry identity does not match this observation.');
      setMesh({objects: [{segmentation_id: point.id, surface: result.surface}]}); setMeshMessage('Exact selected synthetic region · physical RAS mm · not a follow-up scan or anatomical placement.');
    } catch (error) {if (!controller.signal.aborted) setMeshMessage(error instanceof Error ? error.message : 'Geometry unavailable for this observation.');}
  }
  async function loadTrends() {
    if (!query) return;
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller; setBusy(true); setTrends(null);
    try {
      const result = await request<TrendReport>('trends', controller.signal, {timeline: {...query, cursor: null}, tolerance: '0'});
      if (!controller.signal.aborted) {setTrends(result); setMessage('Descriptive trends loaded over the exact full window. No hidden generator values or frontend medical calculations are used.');}
    } catch (error) {if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : 'Trend query unavailable. Retry the exact window.');}
    finally {if (!controller.signal.aborted) setBusy(false);}
  }
  function selectTrendPoint(identifier: string) {
    meshPending.current?.abort(); clearFusion(); setMesh(null); setSelected(null);
    const point = items.find(item => item.id === identifier);
    if (point) void select(point);
    else setMessage(`Point ${identifier} belongs to the full trend window but is not in the loaded timeline pages. Load the next pinned page to inspect its exact state and geometry.`);
  }
  const selectedState = selected?.state_ids.length === 1 ? selected.state_ids[0] : fusionState;
  async function loadFusion() {
    if (busy || !selected || !selectedState || !selected.state_ids.includes(selectedState) || mode === 'observed' || !query) return;
    fusionPending.current?.abort(); const controller = new AbortController(); fusionPending.current = controller;
    setFusion(null); setFusionBusy(true); setFusionMessage('Loading the exact state membership and retained evidence…');
    try {
      const result = await request<S['FusionReport']>('fusion', controller.signal, {state_id: selectedState, timeline: query.window.scope.mode === 'simulation' ? {...query, cursor: null} : null});
      if (result.canonical_state.snapshot.id !== selectedState) throw new Error('State overview identity does not match the selected state.');
      if (!controller.signal.aborted) {setFusion(result); setFusionMessage('Exact state overview loaded. Historical members remain historical; missing sections remain missing.');}
    } catch (error) {if (!controller.signal.aborted) setFusionMessage(error instanceof Error ? error.message : 'State overview unavailable. Retry the same authorized state.');}
    finally {if (!controller.signal.aborted) setFusionBusy(false);}
  }
  return <div className={styles.workflow}>
    <div className={styles.notice}><strong>Exact observation history · no imputation or value carry-forward</strong><p>Source and simulation contexts remain separate. Numerical features are deterministic derivatives, not a diagnosis or prediction. Unknown and incomparable times stay unresolved.</p></div>
    <section><h2>Timeline window</h2><form onSubmit={event => {event.preventDefault(); void load();}} autoComplete="off" className={styles.grid}>
      {selection ? <p className="field-hint">Authorized case: {selection.project.slice(0, 8)}… · {selection.patient.slice(0, 8)}… — session authorized; switch from the case library.</p> : <p className="field-hint">No case selected.</p>}
      <label>Observation context<select value={mode} onChange={event => {changed(); setMode(event.target.value as Scope['mode']); setCutoff('');}}><option value="observed">Real observed source history</option><option value="source_fixture">Synthetic source fixture history</option><option value="simulation">Published simulation branch</option></select></label>
      <label>Exact data revision<input value={revision} onChange={event => {changed(); setRevision(event.target.value);}} inputMode="numeric" required/></label>
      <label>Knowledge as of (ISO timestamp with timezone)<input value={knowledge} onChange={event => {changed(); setKnowledge(event.target.value);}} placeholder="YYYY-MM-DDTHH:MM:SSZ" required/></label>
      {mode === 'simulation' && <>{([['Branch UUID', branch, setBranch], ['Run UUID', run, setRun], ['Published completion UUID', completion, setCompletion], ['Simulation event cutoff day (optional)', cutoff, setCutoff], ['Timeline origin UUID (for cutoff)', origin, setOrigin]] as const).map(([label, value, setter]) => <label key={label}>{label}<input value={value} onChange={event => {changed(); setter(event.target.value.trim());}}/></label>)}</>}
      <p>Loaded observations remain in memory; the research session cookie authorizes every request. The knowledge cutoff limits when evidence became available; event-time cutoffs do not invent a calendar anchor. Source histories use the full event window at the selected knowledge cutoff.</p>
      <div className={styles.controls}><button disabled={busy}>Load exact timeline</button><button type="button" onClick={() => {changed(); setMessage('Private timeline cleared.');}}>Clear private view</button></div>
    </form></section>
    <p role="status" aria-live="polite">{message}</p>
    {page && <><section><h2>Observation points</h2><p>{items.length} loaded of {page.total_points} points. Revision {revision} · {page.historical_revision ? 'historical revision' : 'current revision'}. Current patient revision: {page.current_patient_revision}.</p>{page.restrictions.map(reason => <p key={reason}>{reason}</p>)}
      <div className={styles.table}><table><caption>Individual observation times · no visit inferred</caption><thead><tr><th>Select</th><th>Time / precision</th><th>Modality / concept</th><th>Origin</th><th>Value / missingness</th></tr></thead><tbody>{items.map(point => <tr key={point.id} aria-selected={selected?.id === point.id}><td><button onClick={() => void select(point)}>Inspect {point.id.slice(0, 8)}</button></td><td><TimeLabel time={point.time.reference}/><p>Precision: {point.time.precision}</p>{point.historical_context && <p>Historical context / baseline reference</p>}</td><td>{point.modality} · {point.concept}</td><td><ProvenanceBadge origin={point.origin}/></td><td>{pointValue(point)}{point.conflicts.length > 0 && <p>Conflict: {point.conflicts.join(' · ')}</p>}</td></tr>)}</tbody></table></div>
      {items.length === 0 && <p>No observations in this exact window. No substitute values are shown.</p>}
      <button disabled={busy || !page.next_cursor} onClick={() => void load(true)}>Load next pinned page</button>
      <button disabled={busy || !query} onClick={() => void loadTrends()}>Load descriptive trends for this window</button>
    </section><section><h2>Full-window temporal features</h2><p>Version: {page.features.version}. These features cover the selected window, including points beyond the currently loaded page. Missing counts do not imply a filled value.</p><div className={styles.table}><table><caption>Server-computed intervals and measurement age</caption><thead><tr><th>Series / method</th><th>Usable / missing / censored</th><th>Intervals (days)</th><th>Age (days)</th><th>Lesion / instrument</th></tr></thead><tbody>{page.features.series.map((series, index) => <tr key={index}><td>{series.concept} · {series.unit ?? 'No numeric unit'}<p>{series.method_version}</p></td><td>{series.usable_count} / {series.missing_count} / {series.censored_count}</td><td>{series.interval_days.join(', ') || 'No comparable intervals'}</td><td>{series.age_days ?? 'Unresolved / no valid cutoff'}</td><td>{series.lesion_id ?? 'No lesion link'} · {series.instrument ? `${series.instrument}/${series.instrument_version}` : 'No ordinal instrument'}</td></tr>)}</tbody></table></div><p>Unresolved-time point IDs: {page.features.unresolved_point_ids.join(', ') || 'None'}. Treatment-context point IDs: {page.features.treatment_point_ids.join(', ') || 'None'}.</p></section></>}
    {page && query && <RevisionUpdatePanel key={`${timelineBase}:${JSON.stringify(query)}:${selected?.id ?? ''}:${selectedState ?? ''}`} query={query} baseUrl={timelineBase}/>}
    {trends && <TrendView report={trends} onSelect={selectTrendPoint}/>}
    {selected && <section><h2>Selected observation</h2><p>ID: {selected.id} · <TimeLabel time={selected.time.reference}/> · {selected.modality} · <ProvenanceBadge origin={selected.origin}/></p><p>{pointValue(selected)}. Availability: {selected.availability}. Measurement basis: {selected.measurement_basis}.</p><p>Recorded / available at: {selected.recorded_at}. Method: {selected.method_version}. Supersedes: {selected.supersedes_id ?? 'None'}. State IDs: {selected.state_ids.join(', ') || 'No state membership'}.</p>{selected.summary && <p>{selected.summary}</p>}<p role="status">{meshMessage}</p>{mesh && <Renderer key={selected.id} asset={mesh} selected={selected.id} onFailure={failed}/>}
      <h3>Exact state overview</h3>
      {mode === 'observed' ? <p>Authentic observed-state fusion is not established. Source observations remain available above.</p> : selected.state_ids.length === 0 ? <p>No canonical state membership is available for this observation. No state is inferred from nearby observations.</p> : <>
        {selected.state_ids.length > 1 ? <label>Exact state membership<select value={fusionState} onChange={event => {clearFusion(); setFusionState(event.target.value);}}><option value="">Choose a state explicitly</option>{selected.state_ids.map(id => <option key={id} value={id}>{id}</option>)}</select></label> : <p>Exact state: {selectedState}</p>}
        <button disabled={busy || fusionBusy || !selectedState || !query} onClick={() => void loadFusion()}>Load exact state overview</button>
        <p role="status" aria-live="polite">{fusionMessage}</p>
      </>}
      {fusion && <StateFusionView report={fusion}/>}
    </section>}
  </div>;
}
