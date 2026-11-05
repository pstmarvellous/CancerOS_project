'use client';
import { Suspense, useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import type { components } from '../../../packages/contracts/generated/api';
import { ResearchSessionPanel } from './research-session';
import { CaseCreator } from './case-creator';
import { CaseLibrary } from './case-library';
import { ErrorSummary, LoadingState } from './research';
import { researchJson, researchError } from '../lib/research-client';
type Case = components['schemas']['ResearchCaseView'];
type Source = components['schemas']['ResearchCaseSources']['items'][number];
export function ResearchCases() { return <Suspense fallback={<LoadingState/>}><ResearchCasesBody/></Suspense>; }
function readLastProject(): string | null {
  try { const raw = localStorage.getItem('canceros:last_case'); if (!raw) return null; const last = JSON.parse(raw); return typeof last?.project === 'string' ? last.project : null; } catch { return null; }
}
function ResearchCasesBody() {
  const params = useSearchParams();
  const [project, setProject] = useState<string|null>(()=> params.get('project') ?? (typeof window === 'undefined' ? null : readLastProject()));
  const [authenticated, setAuthenticated] = useState(false);
  const [role, setRole] = useState('');
  const [cases, setCases] = useState<Case[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState<string|null>(null);
  const [moreBusy, setMoreBusy] = useState(false);
  const [create, setCreate] = useState(false);
  const [showImported, setShowImported] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!project || !authenticated) return;
    const controller = new AbortController();
    void (async () => {
      setBusy(true); setError(''); setCases([]); setSources([]);
      try {
        const session = await researchJson<{projects: {project_id: string; role:string}[]}>('/api/research-session', {signal:controller.signal});
        const currentRole = session.projects.find(p => p.project_id === project)?.role ?? '';
        const page = await researchJson<{items: Case[];next_cursor?:string|null}>(`/api/research-cases?project=${encodeURIComponent(project)}`, {signal:controller.signal});
        const options = currentRole === 'admin' ? await researchJson<{items:Source[]}>(`/api/research-cases?project=${encodeURIComponent(project)}&view=sources`, {signal:controller.signal}) : {items:[]};
        if (!controller.signal.aborted) { setCases(page.items); setCursor(page.next_cursor??null); setSources(options.items); setRole(currentRole); }
      } catch (cause) { if (!controller.signal.aborted) setError(researchError(cause)); }
      finally { if (!controller.signal.aborted) setBusy(false); }
    })();
    return () => controller.abort();
  }, [project, authenticated, attempt]);
  async function loadMore() {
    if (!project||!cursor||moreBusy)return;setMoreBusy(true);
    try {
      const page=await researchJson<{items:Case[];next_cursor?:string|null}>(`/api/research-cases?project=${encodeURIComponent(project)}&cursor=${encodeURIComponent(cursor)}`);
      setCases(current=>[...current,...page.items.filter(item=>!current.some(existing=>existing.patient_id===item.patient_id))]);setCursor(page.next_cursor??null);
    }catch(cause){setError(researchError(cause));}finally{setMoreBusy(false);}
  }
  const shown = cases.filter(item => `${item.title} ${item.case_identifier} ${item.pseudonym}`.toLowerCase().includes(query.toLowerCase()));
  return <>
    <div id="research-access"><ResearchSessionPanel selectedProjectId={project} onProjectChange={next => {
      const prev = project;
      if (prev) try { localStorage.setItem('canceros:last_project', prev); } catch {}
      const toStore = next ?? '';
      try {
        if (toStore) localStorage.setItem('canceros:last_project', toStore);
        else if (!next) localStorage.removeItem('canceros:last_project');
      } catch {}
      setProject(next); setCases([]); setQuery(''); setShowImported(false);
    }} onSessionChange={setAuthenticated}/></div>

    {!authenticated && !busy && (
      <div className="research-choices" style={{marginTop:24}}>
        <section className="card"><p className="eyebrow">RESEARCH WORKSPACE</p><h2>Create Research Case</h2><p>Save a pseudonymized profile and source-backed observations within your authorized project. Requires admin role on a project with an eligible source.</p><button className="button-primary" onClick={() => document.getElementById('research-access')?.scrollIntoView({behavior:'smooth'})}>Sign in to start</button></section>
        <section className="card"><p className="eyebrow">NO TOKEN NEEDED</p><h2>Explore Synthetic Demonstration</h2><p>Explore five hypothetical scenarios and an interactive 3D engineering phantom without a credential — the complete CancerOS visualization flow.</p><Link className="button-secondary" href="/demo">Explore Synthetic Demonstration</Link> <Link className="button-ghost" href="/guided-demo" style={{marginLeft:8}}>Guided demo</Link></section>
      </div>
    )}

    {authenticated && project && <>
      {busy && <LoadingState/>}
      {error && <section className="card"><ErrorSummary message={error}/><button className="button-secondary" onClick={() => setAttempt(value => value+1)}>Retry loading workspace</button></section>}
      {!busy && !error && <>
        {/* Action bar — always visible */}
        <div className="card" style={{display:'flex', flexWrap:'wrap', gap:12, justifyContent:'space-between', alignItems:'center', marginBottom:16}}>
          <div><h2 style={{margin:0}}>Research cases for this project</h2><p className="field-hint" style={{margin:0}}>Role: <strong>{role || 'unknown'}</strong> · {cases.length} cases loaded{cases.length ? ' — click Open to enter the unified workspace' : ''}</p></div>
          <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
            <button className="button-ghost" onClick={() => setAttempt(v=>v+1)} disabled={busy}>Refresh cases</button>
            {role==='admin' && <button className="button-primary" onClick={()=>setCreate(v=>{const next=!v; if(next) setTimeout(()=>document.getElementById('new-case-form')?.scrollIntoView({behavior:'smooth'}),50); return next;})}>{create ? 'Close form' : 'New research case'}</button>}
          </div>
        </div>

        {create && <section id="new-case-form" className="card workspace-section" aria-label="New research case">
          <div className="section-heading"><h2>New research case</h2><button className="button-ghost" onClick={() => setCreate(false)}>Cancel</button></div>
          <CaseCreator key={project} project={project} sources={sources} allowed={role === 'admin'}/>
        </section>}

        <section className="workspace-section" aria-label="Saved research cases">
          <label className="search-field" style={{maxWidth:380, display:'flex', flexDirection:'column', gap:6}}>Search loaded cases
            <input type="search" value={query} onChange={event=>setQuery(event.target.value)} placeholder="Title, case identifier or pseudonym" />
          </label>
          <p className="field-hint">{shown.length} of {cases.length} loaded cases shown.{cursor?' More available below.':''} Source records stay separate from public synthetic demo.</p>
          {!cases.length ? <div className="card">
            <h3>No research cases yet</h3>
            {role==='admin' ? <>
              <p>Create your first case with an eligible source. If no source is eligible, your administrator must register a source and complete privacy review.</p>
              <button className="button-primary" onClick={()=>setCreate(true)}>Create first case</button>
            </> : <p>No cases are visible for your role yet. An administrator can create cases for this project. You can still explore the synthetic demonstration.</p>}
            <div style={{marginTop:12}}><Link className="button-secondary" href="/demo">Explore synthetic demo</Link></div>
          </div> : !shown.length ? <p>No loaded cases match “{query}”. <button className="button-ghost" onClick={()=>setQuery('')}>Clear search</button></p> : <div className="case-grid">{shown.map(item => <article className="card case-card" key={item.patient_id}>
            <span className={`badge ${item.origin === 'real_source' ? 'observed' : 'simulated'}`}>{item.origin === 'real_source' ? 'Research source' : 'Synthetic engineering record'}</span>
            <h3>{item.title}</h3><p className="muted" style={{fontSize:13, margin:'4px 0 8px'}}>{item.case_identifier} · {item.pseudonym}</p>
            <dl className="case-fields"><div><dt>Status</dt><dd>{item.status}</dd></div><div><dt>Updated</dt><dd>{new Date(item.updated_at).toLocaleDateString()}</dd></div><div><dt>Clinical records</dt><dd>{item.observation_count}</dd></div><div><dt>Imaging records</dt><dd>{item.imaging_count}</dd></div></dl>
            <Link className="button-secondary" href={`/cases/detail?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(item.patient_id)}`}>Open case</Link>
          </article>)}</div>}
          {cursor&&<button className="button-secondary" onClick={()=>void loadMore()} disabled={moreBusy} style={{marginTop:12}}>{moreBusy?'Loading…':'Load more cases'}</button>}
        </section>

        {role!=='admin' && cases.length>0 && <p className="field-hint">Only administrators can create cases. As {role}, you can open existing cases and add clinical observations where permitted.</p>}
      </>}
      <details className="card workspace-section" onToggle={event=>{if((event.target as HTMLDetailsElement).open)setShowImported(true);}} style={{marginTop:16}}><summary>Previously imported case summaries (legacy)</summary><p className="field-hint">Bounded list of imported patient records that may not yet have an editable research profile. Your patient grants apply.</p>{showImported&&<CaseLibrary key={project} initialProject={project}/>}</details>
    </>}
  </>;
}
