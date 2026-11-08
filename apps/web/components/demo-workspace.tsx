'use client';

import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react';
import type { DemoCatalog, DemoScenario } from '../lib/demo-contracts';
import { familyPresentation, readableConcept, volumeComparison } from '../lib/scenario-presentation';
import { pointValue, type TimelinePoint } from './observation-timeline';
import { TermHelp } from './term-help';
import { TrendView } from './trend-view';
import styles from './demo-workspace.module.css';

const Renderer = dynamic(() => import('./mesh-renderer'), { ssr: false,
  loading: () => <p role="status">Loading the 3D viewer…</p> });
const VIEWS = [
  ['overview', 'Overview'], ['twin', '3D Digital Twin'], ['scenarios', 'Hypothetical Scenarios'],
  ['clinical', 'Clinical Data'], ['insights', 'AI Research Insights'], ['technical', 'Evaluation / Technical Details'],
] as const;
const name = (point: TimelinePoint) => point.measurement_basis === 'baseline_reference' ? 'Shared baseline' : `Day ${day(point) ?? 'not recorded'}`;
const day = (point: TimelinePoint) => point.time.reference.basis === 'relative_day' ? point.time.reference.value : null;
const clinicalValue = (point: TimelinePoint) => point.ordinal_value != null
  ? `${point.ordinal_value} on the demonstration scale · ${point.symptom_presence?.replaceAll('_', ' ') ?? 'presence unknown'}`
  : pointValue(point);
const subscribeFullscreen = (changed: () => void) => {
  document.addEventListener('fullscreenchange', changed);
  return () => document.removeEventListener('fullscreenchange', changed);
};

async function read<T>(url: string, signal: AbortSignal, method = 'GET'): Promise<T> {
  const response = await fetch(url, { method, signal, cache: 'no-store', credentials: 'same-origin' });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.title ?? 'The demo could not load. Try opening it again.');
  }
  return response.json();
}

export function DemoWorkspace() {
  const params = useSearchParams();
  const family = params.get('scenario') ?? 'SC-01';
  const requestedPoint = params.get('state');
  const view = params.get('view') ?? 'twin';
  const [catalog, setCatalog] = useState<DemoCatalog | null>(null);
  const [scenario, setScenario] = useState<DemoScenario | null>(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [failed3D, setFailed3D] = useState(false);
  const [renderAttempt, setRenderAttempt] = useState(0);
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);
  const [fullTwin, setFullTwin] = useState(false);
  const [fullscreenMessage, setFullscreenMessage] = useState('');
  const viewer = useRef<HTMLElement>(null);
  const fullscreenAvailable = useSyncExternalStore(subscribeFullscreen, () => document.fullscreenEnabled, () => false);
  const nativeFullscreen = useSyncExternalStore(subscribeFullscreen, () => !!viewer.current && document.fullscreenElement === viewer.current, () => false);
  const onFailure = useCallback(() => setFailed3D(true), []);

  useEffect(() => {
    const escape = (event: KeyboardEvent) => { if (event.key === 'Escape' && !document.fullscreenElement) setFullTwin(false); };
    document.addEventListener('keydown', escape);
    return () => document.removeEventListener('keydown', escape);
  }, []);

  useEffect(() => {
    if ((!fullTwin && !nativeFullscreen) || !viewer.current) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = previous; };
  }, [fullTwin, nativeFullscreen, view, scenario, family, requestedPoint]);

  useEffect(() => {
    if (!fullTwin || !viewer.current) return;
    const element = viewer.current;
    const previous = document.activeElement;
    element.focus({ preventScroll: true });
    const trap = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;
      const controls = [...element.querySelectorAll<HTMLElement>('button:not(:disabled), select, a[href], [tabindex="0"], summary')].filter(item => item.getClientRects().length > 0);
      const first = controls[0], last = controls.at(-1);
      if (event.shiftKey && (document.activeElement === first || document.activeElement === element)) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || document.activeElement === element)) { event.preventDefault(); first?.focus(); }
    };
    element.addEventListener('keydown', trap);
    return () => { element.removeEventListener('keydown', trap); if (previous instanceof HTMLElement && previous.isConnected) previous.focus({ preventScroll: true }); };
  }, [fullTwin, scenario, family, view, requestedPoint]);

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement === viewer.current) await document.exitFullscreen();
      else await viewer.current?.requestFullscreen();
      setFullscreenMessage('');
    } catch { setFullscreenMessage('Fullscreen is unavailable in this browser. Use Maximize viewer for more space.'); }
  }

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      try {
        await read('/api/demo-session', controller.signal, 'POST');
        const result = await read<DemoCatalog>('/api/demo', controller.signal);
        if (!controller.signal.aborted) { setCatalog(result); setError(''); }
      } catch (error) {
        if (!controller.signal.aborted) setError(error instanceof Error ? error.message : 'The demo could not open.');
      }
    })();
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    if (!catalog) return;
    const controller = new AbortController();
    (async () => {
      try {
        const result = await read<DemoScenario>(`/api/demo?scenario=${encodeURIComponent(family)}`, controller.signal);
        if (!controller.signal.aborted) { setScenario(result); setFailed3D(false); setError(''); }
      } catch (error) {
        if (!controller.signal.aborted) setError(error instanceof Error ? error.message : 'This scenario could not load.');
      }
    })();
    return () => controller.abort();
  }, [catalog, family, attempt]);

  // Bind every panel to the complete URL selection. A previous response is never
  // displayed under a new family label, even during rapid navigation.
  const current = scenario?.id === family ? scenario : null;
  const points = current?.timeline.items.filter(p => ['baseline_reference', 'mask_realized'].includes(p.measurement_basis)) ?? [];
  const selected = requestedPoint ? points.find(p => p.id === requestedPoint) : points[0];
  const index = selected ? points.indexOf(selected) : -1;
  // The existing renderer frames all states together and displays only the
  // selected mesh. Camera scale therefore stays constant across timeline steps.
  const asset = useMemo(() => current ? { objects: Object.entries(current.meshes).map(([id, surface]) => ({ segmentation_id: id, surface })) } : null, [current]);
  function href(next: { view?: string; scenario?: string; state?: string | null }) {
    const query = new URLSearchParams({ view: next.view ?? view, scenario: next.scenario ?? family });
    const point = next.state === undefined ? requestedPoint : next.state;
    if (point) query.set('state', point);
    return `/demo?${query}`;
  }
  function navigate(next: { view?: string; scenario?: string; state?: string | null }) {
    window.history.pushState(null, '', href(next));
    setFailed3D(false);
  }

  if (error) return <section className="card" role="alert"><h1>The demo could not open</h1><p>{error}</p>
    <p>If you run this computer, check the demo bundle with <code>uv run python scripts/prepare_synthetic_demo.py --check</code>, then retry. Otherwise, try again later.</p>
    <button onClick={() => { setError(''); setCatalog(null); setScenario(null); setAttempt(n => n + 1); }}>Retry demo</button>{' '}
    <Link href="/">Return to overview</Link></section>;
  if (!catalog) return <section className="card"><h1>Opening the Digital Twin Demo</h1><p role="status">Preparing your read-only synthetic research workspace…</p></section>;

  return <div className={`${styles.workspace} workspace-wide`} data-left={leftOpen ? 'open' : 'collapsed'} data-right={rightOpen ? 'open' : 'collapsed'}>
    <aside className={styles.rail} aria-label="Demo navigation panel">
      <p><button type="button" className={styles.railToggle} aria-label={leftOpen ? 'Collapse navigation' : 'Expand navigation'} aria-controls="demo-navigation" aria-expanded={leftOpen} onClick={() => setLeftOpen(open => !open)}><span aria-hidden="true">{leftOpen ? '‹' : '☰'}</span><span className={styles.railToggleText}>Navigation</span></button></p>
      <div id="demo-navigation" hidden={!leftOpen}>
      <p className="eyebrow">RESEARCH DEMO 01</p><p className={styles.caseName}>A window into<br/>cancer evolution</p>
      <nav aria-label="Demo workspace">{VIEWS.map(([id, label]) => <Link key={id} href={href({ view: id })} aria-current={view === id ? 'page' : undefined}>{label}</Link>)}</nav>
      <div className={styles.railNote}><span className={styles.dot}/> Read-only demonstration<p>Synthetic geometry and observations. No patient anatomy or clinical predictions.</p></div>
      </div>
    </aside>
    <div className={styles.content}>
      <div className={styles.heading}><div><p className="eyebrow">BREAST CANCER RESEARCH · DIGITAL TWIN</p>
        <h1>{VIEWS.find(([id]) => id === view)?.[1] ?? 'Digital Twin Demo'}</h1></div><span className={styles.pill}>Synthetic demonstration</span></div>
      <div className={styles.context}>
        <label htmlFor="demo-scenario">Hypothetical scenario<select id="demo-scenario" value={family} onChange={event => navigate({ scenario: event.target.value, state: null })}>
          {catalog.scenarios.map(s => <option value={s.id} key={s.id}>{familyPresentation(s.id).plainName}</option>)}</select></label>
        <p>{current ? familyPresentation(family).explanation : 'Loading this scenario…'} <span>Unvalidated what-if exploration · {family}.</span></p>
      </div>
      {!current ? <p role="status">Loading the selected scenario and its measurements…</p> : !selected ?
        <section className="card"><h2>This state is unavailable</h2><p>The saved selection does not belong to this scenario.</p><Link href={href({ state: null })}>Open the shared baseline</Link></section> : <>
      {view === 'overview' && <section className={styles.panel}><h2>Explore a research digital twin</h2><p>This demonstration connects a synthetic tumor-region mask to measured 3D geometry, five hypothetical scenarios and time-indexed observations.</p>
        <div className={styles.steps}><p><b>1. Explore</b>Rotate the model and inspect its measurements.</p><p><b>2. Compare</b>Choose a scenario, then select a day on the timeline.</p><p><b>3. Understand</b>Open Clinical Data or AI Research Insights for context.</p></div>
        <Link className="button" href={href({ view: 'twin' })}>Explore the 3D Digital Twin</Link>
        <p className={styles.subtle}>The shared baseline is a geometric phantom, not a real scan. Missing clinical facts stay missing.</p></section>}
      {view === 'scenarios' && <section className={styles.panel}><h2>Explore a hypothetical scenario</h2><p>Each family shares the same 216 mm³ synthetic baseline and has three generated follow-ups. These are demonstrations of assumptions, not patient-specific predictions.</p>
        <div className={styles.scenarios}>{catalog.scenarios.map(s => <Link key={s.id} href={href({ view: 'twin', scenario: s.id, state: null })} aria-current={s.id === family ? 'true' : undefined}><h3>{familyPresentation(s.id).plainName}</h3><p>{familyPresentation(s.id).explanation}</p><span>Explore in 3D →</span></Link>)}</div></section>}
      {(view === 'twin' || view === 'overview') && <div className={styles.twin} data-details={rightOpen ? 'open' : 'collapsed'}>
        <section ref={viewer} tabIndex={-1} role={fullTwin ? 'dialog' : undefined} aria-modal={fullTwin ? true : undefined} className={styles.viewer} aria-label="Selected digital twin" data-maximized={fullTwin ? 'true' : undefined} data-native-fullscreen={nativeFullscreen ? 'true' : undefined}>
          <div className={styles.viewerHeading}><div><p className="eyebrow">SYNTHETIC TUMOR REGION · {family}</p><h2>{name(selected)} — {selected.exact_value ?? 'Unavailable'} mm³</h2></div><span>Relative day {day(selected)}</span></div>
          <div className={styles.viewerActions}>
            <button type="button" aria-pressed={fullTwin} onClick={() => setFullTwin(full => !full)}>{fullTwin ? 'Restore layout' : 'Maximize viewer'}</button>
            {fullscreenAvailable && <button type="button" aria-pressed={nativeFullscreen} onClick={() => void toggleFullscreen()}>{nativeFullscreen ? 'Exit fullscreen' : 'Fullscreen'}</button>}
            {!fullTwin && !nativeFullscreen && <button type="button" aria-controls="demo-measurements" aria-expanded={rightOpen} onClick={() => setRightOpen(open => !open)}>{rightOpen ? 'Collapse measurements' : 'Show measurements'}</button>}
            {(fullTwin || nativeFullscreen) && <label>Scenario<select aria-label="Viewer hypothetical scenario" value={family} onChange={event => navigate({ scenario: event.target.value, state: null })}>{catalog.scenarios.map(s => <option key={s.id} value={s.id}>{familyPresentation(s.id).plainName}</option>)}</select></label>}
            <span className={styles.inlineMeasurement}>{selected.exact_value ?? 'Unavailable'} mm³ · {name(selected)}</span>
          </div>
          {fullscreenMessage && <p className={styles.subtle} role="status">{fullscreenMessage}</p>}
          <BaselineComparison points={points} selected={selected} />
          {asset && !failed3D ? <Renderer key={`${family}:${renderAttempt}`} asset={asset} selected={selected.id} onFailure={onFailure} label="Synthetic tumor region · geometric phantom · mm"/> :
            <div className={styles.recovery} role="alert"><h3>The 3D view could not load</h3><p>Your selected measurements remain available. Retry with browser graphics acceleration enabled.</p><button onClick={() => { setFailed3D(false); setRenderAttempt(n => n + 1); }}>Retry 3D viewer</button></div>}
          <div className={styles.timeline} aria-label="Scenario timeline"><div><h3>Explore changes over time</h3><p>Select a measured state. Days are relative to the synthetic baseline.</p></div>
            <div className={styles.timeButtons}>{points.map(point => <button key={point.id} aria-pressed={point.id === selected.id} onClick={() => navigate({ state: point.id })}><span>{name(point)}</span><small>{pointValue(point)}</small></button>)}</div>
            <div className={styles.paging}><button disabled={index <= 0} onClick={() => navigate({ state: points[index - 1].id })}>← Previous state</button><span>{index + 1} of {points.length}</span><button disabled={index >= points.length - 1} onClick={() => navigate({ state: points[index + 1].id })}>Next state →</button></div>
          </div>
        </section>
        <aside id="demo-measurements" hidden={!rightOpen} className={styles.inspector} aria-label="Selected state measurements">
          <section className={styles.panel}><p className="eyebrow">SELECTED STATE</p><h2>{name(selected)}</h2><p className={styles.subtle}>{current.label}</p><dl className={styles.metrics}><div><dt>Region volume</dt><dd data-testid="demo-volume">{selected.exact_value ?? 'Unavailable'} <small>mm³</small></dd></div><div><dt>Source</dt><dd className={styles.smallMetric}>Synthetic mask</dd></div><div><dt>Measurement</dt><dd className={styles.smallMetric}>Computed by CancerOS backend</dd></div></dl><p className={styles.subtle}>Volume comes from the voxel mask, not the displayed surface or an AI model.</p></section>
          <section className={styles.panel}><h2>What am I looking at?</h2><p>A measured synthetic region used to demonstrate tumor exploration. Its geometric shape is a test phantom, not authentic patient anatomy.</p><p>No breast anatomy, MRI scan or anatomical placement is implied.</p></section>
          <section className={styles.panel}><h2>Continue exploring</h2><p><Link href={href({ view: 'clinical' })}>Inspect clinical observations →</Link></p><p><Link href={href({ view: 'insights' })}>Read research insights →</Link></p></section>
        </aside>
      </div>}
      {(view === 'twin' || view === 'clinical') && <section className={styles.panel}><h2>Volume over time</h2><p>Backend measurements for <b>{familyPresentation(family).plainName} ({family})</b>. Highlighted point: {name(selected)} · {selected.exact_value ?? 'Unavailable'} mm³.</p><VolumeChart scenario={current} selected={selected.id} onSelect={id => navigate({ state: id })}/></section>}
      {view === 'clinical' && <section className={styles.panel}><h2>Clinical observations</h2><p>Selected geometry: <b>{name(selected)}</b>. Observations below retain their own collection days; they are not carried forward to this state.</p><p className={styles.subtle}>All available observations here were generated for this synthetic scenario. No authentic laboratory, pathology or treatment records are included.</p>
        <div className={styles.table}><table><caption>Scenario observations with their actual relative times</caption><thead><tr><th>Observation</th><th>Relative day</th><th>Value or missingness</th><th>Recorded</th><th>Source</th></tr></thead><tbody>{current.timeline.items.filter(p => p.modality !== 'imaging').map(p => <tr key={p.id}><th>{readableConcept(p.concept)}</th><td>{day(p) ?? 'Not recorded'}</td><td>{clinicalValue(p)}</td><td>{formatRecorded(p.recorded_at)}</td><td>Synthetic scenario</td></tr>)}</tbody></table></div>
        <p className={styles.subtle}>Symptom ratings use an unvalidated demonstration scale, not a clinical severity grade. Missing observations are never filled in from other days.</p>
        <p>Pathology, receptor status, authentic notes and real longitudinal observations: <b>Not recorded in this demonstration.</b></p>
        <TermHelp terms={['mm³', 'Relative day', 'Synthetic observation', 'Derived measurement']} /></section>}
      {view === 'insights' && <section className={styles.panel} aria-label="Research interpretation status"><p className="eyebrow">LOCAL DESCRIPTIVE SUMMARY</p><h2>AI Research Insights</h2><p className={styles.status}>Live Meta AI: unavailable in this demo</p><p>This read-only demonstration does not call an external model. Source permissions and provider access must be verified separately.</p>
        <h3>What the selected data show</h3><p><b>{familyPresentation(family).plainName} ({family}) · {name(selected)}:</b> the backend reports a synthetic region volume of <b>{selected.exact_value} mm³</b>.</p><p>This text is a local template using the selected backend measurement. It is not a live or saved Meta model result.</p><h3>What remains unknown</h3><p>There is no authentic patient anatomy, independently reviewed clinical interpretation or evidence of treatment benefit. A hypothetical change cannot establish diagnosis, response category or an individual outcome.</p><Link href={href({ view: 'twin' })}>Return to the selected 3D state →</Link></section>}
      {view === 'technical' && <section className={styles.panel}><h2>Evaluation and technical details</h2><p>This is a read-only snapshot prepared through the existing private mask, measurement, mesh and simulation pipeline. It contains five hypothetical families with four geometry states each.</p><dl><dt>Prepared</dt><dd>{new Date(catalog.preparedAt).toLocaleString()}</dd><dt>Scientific validation</dt><dd>Not established. Synthetic engineering demonstration only.</dd><dt>Geometry</dt><dd>RAS coordinates in millimeters; source-mask measurements remain authoritative.</dd><dt>Live integrations</dt><dd>No external inference. No authentic patient dataset or clinical source notes.</dd></dl><details><summary>Advanced identifiers and deterministic comparison evidence</summary><p>Branch: {current.timeline.window.scope.branch_id}<br/>Run: {current.timeline.window.scope.run_id}<br/>Selected state: {selected.state_ids.join(', ')}</p><TrendView report={current.trends} onSelect={id => { if (points.some(p => p.id === id)) navigate({ state: id }); }}/></details><p><Link href="/evaluation">Open the full evaluation workspace →</Link></p></section>}
      {!VIEWS.some(([id]) => id === view) && <section className={styles.panel}><h2>Choose a workspace section</h2><Link href={href({ view: 'twin' })}>Open the 3D Digital Twin</Link></section>}
      </>}
    </div>
  </div>;
}

function formatRecorded(recordedAt: string | null | undefined): string {
  if (!recordedAt) return 'Not recorded';
  const parsed = new Date(recordedAt);
  if (Number.isNaN(parsed.getTime())) return 'Not recorded';
  return `Artificial example recorded on ${parsed.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}.`;
}

function BaselineComparison({ points, selected }: { points: TimelinePoint[]; selected: TimelinePoint }) {
  const baseline = points.find(p => p.measurement_basis === 'baseline_reference');
  if (!baseline || baseline.id === selected.id) return null;
  const comparison = volumeComparison(baseline.exact_value, selected.exact_value);
  if (!comparison || selected.exact_value == null || baseline.exact_value == null) return null;
  return (
    <p role="status" data-testid="demo-comparison">
      Compared with this scenario&apos;s {baseline.exact_value} mm³ synthetic baseline, the selected region is {comparison} ({selected.exact_value} mm³).
    </p>
  );
}

function VolumeChart({ scenario, selected, onSelect }: { scenario: DemoScenario; selected: string; onSelect: (id: string) => void }) {  const series = scenario.trends.series.find(s => s.metric_definition === 'numerical_region_volume');
  const points = series?.points.filter(p => p.y !== null && p.x_elapsed_days !== null && !p.reason_codes.length) ?? [];
  if (!points.length) return <p>No compatible volume measurements are available for plotting.</p>;
  const maxX = Math.max(...points.map(p => Number(p.x_elapsed_days)), 1);
  const maxY = Math.max(...points.map(p => Number(p.y)), 1);
  const x = (value: string) => 70 + Number(value) / maxX * 680;
  const y = (value: string) => 190 - Number(value) / maxY * 140;
  return <figure className={styles.chart}><svg viewBox="0 0 800 250" role="img" aria-label="Synthetic region volume by relative day">
    <line x1="70" y1="190" x2="755" y2="190" stroke="#cbd5e1"/><line x1="70" y1="40" x2="70" y2="190" stroke="#cbd5e1"/>
    <text x="15" y="28">mm³</text><text x="400" y="240" textAnchor="middle">Days from synthetic baseline</text>
    {points.map((p, i) => <g key={p.point_id}>{i > 0 && series?.segments[i - 1]?.status === 'comparable' && <line x1={x(points[i - 1].x_elapsed_days!)} y1={y(points[i - 1].y!)} x2={x(p.x_elapsed_days!)} y2={y(p.y!)} stroke="#7c3aed" strokeWidth="2" strokeDasharray="5 5"/>}<circle cx={x(p.x_elapsed_days!)} cy={y(p.y!)} r={p.point_id === selected ? 8 : 5} fill={p.point_id === selected ? '#0f766e' : '#7c3aed'}/><text x={x(p.x_elapsed_days!)} y={y(p.y!) - 16} textAnchor="middle">{p.exact_value ?? p.y}</text><text x={x(p.x_elapsed_days!)} y="214" textAnchor="middle">{p.x_elapsed_days}</text></g>)}
  </svg><figcaption>Exact measured values. Dashed guides are not predictions or intermediate observations.</figcaption><div className={styles.chartLinks}>{points.map(p => <button key={p.point_id} aria-pressed={p.point_id === selected} onClick={() => onSelect(p.point_id)}>Day {p.x_elapsed_days}: {p.exact_value ?? p.y} mm³</button>)}</div></figure>;
}
