'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import type { components } from '../../../packages/contracts/generated/api';
import { researchJson, researchError } from '../lib/research-client';
import { ErrorSummary } from './research';
type Source = components['schemas']['ResearchCaseSources']['items'][number];

export function CaseCreator({project, sources, allowed}: {project: string; sources: Source[]; allowed: boolean}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [key, setKey] = useState(() => crypto.randomUUID());
  const eligible = sources.filter(source => source.creation_permitted);
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
      if (![body.case_identifier, body.title, body.pseudonym, body.profile_source_reference].every(Boolean)) throw new Error('Complete the required case information.');
      const result = await researchJson<{patient_id: string}>(`/api/research-cases?project=${encodeURIComponent(project)}`, {
        method: 'POST', headers: {'content-type':'application/json','idempotency-key':key}, body: JSON.stringify(body),
      });
      router.push(`/cases/detail?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(result.patient_id)}`);
    } catch (cause) { setError(researchError(cause)); setBusy(false); }
  }
  if (!allowed) return <p role="note">Case creation requires a project administrator. You can still open cases granted to your role.</p>;
  if (!eligible.length) return <p role="note">No source is eligible for case creation. An administrator must register a source and record the applicable rights and privacy review. Your existing cases remain available.</p>;
  return <form aria-label="Create research case" onSubmit={submit} onChange={() => setKey(crypto.randomUUID())}>
    <p className="field-hint">Required fields are marked *. Use research labels; omit names, contact details and government identifiers.</p>
    <fieldset disabled={busy}>
      <legend>Case information</legend>
      <div className="form-grid">
        <label>Research case identifier *<input name="identifier" required maxLength={80} pattern={'[A-Za-z0-9._\\-]+'} placeholder="STUDY-042" autoComplete="off"/><span className="field-hint">Unique within this project. Letters, numbers, dots, hyphens and underscores.</span></label>
        <label>Case title *<input name="title" required maxLength={200} placeholder="Longitudinal research case"/></label>
        <label>Source research pseudonym *<input name="pseudonym" required maxLength={100} placeholder="Participant 042" autoComplete="off"/><span className="field-hint">Use the study&apos;s pseudonym to prevent duplicate source linkage.</span></label>
        <label>Source *<select name="source" required>{eligible.map(source => <option key={source.source_version_id} value={source.source_version_id}>{source.title} · {source.origin === 'real_source' ? 'Research source' : 'Synthetic engineering source'}</option>)}</select></label>
        <label>Profile source reference *<input name="reference" required maxLength={500} placeholder="Study register / entry 042"/><span className="field-hint">A source locator or reference supporting this research profile.</span></label>
      </div>
    </fieldset>
    {error && <ErrorSummary message={error}/>}
    <button className="button-primary" type="submit" disabled={busy}>{busy ? 'Saving case…' : 'Save research case'}</button>
  </form>;
}
