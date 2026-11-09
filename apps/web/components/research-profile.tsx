'use client';
import { useEffect, useRef, useState } from 'react';
import type { components } from '../../../packages/contracts/generated/api';
import { ErrorSummary, LoadingState } from './research';
import { researchJson, researchError } from '../lib/research-client';
type Profile = components['schemas']['ResearchCaseView'];

type ProfileProps = {project:string; patient:string; onLoaded?:(profile:Profile, canEdit:boolean)=>void};
export function ResearchProfile(props:ProfileProps) {
  return <ResearchProfileBody key={`${props.project}:${props.patient}`} {...props}/>;
}
function ResearchProfileBody({project, patient, onLoaded}:ProfileProps) {
  const [profile, setProfile] = useState<Profile|null>(null);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [canEdit, setCanEdit] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [key, setKey] = useState(()=>crypto.randomUUID());
  const loadedCallback = useRef(onLoaded);
  const active = useRef(true);
  useEffect(()=>{active.current=true; return ()=>{active.current=false;};},[]);
  useEffect(()=>{loadedCallback.current=onLoaded;},[onLoaded]);
  useEffect(() => {
    const controller = new AbortController();
    void (async()=>{
      try {
        const body = await researchJson<Profile>(`/api/research-profile?project=${project}&patient=${patient}`, {signal:controller.signal});
        const session = await researchJson<{projects:{project_id:string;role:string}[]}>('/api/research-session', {signal:controller.signal});
        if (!controller.signal.aborted) {const editable=session.projects.some(p=>p.project_id===project && p.role==='admin');setProfile(body); setError(''); setCanEdit(editable); loadedCallback.current?.(body,editable);}
      } catch(cause) {if (!controller.signal.aborted) setError(researchError(cause));}
    })();
    return ()=>controller.abort();
  }, [project,patient,attempt]);
  async function save(event:React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!profile || busy) return;
    const data = new FormData(event.currentTarget);
    const age = String(data.get('age')).trim();
    if (age && (!/^\d+$/.test(age) || !data.get('age_date'))) {setError('A source-supported age requires whole years and an observation date.'); return;}
    const body = {expected_profile_revision:profile.profile_revision, case_identifier:String(data.get('identifier')).trim(), title:String(data.get('title')).trim(),pseudonym:String(data.get('pseudonym')).trim(), status:data.get('status'), sex:data.get('sex'), age_at_observation:age ? Number(age) : null, age_observed_on:age ? data.get('age_date') : null, profile_source_reference:String(data.get('reference')).trim(), medical_history:String(data.get('history')).trim() || null};
    setBusy(true); setError(''); setNotice('');
    try {
      const result = await researchJson<Profile>(`/api/research-profile?project=${project}&patient=${patient}`,{method:'POST',headers:{'content-type':'application/json','idempotency-key':key},body:JSON.stringify(body)});
      if (!active.current) return;
      loadedCallback.current?.(result,canEdit);
      setProfile(result); setEditing(false); setKey(crypto.randomUUID()); setNotice('Profile saved. Previous revisions are retained.');
    } catch(cause) {if (active.current) setError(researchError(cause));} finally {if (active.current) setBusy(false);}
  }
  return <section className="card workspace-section" aria-label="Research profile editor">
    <div className="section-heading"><div><h2>Research profile</h2><p className="field-hint" style={{margin:0}}>Pseudonymized, source-backed. Revision history retained; missing stays “Not recorded”.</p></div>
      {profile && canEdit && !editing && <button className="button-secondary" onClick={()=>{setEditing(true);setNotice('');}}>Edit profile</button>}</div>
    {error && <><ErrorSummary message={error}/><button className="button-ghost" onClick={()=>setAttempt(n=>n+1)} style={{marginTop:8}}>Reload saved profile</button></>}
    {!profile && !error && <LoadingState/>}
    {notice && <p role="status" className="field-hint" style={{background:'#ecfdf5', border:'1px solid #a7f3d0', padding:12, borderRadius:8}}>{notice}</p>}
    {profile && !editing && <>
      <div style={{display:'flex', flexWrap:'wrap', gap:8, alignItems:'center', marginBottom:12}}>
        <h3 style={{margin:0}}>{profile.title}</h3>
        <span className={`badge ${profile.origin==='real_source'?'observed':'simulated'}`}>{profile.origin==='real_source'?'Source-backed research record':'Synthetic engineering record'}</span>
        <span className="badge warning">Revision {profile.profile_revision}</span>
        <span className="badge">{profile.status}</span>
      </div>
      <dl className="profile-facts" style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))', gap:12}}>
        <div><dt>Case identifier</dt><dd>{profile.case_identifier}</dd></div>
        <div><dt>Pseudonym</dt><dd>{profile.pseudonym}</dd></div>
        <div><dt>Status</dt><dd>{profile.status}</dd></div>
        <div><dt>Sex</dt><dd>{profile.sex.replaceAll('_',' ')}</dd></div>
        <div><dt>Age</dt><dd>{profile.age_at_observation==null?'Not recorded':`${profile.age_at_observation} years · ${profile.age_observed_on}`}</dd></div>
        <div style={{gridColumn:'1 / -1'}}><dt>Medical history</dt><dd>{profile.medical_history || 'Not recorded — use clinical note for detailed history'}</dd></div>
        <div style={{gridColumn:'1 / -1'}}><dt>Source reference</dt><dd>{profile.profile_source_reference}</dd></div>
        <div><dt>Created</dt><dd>{new Date(profile.created_at).toLocaleString()}</dd></div>
        <div><dt>Updated</dt><dd>{new Date(profile.updated_at).toLocaleString()}</dd></div>
      </dl>
      <p className="field-hint" style={{marginTop:12}}>Cancer findings (ER/PR/HER2, stage) belong in source-backed diagnosis observations — not here — to preserve provenance and missingness.</p>
    </>}
    {profile && editing && <form aria-label="Edit research profile" onSubmit={save} onChange={()=>setKey(crypto.randomUUID())}>
      <fieldset disabled={busy} style={{border:0, padding:0}}>
        <legend style={{fontWeight:700, marginBottom:8}}>Edit source-supported profile</legend>
        <p className="field-hint">Unknown fields remain “Not recorded”. Case identifier and pseudonym are immutable after creation; edits create new revision retaining original link.</p>
        <div className="form-grid">
          <label>Case identifier (immutable)<input name="identifier" readOnly required maxLength={80} pattern={'[A-Za-z0-9._\\-]+'} defaultValue={profile.case_identifier}/><span className="field-hint">Cannot be changed after creation.</span></label>
          <label>Pseudonym (immutable)<input name="pseudonym" readOnly required maxLength={100} defaultValue={profile.pseudonym}/></label>
          <label>Case title *<input name="title" required maxLength={200} defaultValue={profile.title} placeholder="Longitudinal research case title"/><span className="field-hint">Clear title for library listing.</span></label>
          <label>Status<select name="status" defaultValue={profile.status}>{['draft','active','archived'].map(value=><option key={value} value={value}>{value}</option>)}</select></label>
          <label>Sex as documented<select name="sex" defaultValue={profile.sex}>{['not_recorded','unknown','female','male','intersex'].map(value=><option key={value} value={value}>{value.replaceAll('_',' ')}</option>)}</select></label>
          <label>Age at observation (years, source only)<input type="number" name="age" aria-label="Age at observation" min="0" max="150" step="1" defaultValue={profile.age_at_observation ?? ''} placeholder="e.g., 54"/></label>
          <label>Age observed on<input type="date" name="age_date" aria-label="Age observed on" defaultValue={profile.age_observed_on ?? ''}/><span className="field-hint">Required if age entered.</span></label>
          <label style={{gridColumn:'1 / -1'}}>Source reference *<input name="reference" required maxLength={500} defaultValue={profile.profile_source_reference} placeholder="Study register / entry"/><span className="field-hint">Locator supporting this profile.</span></label>
          <label style={{gridColumn:'1 / -1'}}>Documented medical history<textarea name="history" aria-label="Documented medical history" rows={3} maxLength={3000} defaultValue={profile.medical_history ?? ''} placeholder="Source-supported summary, no identifiers; detailed notes use clinical note form"/><span className="field-hint">Omit names, contact details, government IDs.</span></label>
        </div>
      </fieldset>
      <div style={{display:'flex', gap:8, marginTop:12}}><button className="button-primary" disabled={busy}>{busy?'Saving…':'Save profile revision'}</button><button className="button-ghost" type="button" disabled={busy} onClick={()=>{setEditing(false);setError('');}}>Cancel</button></div>
    </form>}
  </section>;
}
