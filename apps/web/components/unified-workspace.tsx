'use client';
import { Suspense, useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import type { components } from '../../../packages/contracts/generated/api';
import { ErrorSummary, LoadingState } from './research';
import { ResearchProfile } from './research-profile';
import { ClinicalHistoryTable } from './clinical-history-table';
import { ClinicalChartsExplorer } from './clinical-charts-explorer';
import { ObservationIntake } from './observation-intake';
import { CaseImaging } from './case-imaging';
import { LesionViewer } from './lesion-viewer';
import { StateTimelineExplorer } from './state-timeline-explorer';

type S = components['schemas'];
type PatientDetail = S['PatientDetail'];
type VisitPage = S['VisitPage'];
type ClinicalRecord = S['ClinicalRecord'];

type Status = { kind: 'needs-selection' } | { kind: 'loading' } | { kind: 'failed'; message: string } | { kind: 'ready' };
type TabId = 'overview' | 'clinical' | 'charts' | 'imaging' | 'timeline';

function useSelection(): { project: string | null; patient: string | null; tab: TabId } {
  const params = useSearchParams();
  const raw = params.get('tab');
  const normalized = raw === 'twin' ? 'imaging' : raw;
  const tab: TabId = ['overview','clinical','charts','imaging','timeline'].includes(normalized ?? '') ? (normalized as TabId) : 'overview';
  return { project: params.get('project'), patient: params.get('patient'), tab };
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try { return JSON.parse(text) as unknown; } catch { return { raw: text.slice(0,500)}; }
}
function explain(response: Response): string {
  if (response.status === 401) return 'Sign in with an authorized session, then retry. Your session may have expired.';
  if (response.status === 403) return 'This case or action is restricted for your role. Ask your administrator for access.';
  if (response.status === 404) return 'The case is not available to your account. Check that you selected the correct project.';
  if (response.status === 409) return 'The record or revision changed. Reload the case before retrying.';
  if (response.status === 412) return 'The case revision changed while editing. Reload before retrying.';
  if (response.status === 422) return 'A field value was rejected. Check values, units and dates.';
  return `Request failed (status ${response.status}).`;
}

export function UnifiedWorkspace() {
  return <Suspense fallback={<LoadingState/>}><UnifiedWorkspaceBody/></Suspense>;
}

function UnifiedWorkspaceBody() {
  const { project, patient, tab: initialTab } = useSelection();
  const [tab, setTab] = useState<TabId>(initialTab);
  const [status, setStatus] = useState<Status>(()=> project && patient ? { kind:'loading' } : { kind:'needs-selection'});
  const [detail, setDetail] = useState<PatientDetail | null>(null);
  const [sourceOrigin, setSourceOrigin] = useState<'real_source'|'synthetic_engineering_fixture'|null>(null);
  const [canWrite, setCanWrite] = useState(false);
  const [visits, setVisits] = useState<VisitPage | null>(null);
  const [message, setMessage] = useState('Loading research case…');
  const [correction, setCorrection] = useState<ClinicalRecord|null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const pending = useRef<AbortController|null>(null);
  useEffect(()=>()=>{ pending.current?.abort(); }, []);

  const load = useCallback(async () => {
    if (!project || !patient) { setStatus({kind:'needs-selection'}); return; }
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setStatus({kind:'loading'});
    try {
      const detailRes = await fetch(`/api/case-detail?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`, { cache:'no-store', signal: controller.signal });
      if (!detailRes.ok) throw new Error(explain(detailRes));
      const detailBody = await readJson(detailRes) as PatientDetail;
      const visitRes = await fetch(`/api/case-visits?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`, { cache:'no-store', signal: controller.signal });
      if (!visitRes.ok) throw new Error(explain(visitRes));
      const visitBody = await readJson(visitRes) as VisitPage;
      if (controller.signal.aborted) return;
      setDetail(detailBody);
      setVisits(visitBody);
      setStatus({kind:'ready'});
      setMessage(`Research case loaded · ${detailBody.observation_count} observations in ${detailBody.visit_count} visits. Session will persist after refresh via secure cookie + last-case local storage.`);
      try { localStorage.setItem('canceros:last_case', JSON.stringify({project, patient, at:Date.now()})); } catch {}
    } catch (e) {
      if (controller.signal.aborted) return;
      setStatus({kind:'failed', message: e instanceof Error ? e.message : 'The case could not load.'});
    }
  }, [project, patient]);

  useEffect(()=>{
    const controller = new AbortController();
    pending.current?.abort();
    pending.current = controller;
    void (async () => {
      if (!project || !patient) { setStatus({kind:'needs-selection'}); return; }
      try { await load(); } catch { /* load reports its own status */ }
    })();
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, refreshKey]);

  function navigateTab(next: TabId) {
    setTab(next);
    const url = new URL(window.location.href);
    url.searchParams.set('tab', next);
    url.searchParams.delete('lesion');
    window.history.replaceState(null, '', url.toString());
  }

  if (!project || !patient) {
    return <section className="card">
      <h2>Select a research case</h2>
      <p>Open a case from the <Link href="/cases">research case library</Link>. The workspace keeps your project selection in secure cookie and restores the last case from local storage after refresh — no UUID typing required.</p>
      <p className="field-hint">If you arrived here directly, you need project and patient identifiers in the URL: <code>?project=&lt;id&gt;&amp;patient=&lt;id&gt;</code>. Use the case library to generate those automatically by clicking “Open case”.</p>
      <p><Link className="button-primary" href="/cases">Go to case library</Link> <Link className="button-secondary" href="/demo">Explore synthetic demo without token</Link></p>
    </section>;
  }
  if (status.kind === 'loading') return <LoadingState/>;
  if (status.kind === 'failed') return <section className="card"><ErrorSummary message={status.message}/><p><button className="button-secondary" onClick={()=>setRefreshKey(k=>k+1)}>Retry loading case</button> <Link className="button-ghost" href={`/cases?project=${encodeURIComponent(project)}`}>Back to library</Link></p></section>;
  if (!detail) return <LoadingState/>;

  const tabs: {id:TabId; label:string; hint:string}[] = [
    {id:'overview', label:'Overview & Profile', hint:'Research profile, source, completeness'},
    {id:'clinical', label:'Clinical Records', hint:'History, add observations, corrections'},
    {id:'charts', label:'Charts', hint:'Lab small multiples, vitals, symptoms'},
    {id:'imaging', label:'Imaging & 3D', hint:'Studies, sources, and authorized case viewer'},
    {id:'timeline', label:'Timeline', hint:'Persisted states with baseline pinning and A/B compare'},
  ];

  return <>
    <div className="card" style={{display:'flex', flexWrap:'wrap', gap:12, justifyContent:'space-between', alignItems:'center', position:'sticky', top:0, zIndex:2}}>
      <div>
        <p className="eyebrow" style={{margin:0}}>RESEARCH CASE · {detail.display_code ?? detail.patient_id.slice(0,8)}</p>
        <p role="status" aria-live="polite" style={{margin:0, fontSize:14, color:'var(--muted)'}}>{message}</p>
        <p className="field-hint" style={{margin:'4px 0 0'}}>Reopening after refresh works — last selection stored locally, auth via secure httpOnly cookie. No UUID entry required.</p>
      </div>
      <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
        <Link className="button-ghost" href={`/cases?project=${encodeURIComponent(project)}`}>← Case library</Link>
        <button className="button-ghost" onClick={()=>setRefreshKey(k=>k+1)}>Reload case</button>
      </div>
    </div>

    <div className="case-nav" style={{marginTop:16, borderRadius:12, background:'#fff', border:'1px solid var(--border)', padding:'8px 12px'}} aria-label="Workspace tabs">
      <ul className="nav-list" role="tablist">
        {tabs.map(t=> <li key={t.id}><button role="tab" aria-selected={tab===t.id} className={tab===t.id ? 'button-secondary' : 'button-ghost'} style={{minHeight:36, padding:'8px 14px', fontSize:13}} onClick={()=>navigateTab(t.id)} title={t.hint}>{t.label}</button></li>)}
      </ul>
    </div>

    {tab==='overview' && <>
      <section className="intro" style={{marginTop:20}}><h2>Research profile & source completeness</h2><p className="lead" style={{fontSize:16}}>Source-backed facts only. Missing values stay “Not recorded”. Synthetic descendants stay simulated. Revision history retained.</p></section>
      <ResearchProfile project={project} patient={patient} onLoaded={(profile, editable)=>{ setSourceOrigin(profile.origin); setCanWrite(editable); }} />
      <section className="card" aria-label="Completeness" style={{marginTop:16}}>
        <h3>Completeness by capability</h3>
        <p className="field-hint">Describes record availability, not patient health or trust score.</p>
        <ul className="step-list">
          <li>Clinical records: {detail.observation_count} accepted, {detail.visit_count} visits</li>
          <li>Profile revision: {detail.data_revision} · data revision tracked with integrity hash</li>
        </ul>
        <p className="field-hint">Missing stays missing — never shown as zero. Restricted capabilities show “access restricted”.</p>
      </section>
      <section className="card" style={{marginTop:16}}>
        <h3>What you can do in this workspace</h3>
        <ol className="step-list">
          <li><strong>Overview</strong> (here) — review profile and completeness, edit if admin.</li>
          <li><strong>Clinical Records</strong> — view timeline, add source-backed observations, correct where permitted.</li>
          <li><strong>Charts</strong> — lab small multiples without interpolation, vitals, symptoms.</li>
          <li><strong>Imaging & 3D</strong> — authorized studies with the case viewer inline.</li>
          <li><strong>Timeline</strong> — persisted states with baseline pinning and A/B compare.</li>
        </ol>
        <p><button className="button-primary" onClick={()=>navigateTab('clinical')}>Continue to Clinical Records</button></p>
      </section>
    </>}

    {tab==='clinical' && <>
      <section className="intro" style={{marginTop:20}}><h2>Clinical observations & provenance</h2><p className="lead" style={{fontSize:16}}>Enter source-backed values only. Time, units, collection status preserved. Corrections append evidence.</p></section>
      <ClinicalHistoryTable key={`${detail.data_revision}:${refreshKey}`} project={project} patient={patient} onCorrect={canWrite?record=>{ setCorrection(record); setTimeout(()=>document.getElementById('case-observation-entry')?.scrollIntoView({behavior:'smooth'}),0); navigateTab('clinical'); }:undefined} />
      <div id="case-observation-entry" style={{marginTop:24}}>
        {sourceOrigin && canWrite ? <ObservationIntakeV2
          key={correction?.id ?? 'new-observation'}
          project={project} patient={patient} revision={detail.data_revision} origin={sourceOrigin}
          correction={correction}
          onCancelCorrection={()=>setCorrection(null)}
          onSaved={note=>{ setCorrection(null); setMessage(note); setRefreshKey(k=>k+1); }}
        /> : sourceOrigin ? <div className="card"><h3>Add observations requires editor permission</h3><p>Your current role cannot add observations to this case. An administrator or editor can. You can still view the timeline and charts.</p></div> : <div className="card"><p>Loading observation permissions…</p></div>}
      </div>
      <section className="card workspace-section" style={{marginTop:24}}>
        <h3>Visit history</h3>
        {visits && visits.items.length>0 ? <ul>{visits.items.map(v=> <li key={v.visit_id}>Visit {v.visit_id.slice(0,8)}… · {v.observation_count} observations · {v.time_basis}</li>)}</ul> : <p>No visits yet. Unknown-time records stay unplaced.</p>}
      </section>
    </>}

    {tab==='charts' && <>
      <section className="intro" style={{marginTop:20}}><h2>Clinical charts — no invented values</h2><p className="lead" style={{fontSize:16}}>Small multiples per concept+unit, missing and censored labeled, no gap filling or smoothing.</p></section>
      <p><button className="button-ghost" onClick={()=>navigateTab('clinical')}>← Back to Clinical Records</button></p>
      <ClinicalChartsExplorer key={`${project}:${patient}:${refreshKey}`} />
    </>}

    {tab==='imaging' && <>
      <section className="intro" style={{marginTop:20}}><h2>Imaging & 3D — authorized case viewer</h2><p className="lead" style={{fontSize:16}}>Authorized imaging studies linked to this case. Missing stays missing; DCE phases are not visits. The viewer below inherits this case — select an authorized lesion, no UUID entry needed.</p></section>
      <CaseImaging project={project} patient={patient}/>
      <section className="card" style={{marginTop:24}} aria-label="Authorized case 3D viewer">
        <h3>3D viewer for this case</h3>
        <p className="field-hint">Server mask measurements stay authoritative with a prominent overlay. The viewer inherits this case from the workspace.</p>
        <LesionViewer project={project} patient={patient} />
      </section>
      <section className="card" style={{marginTop:16}}>
        <h3>Need a reference without real data?</h3>
        <p>For a synthetic reference using the same viewer code, explore the demonstration.</p>
        <p><Link className="button-ghost" href="/demo?view=twin">Open synthetic 3D demo</Link></p>
      </section>
    </>}

    {tab==='timeline' && <>
      <section className="intro" style={{marginTop:20}}><h2>Timeline — persisted states and comparisons</h2><p className="lead" style={{fontSize:16}}>Branch picker, discrete state slider with list equivalent, persisted snapshot detail, and pinned A/B comparison. Observations and states stay separate tracks; nothing interpolates or autoplays.</p></section>
      <StateTimelineExplorer project={project} patient={patient} />
      <section className="card" style={{marginTop:16}}>
        <h3>Legacy observation timeline</h3>
        <p className="field-hint">The exact-window observation timeline remains available as a separate reference. It still requires its own authorized context and does not inherit this tab automatically.</p>
        <p><Link className="button-ghost" href={`/timeline?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`}>Open legacy observation timeline</Link> <Link className="button-ghost" href={`/states?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`}>Open states page</Link></p>
      </section>
    </>}
  </>;
}

function ObservationIntakeV2({ project, patient, revision, origin, onSaved, correction, onCancelCorrection }:
  { project:string; patient:string; revision:number; origin:'real_source'|'synthetic_engineering_fixture'; onSaved:(m:string)=>void; correction?:components['schemas']['ClinicalRecord']|null; onCancelCorrection?:()=>void }) {
  return <ObservationIntake project={project} patient={patient} revision={revision} origin={origin} onSaved={onSaved} correction={correction} onCancelCorrection={onCancelCorrection} />;
}
