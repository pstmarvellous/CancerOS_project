'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import type { components } from '../../../packages/contracts/generated/api';
import styles from './simulation-workflow.module.css';

type Schema = components['schemas'];
type Config = Schema['SimulationConfig'];
type Saved = Schema['ConfigVersion'];
type Branch = Schema['BranchReport'];
type Run = Schema['SimulationRun'];
type Preview = Schema['SampledObservations'];
type Eligibility = Schema['EligibilityReport'];
type Completion = Schema['CompletionReport'];
type Job = Schema['ImagingJobRecord'];
type Current = Schema['CurrentRunView'];
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const FAMILY: Record<string, string> = {'SC-01': 'Strong simulated reduction', 'SC-02': 'Modest reduction or near stable', 'SC-03': 'Increasing simulated burden', 'SC-04': 'Decline followed by regrowth', 'SC-05': 'Independent clinical deterioration'};
const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';

export function SimulationWorkflow() {
  const [project, setProject] = useState(''); const [patient, setPatient] = useState('');
  const [branchId, setBranchId] = useState(''); const [token, setToken] = useState('');
  const [branch, setBranch] = useState<Branch | null>(null);
  const [draft, setDraft] = useState('{}'); const [revision, setRevision] = useState('0'); const [configId, setConfigId] = useState('');
  const [saved, setSaved] = useState<Saved | null>(null); const [preview, setPreview] = useState<Preview | null>(null);
  const [eligibility, setEligibility] = useState<Eligibility | null>(null); const [run, setRun] = useState<Run | null>(null);
  const [job, setJob] = useState<Job | null>(null); const [completion, setCompletion] = useState<Completion | null>(null);
  const [current, setCurrent] = useState<string | null>(null); const [currentView, setCurrentView] = useState<Current | null>(null); const [attestation, setAttestation] = useState('');
  const [reviewed, setReviewed] = useState(false); const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('Load an authorized branch, then enter an explicit simulation configuration.');
  const pending = useRef<AbortController | null>(null);
  const retries = useRef(new Map<string, string>());
  useEffect(() => () => pending.current?.abort(), []);
  function resetResults() {setSaved(null); setPreview(null); setEligibility(null); setRun(null); setJob(null); setCompletion(null); setReviewed(false);}
  function contextChanged() {pending.current?.abort(); setBusy(false); setBranch(null); setCurrent(null); setCurrentView(null); resetResults(); retries.current.clear(); setMessage('Context changed. Reload the branch. The editable draft is preserved.');}
  async function request<T>(path: string, signal: AbortSignal, body?: unknown): Promise<T> {
    const headers: Record<string, string> = {Authorization: `Bearer ${token.trim()}`};
    let key: string | undefined;
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json'; key = `${project}/${patient}${path}:${JSON.stringify(body)}`;
      if (!retries.current.has(key)) retries.current.set(key, crypto.randomUUID());
      headers['Idempotency-Key'] = retries.current.get(key)!;
    }
    const response = await fetch(`${API}/api/v1/projects/${project}/patients/${patient}${path}`, {method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body), signal, cache: 'no-store', credentials: 'omit', redirect: 'error'});
    if (!response.ok) {
      const messages: Record<number, string> = {401: 'Access denied. Check the authorized token.', 403: 'Access denied for this project, patient or action.', 404: 'Record unavailable in this context. Check identifiers.', 409: 'Current permissions, revision, draft or scientific gates block this action. Reload the branch and inspect the saved assumptions. Your draft is preserved.', 422: 'Configuration rejected. Check required fields, units, family parameters and schedule. Your draft is preserved.'};
      throw new Error(messages[response.status] || 'The API request failed. Check the local service and retry the same action.');
    }
    const result: T = await response.json();
    if (key) retries.current.delete(key);
    return result;
  }
  async function act(action: (signal: AbortSignal) => Promise<void>) {
    if (![project, patient, branchId].every(value => UUID.test(value)) || !token.trim()) {setMessage('Enter valid project, patient and branch UUIDs and an authorized administrator token.'); return;}
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller; setBusy(true);
    try {await action(controller.signal);} catch (error) {if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : 'Request failed. Your draft is preserved.');}
    finally {if (!controller.signal.aborted) setBusy(false);}
  }
  async function load(signal: AbortSignal) {
    const value = await request<Branch>(`/branches/${branchId}`, signal);
    if (value.id !== branchId) throw new Error('Returned branch does not match the selected context.');
    const pointer = await request<Current>(`/branches/${branchId}/current-simulation`, signal);
    setBranch(value); setCurrent(pointer.publication?.run_id ?? null); setCurrentView(pointer); resetResults();
    setMessage('Branch loaded. The baseline is an unverified engineering fixture. Enter explicit assumptions; no clinical defaults are supplied.');
  }
  async function save(signal: AbortSignal) {
    let config: Config;
    try {config = JSON.parse(draft) as Config;} catch {throw new Error('Draft is not valid JSON. Correct it and save again.');}
    if (!config || config.branch_id !== branchId || config.baseline_hash !== branch?.baseline_hash) throw new Error('Draft branch and baseline hash must match the loaded branch.');
    if (config.treatment?.category !== 'no_specific_assumption') throw new Error('Specific treatment assumptions remain disabled pending qualified policy review.');
    const expected = Number(revision);
    if (!Number.isSafeInteger(expected) || expected < 0) throw new Error('Enter a nonnegative expected draft revision.');
    const value = await request<Saved>(`/branches/${branchId}/simulation-configs`, signal, {expected_draft_revision: expected, config});
    setSaved(value); setRevision(String(value.draft_revision)); setRun(null); setCompletion(null); setJob(null); setPreview(null); setEligibility(null); setReviewed(false);
    setMessage('Immutable draft version saved. Inspect eligibility and the sampled schedule before freezing.');
  }
  async function resumeDraft(signal: AbortSignal) {
    if (!UUID.test(configId)) throw new Error('Enter a valid saved configuration UUID.');
    const value = await request<Saved>(`/simulation-configs/${configId}`, signal);
    if (value.branch_id !== branchId || value.config.baseline_hash !== branch?.baseline_hash) throw new Error('Saved configuration belongs to a different branch or baseline. Your draft is preserved.');
    resetResults(); setSaved(value); setDraft(JSON.stringify(value.config, null, 2)); setRevision(String(value.draft_revision));
    setMessage('Saved immutable configuration loaded. Inspect eligibility and the sampled schedule again; current permissions are checked by the server.');
  }
  async function inspect(signal: AbortSignal) {
    if (!saved) return;
    const check = await request<Eligibility>('/eligibility-checks', signal, {config_id: saved.id, capability: saved.config.geometry_policy === 'none' ? 'measurement' : 'anatomical_mesh'});
    setEligibility(check);
    setPreview(await request<Preview>(`/simulation-configs/${saved.id}/schedule-preview`, signal));
    setMessage('Eligibility and schedule loaded. Engineering test permission does not establish clinical eligibility.');
  }
  async function freeze(signal: AbortSignal) {
    if (!saved) return;
    const value = await request<Run>(`/branches/${branchId}/simulation-runs`, signal, {config_id: saved.id, expected_draft_revision: saved.draft_revision, expected_config_hash: saved.config_hash});
    setRun(value); setMessage('Isolated engineering run frozen. Generate to dispatch the existing worker.');
  }
  async function generate(signal: AbortSignal) {
    if (!run) return;
    const value = await request<Job>('/imaging-jobs', signal, {expected_revision: run.input_revision, command: {operation: 'simulation_complete', input: {run_id: run.id, expected_config_hash: run.config_hash}}});
    setJob(value); setMessage('Worker queued. Refresh job status to inspect progress; publication remains separate.');
  }
  async function refresh(signal: AbortSignal) {
    if (!job) return;
    const value = await request<Job>(`/imaging-jobs/${job.id}`, signal); setJob(value);
    if (value.result_report_id) {
      const result = await request<Completion>(`/simulation-completions/${value.result_report_id}`, signal);
      if (result.run_id !== run?.id || result.branch_id !== branchId || result.config_hash !== run.config_hash) throw new Error('Completion references do not match the selected frozen run.');
      setCompletion(result); setMessage(result.next_action);
    } else setMessage(value.next_action);
  }
  async function publish(signal: AbortSignal) {
    if (!completion) return;
    await request(`/simulation-completions/${completion.id}/publications`, signal, {expected_config_hash: completion.config_hash, expected_patient_revision: completion.input_revision, expected_association_head: completion.association_head, expected_current_run_id: current, engineering_attestation_sha256: attestation});
    setCurrent(completion.run_id); setCurrentView(null); setMessage('Complete run published privately as an engineering fixture. Scientific review remains pending.');
  }
  const canFreeze = !!saved?.summary.available_actions.includes('freeze_isolated_test_run');
  const canPublish = completion?.status === 'ready' && completion.validation?.status === 'engineering_passed' && /^[0-9a-f]{64}$/.test(attestation) && current !== completion.run_id;
  return <div className={styles.workflow}>
    <div className={styles.notice}><strong>Hypothetical simulation · SYNTHETIC_GENERATED · scientific review pending</strong><p>This workflow does not predict an individual response or select treatment. Authentic baseline and reviewed scientific-policy gates remain open. Normal development mode cannot freeze runs.</p></div>
    <section><h2>1. Authorized baseline</h2><form onSubmit={event => {event.preventDefault(); void act(load);}} autoComplete="off" className={styles.grid}>
      {([['Project UUID', project, setProject], ['Patient UUID', patient, setPatient], ['Branch UUID', branchId, setBranchId]] as const).map(([label, value, setter]) => <label key={label}>{label}<input value={value} onChange={event => {contextChanged(); setter(event.target.value.trim());}} required spellCheck={false}/></label>)}
      <label>Administrator access token<input type="password" value={token} onChange={event => {contextChanged(); setToken(event.target.value);}} autoComplete="off" required/></label>
      <p>Private requests use the configured local API. Tokens and drafts stay in memory; nothing is saved in browser storage.</p>
      <div className={styles.controls}><button disabled={busy}>Load baseline branch</button><button type="button" onClick={() => {contextChanged(); setToken(''); setDraft('{}'); setConfigId(''); setRevision('0'); setAttestation(''); setMessage('Private view, token and draft cleared.');}}>Clear private view</button></div>
    </form>{branch && <dl><dt>Baseline measurement</dt><dd>{branch.input.baseline_measurement_id}</dd><dt>Baseline hash</dt><dd>{branch.baseline_hash}</dd><dt>Observed baseline verified</dt><dd>{String(branch.observed_baseline_verified)} · {branch.mode}</dd><dt>Current private run</dt><dd>{current ?? 'None'}{currentView && !currentView.current_use_allowed && <p>Current use restricted. {currentView.next_action} {currentView.restrictions.join(' · ')}</p>}</dd></dl>}</section>
    <p role="status" aria-live="polite">{message}</p>
    <section><h2>2. Explicit scenario and schedule</h2><p>{Object.entries(FAMILY).map(([code, label]) => `${code}: ${label}`).join(' · ')}</p><p>Paste the owned SimulationConfig JSON with explicit volume targets in mm³, modality times, clinical values, seed and family parameters. Specific therapy categories remain disabled. Missing values stay missing.</p>
      <label>Saved configuration UUID (optional)<input value={configId} onChange={event => setConfigId(event.target.value.trim())} spellCheck={false}/></label><button disabled={busy || !branch} onClick={() => void act(resumeDraft)}>Load saved configuration</button>
      <label>Simulation configuration JSON<textarea rows={18} value={draft} spellCheck={false} onChange={event => {pending.current?.abort(); setBusy(false); setDraft(event.target.value); resetResults();}}/></label>
      <label>Expected current draft revision<input inputMode="numeric" value={revision} onChange={event => setRevision(event.target.value)}/></label>
      <div className={styles.controls}><button disabled={busy || !branch} onClick={() => void act(save)}>Save immutable draft version</button><button disabled={busy || !saved} onClick={() => void act(inspect)}>Inspect eligibility and schedule</button></div>
      {saved && <><p>{saved.summary.disclosure} · {FAMILY[saved.config.scenario.family]} · saved revision {saved.draft_revision}</p><ul>{saved.summary.blocking_reasons.map(reason => <li key={reason}>{reason}</li>)}</ul></>}
      {eligibility && <div className={styles.notice}><strong>Eligibility: {eligibility.result.status}</strong><pre>{JSON.stringify(eligibility.result, null, 2)}</pre></div>}
      {preview && <div className={styles.table}><table><caption>Server sampled schedule · relative days, not calendar dates</caption><thead><tr><th>Slot</th><th>Modality</th><th>Configured day</th><th>Sampled day</th><th>Target / missingness</th></tr></thead><tbody>{preview.slots.map(slot => {const target = preview.tumor_targets.find(item => item.slot_id === slot.slot_id); return <tr key={slot.slot_id}><td>{slot.slot_id}</td><td>{slot.modality}</td><td>{slot.configured_day}</td><td>{slot.relative_day}</td><td>{target ? target.target_mm3 === null ? target.missing_reason : `${target.target_mm3} mm³` : 'Clinical course in configuration'}</td></tr>;})}</tbody></table></div>}
      <label><input type="checkbox" checked={reviewed} onChange={event => setReviewed(event.target.checked)}/> I reviewed the explicit assumptions, synthetic provenance, eligibility gaps and sampled schedule.</label>
    </section>
    <section><h2>3. Generate and validate</h2>{!canFreeze && <p>Generation disabled: an authentic accepted baseline and qualified scientific policy are required. Isolated test execution is available only when the server explicitly advertises it.</p>}
      <div className={styles.controls}><button disabled={busy || !canFreeze || !preview || !eligibility || !reviewed || !!run} onClick={() => void act(freeze)}>Freeze isolated test run</button><button disabled={busy || !run || !!job} onClick={() => void act(generate)}>Generate complete engineering run</button><button disabled={busy || !job} onClick={() => void act(refresh)}>Refresh worker status</button></div>
      {job && <p>Worker: {job.status} · stage {job.stage}. {job.next_action}{job.error_code && ` Error: ${job.error_code}. Preserve the previous publication; inspect failure evidence and create a new run if frozen inputs changed.`}</p>}
      {completion && <><p>Completion: {completion.status} · stage {completion.stage}. {completion.next_action}</p>{completion.validation && <table><caption>Software validation · qualified scientific review pending</caption><thead><tr><th>Level</th><th>Status</th><th>Finding</th></tr></thead><tbody>{completion.validation.findings.map((finding, index) => <tr key={index}><td>{finding.level}</td><td>{finding.status}</td><td>{finding.code}</td></tr>)}</tbody></table>}</>}
    </section>
    <section><h2>4. Explicit private publication</h2><p>Only a complete, validated run can replace the guarded current-run pointer. This action publishes an engineering fixture privately; it does not establish clinical validity.</p><label>Engineering attestation SHA-256<input value={attestation} onChange={event => setAttestation(event.target.value.trim())} spellCheck={false}/></label><button disabled={busy || !canPublish} onClick={() => void act(publish)}>Publish complete run privately</button>{current && <p><Link href={`/states?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&branch=${encodeURIComponent(branchId)}`}>Inspect branch states with exact run identity preserved</Link> · <Link href="/timeline">Inspect the published observation timeline and exact-point geometry</Link>. Select the published branch/run and knowledge cutoff in the private timeline form.{completion?.run_id === current && <> Completion UUID: {completion.id}. Run UUID: {current}. Data revision: {completion.input_revision}.</>}</p>}</section>
  </div>;
}
