'use client';
import { useEffect, useRef, useState } from 'react';
import type { components } from '../../../packages/contracts/generated/api';
import { ErrorSummary, LoadingState } from './research';
import { researchJson, researchError } from '../lib/research-client';
type Profile = components['schemas']['ResearchCaseView'];

export function ResearchProfile({project, patient, onLoaded}: {project:string; patient:string; onLoaded?:(profile:Profile, canEdit:boolean)=>void}) {
  const [profile, setProfile] = useState<Profile|null>(null);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [canEdit, setCanEdit] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [attempt, setAttempt] = useState(0);
  const [key, setKey] = useState(()=>crypto.randomUUID());
  const loadedCallback = useRef(onLoaded);
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
      setProfile(result); setEditing(false); setKey(crypto.randomUUID()); setNotice('Profile saved. Previous revisions are retained.');
    } catch(cause) {setError(researchError(cause));} finally {setBusy(false);}
  }
  return <section className="card workspace-section" aria-label="Research profile editor">
    <div className="section-heading"><h2>Research profile</h2>{profile && canEdit && !editing && <button className="button-secondary" onClick={()=>{setEditing(true);setNotice('');}}>Edit research profile</button>}</div>
    {error && <><ErrorSummary message={error}/><button className="button-ghost" onClick={()=>setAttempt(n=>n+1)}>Reload saved profile</button></>}
    {!profile && !error && <LoadingState/>}
    {notice && <p role="status">{notice}</p>}
    {profile && !editing && <>
      <h3>{profile.title}</h3><span className={`badge ${profile.origin==='real_source'?'observed':'simulated'}`}>{profile.origin==='real_source'?'Source-backed research record':'Synthetic engineering record'}</span>
      <dl className="profile-facts"><div><dt>Case identifier</dt><dd>{profile.case_identifier}</dd></div><div><dt>Pseudonym</dt><dd>{profile.pseudonym}</dd></div><div><dt>Status</dt><dd>{profile.status}</dd></div><div><dt>Sex</dt><dd>{profile.sex.replaceAll('_',' ')}</dd></div><div><dt>Age at observation</dt><dd>{profile.age_at_observation==null?'Not recorded':`${profile.age_at_observation} years · ${profile.age_observed_on}`}</dd></div><div><dt>Medical history</dt><dd>{profile.medical_history || 'Not recorded'}</dd></div><div><dt>Profile source</dt><dd>{profile.profile_source_reference}</dd></div><div><dt>Created / updated</dt><dd>{new Date(profile.created_at).toLocaleString()} / {new Date(profile.updated_at).toLocaleString()}</dd></div></dl>
      <p className="field-hint">Profile revision {profile.profile_revision}. Cancer findings belong in source-backed diagnosis observations below.</p>
    </>}
    {profile && editing && <form aria-label="Edit research profile" onSubmit={save} onChange={()=>setKey(crypto.randomUUID())}><fieldset disabled={busy}><legend>Source-supported research profile</legend><p className="field-hint">Unknown fields remain not recorded. Required fields are marked *. Case identity and source pseudonym are fixed; corrections retain their original linkage.</p><div className="form-grid">
      <label>Research case identifier *<input name="identifier" readOnly required maxLength={80} pattern={'[A-Za-z0-9._\\-]+'} defaultValue={profile.case_identifier}/></label>
      <label>Case title *<input name="title" required maxLength={200} defaultValue={profile.title}/></label>
      <label>Research pseudonym *<input name="pseudonym" readOnly required maxLength={100} defaultValue={profile.pseudonym}/></label>
      <label>Case status<select name="status" defaultValue={profile.status}>{['draft','active','archived'].map(value=><option key={value}>{value}</option>)}</select></label>
      <label>Sex as documented<select name="sex" defaultValue={profile.sex}>{['not_recorded','unknown','female','male','intersex'].map(value=><option key={value} value={value}>{value.replaceAll('_',' ')}</option>)}</select></label>
      <label>Age at observation (years)<input type="number" name="age" min="0" max="150" step="1" defaultValue={profile.age_at_observation ?? ''}/><span className="field-hint">Source age only; leave blank if not recorded.</span></label>
      <label>Age observation date<input type="date" name="age_date" defaultValue={profile.age_observed_on ?? ''}/></label>
      <label>Profile source reference *<input name="reference" required maxLength={500} defaultValue={profile.profile_source_reference}/></label>
      <label className="field-wide">Documented medical history<textarea name="history" rows={3} maxLength={3000} defaultValue={profile.medical_history ?? ''}/><span className="field-hint">A source-supported research summary. Omit direct identifiers. Detailed source notes use the clinical notes form.</span></label>
    </div></fieldset><div className="actions"><button className="button-primary" disabled={busy}>{busy?'Saving…':'Save profile'}</button><button className="button-ghost" type="button" disabled={busy} onClick={()=>{setEditing(false);setError('');}}>Cancel editing</button></div></form>}
  </section>;
}
