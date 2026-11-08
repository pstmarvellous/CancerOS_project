'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import type { components } from '../../../packages/contracts/generated/api';
import { ErrorSummary, LoadingState } from './research';

type Schema = components['schemas'];
type Branch = Schema['BranchReport'];
type BranchSummary = Schema['BranchSummary'];
type BranchPage = Schema['BranchPage'];
type Saved = Schema['ConfigVersion'];
type Preview = Schema['SampledObservations'];
type Eligibility = Schema['EligibilityReport'];
type Run = Schema['SimulationRun'];
type Completion = Schema['CompletionReport'];
type Job = Schema['ImagingJobRecord'];
type Current = Schema['CurrentRunView'];

const FAMILY: { id: string; label: string; hint: string }[] = [
  { id: 'SC-01', label: 'Continuous shrinkage', hint: 'The modeled region keeps getting smaller. Not a response claim.' },
  { id: 'SC-02', label: 'Little or no size change', hint: 'The modeled region stays about the same size. Missing stays missing.' },
  { id: 'SC-03', label: 'Continued growth', hint: 'The modeled region keeps getting larger. Not progression staging.' },
  { id: 'SC-04', label: 'Shrinks, then grows again', hint: 'Smaller first, then larger again. Seed and days explicit.' },
  { id: 'SC-05', label: 'Stable size with worsening symptoms', hint: 'Size stays flat while the symptom course changes. Imaging stays separate.' },
];

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  return text ? (JSON.parse(text) as unknown) : null;
}

function explain(response: Response): string {
  if (response.status === 401) return 'Sign in with an authorized session, then retry. A viewer cannot freeze runs.';
  if (response.status === 403) return 'This simulation action is restricted for your role. Ask an administrator for access.';
  if (response.status === 404) return 'The selected branch, run, or configuration is unavailable in this authorized case.';
  if (response.status === 409) return 'Current permissions, revision, draft, or scientific gates block this action. Reload the branch; your builder entries are preserved.';
  if (response.status === 422) return 'The generated configuration was rejected. Check family parameters, days, and schedule.';
  return `The authorized request failed (status ${response.status}).`;
}

export function SimulationBuilder({ project, patient }: { project: string; patient: string }) {
  const [branches, setBranches] = useState<BranchSummary[]>([]);
  const [branchId, setBranchId] = useState('');
  const [branch, setBranch] = useState<Branch | null>(null);
  const [family, setFamily] = useState('SC-01');
  const [geometry, setGeometry] = useState<'none' | 'anatomical_mesh'>('none');
  const [days, setDays] = useState('10, 30, 60');
  const [seed, setSeed] = useState('7');
  const [target, setTarget] = useState('120.5');
  const [missingReason, setMissingReason] = useState('');
  const [revision, setRevision] = useState('0');
  const [savedId, setSavedId] = useState('');
  const [saved, setSaved] = useState<Saved | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [eligibility, setEligibility] = useState<Eligibility | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [completion, setCompletion] = useState<Completion | null>(null);
  const [current, setCurrent] = useState<Current | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [attestation, setAttestation] = useState('');
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>('loading');
  const [message, setMessage] = useState('Loading authorized branches for this case. No UUID entry is needed.');
  const branchIdRef = useRef('');
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  useEffect(() => {
    const controller = new AbortController();
    pending.current?.abort();
    pending.current = controller;
    if (!project || !patient) {
      controller.abort();
      queueMicrotask(() => { setStatus('failed'); setMessage('Open a case from the workspace first — no UUID entry is needed.'); });
      return () => controller.abort();
    }
    void (async () => {
      setStatus('loading');
      try {
        const response = await fetch(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=branches`, { cache: 'no-store', signal: controller.signal });
        if (!response.ok) throw new Error(explain(response));
        const page = (await readJson(response)) as BranchPage;
        if (controller.signal.aborted) return;
        setBranches(page.items ?? []);
        if (page.items?.length && !branchIdRef.current) {
          branchIdRef.current = page.items[0].branch_id;
          setBranchId(page.items[0].branch_id);
        }
        setStatus('ready');
        setMessage(page.items?.length ? `${page.items.length} authorized branch${page.items.length === 1 ? '' : 'es'} loaded. Select one; the builder generates owned JSON.` : 'No simulation branches exist for this case yet. Create a branch from an observed baseline before generating.');
      } catch (error) {
        if (controller.signal.aborted) return;
        setStatus('failed');
        setMessage(error instanceof Error ? error.message : 'Branches could not load.');
      }
    })();
    return () => controller.abort();
  }, [project, patient]);

  async function reloadBranches(signal: AbortSignal) {
    const response = await fetch(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=branches`, { cache: 'no-store', signal });
    if (!response.ok) throw new Error(explain(response));
    const page = (await readJson(response)) as BranchPage;
    setBranches(page.items ?? []);
    setStatus('ready');
    setMessage(page.items?.length ? `${page.items.length} authorized branch${page.items.length === 1 ? '' : 'es'} loaded. Select one; the builder generates owned JSON.` : 'No simulation branches exist for this case yet. Create a branch from an observed baseline before generating.');
  }

  async function authorized<T>(path: string, signal: AbortSignal, body?: unknown): Promise<T> {
    const headers: Record<string, string> = {};
    let key: string | undefined;
    if (body !== undefined) {
      headers['content-type'] = 'application/json';
      key = crypto.randomUUID();
      headers['idempotency-key'] = key;
    }
    const response = await fetch(path, { method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store', signal });
    if (!response.ok) throw new Error(explain(response));
    return (await readJson(response)) as T;
  }

  async function act(action: (signal: AbortSignal) => Promise<void>) {
    if (!UUID.test(branchId)) { setMessage('Select an authorized branch from the list. No manual UUID entry is needed.'); return; }
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setBusy(true);
    try { await action(controller.signal); } catch (error) { if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : 'Request failed. Builder entries are preserved.'); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }

  async function loadBranch(signal: AbortSignal) {
    setSaved(null); setPreview(null); setEligibility(null); setRun(null); setJob(null); setCompletion(null); setReviewed(false);
    const value = await authorized<Branch>(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=branch&branch=${encodeURIComponent(branchId)}`, signal);
    const pointer = await authorized<Current>(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=current&branch=${encodeURIComponent(branchId)}`, signal);
    setBranch(value); setCurrent(pointer);
    setMessage('Branch loaded. The builder generates explicit assumptions below; no clinical defaults are supplied.');
  }

  function parseDays(): string[] {
    return days.split(',').map(part => part.trim()).filter(part => /^-?(0|[1-9]\d*)(\.\d{1,9})?$/.test(part));
  }

  function buildConfig(): Record<string, unknown> {
    const dayList = parseDays();
    const seedValue = Number(seed);
    const hasMissing = missingReason.trim().length > 0;
    const targetValue = target.trim();
    if (!branch) throw new Error('Load a branch before generating a configuration.');
    if (dayList.length < 3) throw new Error('Enter at least three follow-up days, for example 10, 30, 60.');
    if (!Number.isSafeInteger(seedValue) || seedValue < 0 || seedValue > 4294967295) throw new Error('Enter an integer seed from 0 to 4294967295.');
    if (!hasMissing && !/^-?(0|[1-9]\d*)(\.\d{1,9})?$/.test(targetValue)) throw new Error('Enter an explicit decimal target volume in mm³, or a missing reason.');
    if (!branch.baseline_hash) throw new Error('Branch baseline hash is unavailable. Reload the branch.');
    const detailRevision = 1;
    const slots = dayList.map((day, index) => ({ slot_id: `slot-${index + 1}`, modality: 'imaging', relative_day: day }));
    const explicitTarget = hasMissing ? null : targetValue;
    return {
      baseline_state_id: branch.baseline_state_id ?? null,
      baseline_hash: branch.baseline_hash,
      branch_id: branch.id,
      input_revision: detailRevision,
      scenario: { family, definition_version: `${family.toLowerCase()}-explicit/1` },
      treatment: { exposure: 'none' },
      schedule: { slots },
      tumor_profile: {
        metric: 'numerical_region_volume',
        unit: 'mm3',
        points: slots.map(slot => hasMissing ? { slot_id: slot.slot_id, target_mm3: null, missing_reason: missingReason.trim() } : { slot_id: slot.slot_id, target_mm3: explicitTarget }),
      },
      clinical_profile: { configuration: 'stable' },
      noise: { mode: 'none' },
      missingness: { mode: 'none' },
      geometry_policy: geometry === 'anatomical_mesh' ? 'isotropic-fixed-grid/1' : 'none',
      seed: seedValue,
    };
  }

  async function save(signal: AbortSignal) {
    let config: Record<string, unknown>;
    try { config = buildConfig(); } catch (error) { throw error; }
    const expected = Number(revision);
    if (!Number.isSafeInteger(expected) || expected < 0) throw new Error('Enter a nonnegative expected draft revision.');
    const value = await authorized<Saved>(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=config&branch=${encodeURIComponent(branchId)}`, signal, { expected_draft_revision: expected, config });
    setSaved(value); setRevision(String(value.draft_revision)); setRun(null); setCompletion(null); setJob(null); setPreview(null); setEligibility(null); setReviewed(false);
    setMessage(`Immutable draft saved · revision ${value.draft_revision}. Inspect eligibility and the sampled schedule before freezing.`);
  }

  async function resume(signal: AbortSignal) {
    if (!UUID.test(savedId)) throw new Error('Select a saved configuration from this branch. Paste is only needed when reopening an older revision manually.');
    const value = await authorized<Saved>(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=config&config=${encodeURIComponent(savedId)}`, signal);
    if (value.branch_id !== branchId) throw new Error('Saved configuration belongs to a different branch. Builder entries are preserved.');
    setSaved(value); setRevision(String(value.draft_revision));
    setMessage(`Saved configuration ${value.id.slice(0, 8)}… loaded. Inspect eligibility and schedule again.`);
  }

  async function inspect(signal: AbortSignal) {
    if (!saved) return;
    const check = await authorized<Eligibility>(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=eligibility`, signal, { config_id: saved.id, capability: saved.config.geometry_policy === 'none' ? 'measurement' : 'anatomical_mesh' });
    setEligibility(check);
    const sampled = await authorized<Preview>(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=preview&config=${encodeURIComponent(saved.id)}`, signal);
    setPreview(sampled);
    setMessage('Eligibility and sampled schedule loaded. Engineering test permission does not establish clinical eligibility.');
  }

  async function freeze(signal: AbortSignal) {
    if (!saved) return;
    const value = await authorized<Run>(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=run&branch=${encodeURIComponent(branchId)}`, signal, { config_id: saved.id, expected_draft_revision: saved.draft_revision, expected_config_hash: saved.config_hash });
    setRun(value); setJob(null); setCompletion(null);
    setMessage('Isolated test run frozen. Generate the engineering run, then refresh worker status.');
  }

  async function generate(signal: AbortSignal) {
    if (!run) return;
    const value = await authorized<Job>(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=job`, signal, { expected_revision: run.input_revision, command: { operation: 'simulation_complete', input: { run_id: run.id, expected_config_hash: run.config_hash } } });
    setJob(value);
    setMessage('Worker queued. Refresh worker status to inspect progress; publication remains separate.');
  }

  async function refresh(signal: AbortSignal) {
    if (!job) return;
    const value = await authorized<Job>(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=job&job=${encodeURIComponent(job.id)}`, signal);
    setJob(value);
    if (value.result_report_id) {
      const result = await authorized<Completion>(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=completion&completion=${encodeURIComponent(value.result_report_id)}`, signal);
      if (result.run_id !== run?.id) throw new Error('Completion does not match the frozen run.');
      setCompletion(result);
      setMessage(result.next_action);
    } else setMessage(value.next_action);
  }

  async function publish(signal: AbortSignal) {
    if (!completion) return;
    await authorized(`/api/simulation?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&resource=complete`, signal, { completion_id: completion.id, expected_config_hash: completion.config_hash, expected_patient_revision: completion.input_revision, expected_association_head: completion.association_head, expected_current_run_id: current?.publication?.run_id ?? null, engineering_attestation_sha256: attestation });
    setMessage('Complete run published privately as an engineering fixture. Scientific review remains pending.');
  }

  const canFreeze = !!saved?.summary.available_actions.includes('freeze_isolated_test_run');
  const canPublish = completion?.status === 'ready' && completion?.validation?.status === 'engineering_passed' && /^[0-9a-f]{64}$/.test(attestation);

  if (status === 'loading') return <LoadingState />;
  if (status === 'failed') return <section className="card"><ErrorSummary message={message} /><p><button className="button-secondary" onClick={() => void act(reloadBranches)}>Retry loading branches</button></p></section>;

  return <div>
    <div className="card" role="status" aria-live="polite" style={{ borderLeft: '4px solid #6d28d9' }}>
      <strong>Hypothetical simulation · SYNTHETIC_GENERATED · scientific review pending</strong>
      <p style={{ margin: '8px 0 0' }}>{message}</p>
      <p className="field-hint" style={{ margin: '8px 0 0' }}>Treatment exposure stays locked to <code>none</code>. Generation never changes observed history.</p>
    </div>

    <section className="card" style={{ marginTop: 16 }}>
      <h2>1. Select an authorized branch</h2>
      {branches.length ? (
        <label>Branch in this case
          <select value={branchId} onChange={event => { setBranchId(event.target.value); setBranch(null); setSaved(null); setPreview(null); setEligibility(null); setRun(null); setJob(null); setCompletion(null); }} aria-label="Branch in this case">
            {branches.map((item, index) => <option key={item.branch_id} value={item.branch_id}>Branch {index + 1} · observed baseline {String(item.observed_baseline_verified)} · {item.mode}</option>)}
          </select>
          <span className="field-hint">Branches come from the authorized case list; no UUID typing.</span>
        </label>
      ) : <p>No branches exist for this case. Create a branch from an observed baseline first.</p>}
      <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
        <button className="button-secondary" disabled={busy || !branchId} onClick={() => void act(loadBranch)}>Load baseline branch</button>
        <button className="button-ghost" type="button" disabled={busy} onClick={() => void act(reloadBranches)}>Reload branches</button>
      </div>
      {branch && <dl className="case-fields" style={{ marginTop: 12 }}><div><dt>Baseline verified</dt><dd>{String(branch.observed_baseline_verified)} · {branch.mode}</dd></div><div><dt>Baseline hash</dt><dd>{branch.baseline_hash.slice(0, 12)}…</dd></div><div><dt>Current private run</dt><dd>{current?.publication?.run_id ? current.publication.run_id.slice(0, 8).concat('…') : 'None'}</dd></div></dl>}
    </section>

    <section className="card" style={{ marginTop: 16 }}>
      <h2>2. Explicit scenario and schedule</h2>
      <p className="field-hint">Pick a family and schedule; the builder generates owned SimulationConfig JSON. Paste is never required.</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(200px,1fr))', gap: 8, margin: '12px 0' }}>
        {FAMILY.map(item => <button key={item.id} type="button" className={family === item.id ? 'button-secondary' : 'button-ghost'} style={{ textAlign: 'left' }} onClick={() => setFamily(item.id)} aria-pressed={family === item.id} aria-label={`Scenario family ${item.id}: ${item.label}`}><strong>{item.id}</strong> · {item.label}<span className="field-hint" style={{ display: 'block' }}>{item.hint}</span></button>)}
      </div>
      <div className="form-grid">
        <label>Geometry policy<select value={geometry} onChange={event => setGeometry(event.target.value as 'none' | 'anatomical_mesh')}><option value="none">Measurement only</option><option value="anatomical_mesh">Anatomical mesh</option></select><span className="field-hint">Measurement-only skips mesh regeneration.</span></label>
        <label>Follow-up days (relative)<input value={days} onChange={event => setDays(event.target.value)} inputMode="text" placeholder="10, 30, 60" /><span className="field-hint">Comma-separated relative days, not calendar dates.</span></label>
        <label>Explicit target volume mm³<input value={target} onChange={event => setTarget(event.target.value)} inputMode="decimal" placeholder="120.5" /><span className="field-hint">Positive mm³ per target, or set a missing reason.</span></label>
        <label>Missing reason (optional)<input value={missingReason} onChange={event => setMissingReason(event.target.value)} placeholder="not_acquired" /><span className="field-hint">When set, targets stay missing with this reason.</span></label>
        <label>Seed (integer)<input value={seed} onChange={event => setSeed(event.target.value)} inputMode="numeric" /><span className="field-hint">Reproducibility seed recorded in assumptions.</span></label>
        <label>Expected current draft revision<input value={revision} onChange={event => setRevision(event.target.value)} inputMode="numeric" /><span className="field-hint">Optimistic concurrency; reload on 409.</span></label>
      </div>
      <p className="field-hint">Treatment exposure: <code>none</code> (locked pending qualified policy review). Specific therapy categories remain disabled.</p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button className="button-primary" disabled={busy || !branch} onClick={() => void act(save)}>Save immutable draft version</button>
        <button className="button-secondary" disabled={busy || !saved} onClick={() => void act(inspect)}>Inspect eligibility and schedule</button>
      </div>
      {saved && <><p style={{ marginTop: 12 }}>{saved.summary.disclosure} · saved revision {saved.draft_revision}</p><ul>{saved.summary.blocking_reasons.map(reason => <li key={reason}>{reason}</li>)}</ul></>}
      {eligibility && <div className="card" style={{ marginTop: 12 }}><strong>Eligibility: {eligibility.result.status}</strong><pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(eligibility.result, null, 2)}</pre></div>}
      {preview && <div style={{ overflowX: 'auto', marginTop: 12 }}><table><caption>Server sampled schedule · relative days</caption><thead><tr><th>Slot</th><th>Modality</th><th>Configured day</th><th>Sampled day</th><th>Target / missingness</th></tr></thead><tbody>{preview.slots.map(slot => { const found = preview.tumor_targets.find(item => item.slot_id === slot.slot_id); return <tr key={slot.slot_id}><td>{slot.slot_id}</td><td>{slot.modality}</td><td>{slot.configured_day}</td><td>{slot.relative_day}</td><td>{found ? found.target_mm3 === null ? found.missing_reason : `${found.target_mm3} mm³` : 'Clinical course in configuration'}</td></tr>; })}</tbody></table></div>}
      <details style={{ marginTop: 12 }}><summary>Advanced: reopen a saved configuration by ID</summary><label>Saved configuration ID<input value={savedId} onChange={event => setSavedId(event.target.value.trim())} placeholder="Saved configuration UUID" /><span className="field-hint">Only needed when reopening an older revision outside this builder flow.</span></label><button className="button-ghost" disabled={busy || !branch} onClick={() => void act(resume)} style={{ marginTop: 8 }}>Load saved configuration</button></details>
      <label style={{ display: 'block', marginTop: 12 }}><input type="checkbox" checked={reviewed} onChange={event => setReviewed(event.target.checked)} /> I reviewed the explicit assumptions, synthetic provenance, eligibility gaps and sampled schedule.</label>
    </section>

    <section className="card" style={{ marginTop: 16 }}>
      <h2>3. Generate and validate</h2>
      {!canFreeze && <p className="field-hint">Generation stays disabled until the server advertises an isolated test run for an authentic accepted baseline. This is a scientific-policy gate, not a UI error.</p>}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button className="button-secondary" disabled={busy || !canFreeze || !preview || !eligibility || !reviewed || !!run} onClick={() => void act(freeze)}>Freeze isolated test run</button>
        <button className="button-secondary" disabled={busy || !run || !!job} onClick={() => void act(generate)}>Generate complete engineering run</button>
        <button className="button-ghost" disabled={busy || !job} onClick={() => void act(refresh)}>Refresh worker status</button>
      </div>
      {job && <p>Worker: {job.status} · stage {job.stage}. {job.next_action}{job.error_code && ` Error: ${job.error_code}. Preserve the previous publication; inspect failure evidence and create a new run if frozen inputs changed.`}</p>}
      {completion && <><p>Completion: {completion.status} · stage {completion.stage}. {completion.next_action}</p>{completion.validation && <table><caption>Software validation · qualified scientific review pending</caption><thead><tr><th>Level</th><th>Status</th><th>Finding</th></tr></thead><tbody>{completion.validation.findings.map((finding, index) => <tr key={index}><td>{finding.level}</td><td>{finding.status}</td><td>{finding.code}</td></tr>)}</tbody></table>}</>}
    </section>

    <section className="card" style={{ marginTop: 16 }}>
      <h2>4. Explicit private publication</h2>
      <p className="field-hint">Only a complete, validated run can replace the guarded current-run pointer. This publishes an engineering fixture privately; it does not establish clinical validity.</p>
      <label>Engineering attestation SHA-256<input value={attestation} onChange={event => setAttestation(event.target.value.trim())} spellCheck={false} placeholder="64 hex characters" /><span className="field-hint">Paste the reviewed attestation digest; nothing publishes automatically.</span></label>
      <button className="button-primary" disabled={busy || !canPublish} onClick={() => void act(publish)} style={{ marginTop: 8 }}>Publish complete run privately</button>
      {current?.publication?.run_id && <p>Current private run: {current.publication.run_id.slice(0, 8)}… <Link href={`/states?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&branch=${encodeURIComponent(branchId)}`}>Inspect branch states</Link></p>}
    </section>
  </div>;
}

export function SimulationWorkflow() {
  return <SimulationBuilderFromQuery />;
}

function SimulationBuilderFromQuery() {
  return <SimulationBuilderShell />;
}

function readLastCase(): { project: string; patient: string } | null {
  try {
    const raw = localStorage.getItem('canceros:last_case');
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { project?: unknown; patient?: unknown };
    if (typeof parsed.project === 'string' && typeof parsed.patient === 'string' && UUID.test(parsed.project) && UUID.test(parsed.patient)) {
      return { project: parsed.project, patient: parsed.patient };
    }
    return null;
  } catch { return null; }
}

function SimulationBuilderShell() {
  const [context, setContext] = useState<{ project: string; patient: string } | null>(() => (typeof window === 'undefined' ? null : readLastCase()));
  const [project, setProject] = useState('');
  const [patient, setPatient] = useState('');
  if (context) return <SimulationBuilder project={context.project} patient={context.patient} />;
  const applyContext = (value: { project: string; patient: string }) => setContext(value);
  return (
    <div>
      <p className="field-hint">The builder inherits the last opened case from the workspace. Open a case once — no UUID paste needed — or enter the workspace identifiers below a single time. This one-time entry is stored only to route the same authorized case; the research session cookie still authorizes every request.</p>
      <form onSubmit={event => { event.preventDefault(); if (UUID.test(project) && UUID.test(patient)) applyContext({ project, patient }); }} className="card">
        <label>Project (one-time routing)<input value={project} onChange={event => setProject(event.target.value.trim())} placeholder="Selected automatically after opening a case" /></label>
        <label>Patient (one-time routing)<input value={patient} onChange={event => setPatient(event.target.value.trim())} placeholder="Selected automatically after opening a case" /></label>
        <button className="button-secondary" type="submit" style={{ marginTop: 8 }}>Use this case context</button>
      </form>
      <p><Link href="/cases">← Case library</Link></p>
    </div>
  );
}
