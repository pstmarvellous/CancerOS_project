'use client';
import { rememberCase } from '../lib/case-selection';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { components } from '../../../packages/contracts/generated/api';
import { researchJson, researchError } from '../lib/research-client';
import { ErrorSummary } from './research';
import { TermHelp } from './term-help';
const RECORD_TYPE_HELP = ['Case reference', 'Participant code', 'Source record', 'Source reference', 'Record type'] as const;
type Source = components['schemas']['ResearchCaseSources']['items'][number];

export function CaseCreator({project, sources, allowed}: {project: string; sources: Source[]; allowed: boolean}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [key, setKey] = useState(() => crypto.randomUUID());
  const eligible = sources.filter(source => source.creation_permitted);
  const hasIneligible = sources.some(s => !s.creation_permitted);
  const [sourceId, setSourceId] = useState<string>(eligible[0]?.source_version_id ?? '');
  const selectedSource = eligible.find(source => source.source_version_id === sourceId) ?? eligible[0] ?? null;
  const recordType = selectedSource == null ? null : selectedSource.origin === 'real_source' ? 'Source-backed research record' : 'Artificial demonstration';
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || !allowed) return;
    const data = new FormData(event.currentTarget);
    setBusy(true); setError('');
    try {
      const body = {
        source_version_id: data.get('source'), case_identifier: String(data.get('identifier')).trim(),
        title: String(data.get('title')).trim(), pseudonym: String(data.get('pseudonym')).trim(),
        status: 'draft', sex: 'not_recorded', age_at_observation: null, age_observed_on: null,
        profile_source_reference: String(data.get('reference')).trim(), medical_history: null,
      };
      if (![body.case_identifier, body.title, body.pseudonym, body.profile_source_reference].every(Boolean)) throw new Error('Complete required fields: identifier, title, pseudonym, source reference.');
      if (!body.case_identifier.match(/^[A-Za-z0-9._-]+$/)) throw new Error('Case identifier may contain only letters, numbers, dots, hyphens, underscores.');
      const result = await researchJson<{patient_id: string}>(`/api/research-cases?project=${encodeURIComponent(project)}`, {
        method: 'POST', headers: {'content-type':'application/json','idempotency-key':key}, body: JSON.stringify(body),
      });
      rememberCase(project, result.patient_id);
      router.push(`/cases/detail?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(result.patient_id)}`);
    } catch (cause) { setError(researchError(cause)); setBusy(false); }
  }
  if (!allowed) return <div className="card" style={{padding:16}}><h3>Admin role required</h3><p role="note">Case creation requires project administrator role. You can still open cases assigned to your role and add observations where permitted. Ask your administrator to elevate your role or to create the case for you.</p></div>;
  if (!eligible.length) return <div className="card" style={{padding:16}}>
    <h3>No eligible source for case creation</h3>
    <p role="note">No source in this project is eligible for case creation.</p>
    <ul className="step-list">
      <li>Ask your administrator to register a source artifact and complete internal + privacy reviews.</li>
      <li>Check that linkage key is configured (<code>linkage_active_key</code> in server config).</li>
      <li>Ensure your project membership role is admin.</li>
    </ul>
    {hasIneligible && <>
      <p className="field-hint">Existing sources in this project:</p>
      <ul>{sources.map(s=> <li key={s.source_version_id}>{s.title} · {s.origin} — not eligible: {s.reason}</li>)}</ul>
    </>}
    <p className="field-hint">Your existing cases remain available below. For local development, create source via admin bootstrap script in <code>scripts/</code>.</p>
  </div>;
  return <form aria-label="Create research case" onSubmit={submit} onChange={() => setKey(crypto.randomUUID())}>
    <p className="field-hint">Required fields *. Use research labels only — no real names, contact details, or government IDs. Letters/numbers/dot/hyphen/underscore only for the reference.</p>
    <dl className="profile-facts" style={{display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))', gap:12, margin:'0 0 16px'}}>
      <div><dt>Research project</dt><dd>Currently selected project — the case is created here and nowhere else.</dd></div>
      <div><dt>Record type</dt><dd>{recordType ?? 'Determined by the selected source below.'}{recordType === 'Artificial demonstration' ? ' Entries in this case are labeled synthetic, never authentic.' : ''}</dd></div>
    </dl>
    <fieldset disabled={busy} style={{border:0, padding:0, display:'grid', gap:16, gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))'}}>
      <label style={{display:'flex', flexDirection:'column', gap:6}}>Case title *<input name="title" required maxLength={200} placeholder="Breast Cancer Research Example A"/><span className="field-hint">Displayed in the library.</span></label>
      <label style={{display:'flex', flexDirection:'column', gap:6}}>Case reference *<input name="identifier" required maxLength={80} pattern={'[A-Za-z0-9._\\-]+'} placeholder="DEMO-001" autoComplete="off"/><span className="field-hint">Unique within the project. Example: DEMO-001</span></label>
      <label style={{display:'flex', flexDirection:'column', gap:6}}>Participant code *<input name="pseudonym" required maxLength={100} placeholder="Participant 042" autoComplete="off"/><span className="field-hint">Study code that prevents duplicate linkage — never a real name.</span></label>
      <label style={{display:'flex', flexDirection:'column', gap:6}}>Source record *<select name="source" required value={selectedSource?.source_version_id ?? ''} onChange={event => setSourceId(event.target.value)}>{eligible.map(source => <option key={source.source_version_id} value={source.source_version_id}>{source.title} · {source.origin === 'real_source' ? 'Research source' : 'Artificial demonstration source'}</option>)}</select><span className="field-hint">Only eligible sources shown. The record type above follows this choice.</span></label>
      <label style={{display:'flex', flexDirection:'column', gap:6, gridColumn:'1 / -1'}}>Source reference *<input name="reference" required maxLength={500} placeholder="Study register / entry 042"/><span className="field-hint">Locator supporting this profile (page, entry, report).</span></label>
    </fieldset>
    {error && <div style={{marginTop:12}}><ErrorSummary message={error}/></div>}
    <div style={{marginTop:16, display:'flex', gap:8}}><button className="button-primary" type="submit" disabled={busy}>{busy ? 'Saving case…' : 'Create Case'}</button></div>
    <p className="field-hint" style={{marginTop:8}}>Saving creates an immutable case binding with idempotency key and opens the saved case overview. Reopen after refresh via stored selection, no UUID typing.</p>
    <TermHelp terms={[...RECORD_TYPE_HELP]} />
  </form>;
}
