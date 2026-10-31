'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import type { components } from '../../../packages/contracts/generated/api';
import { ErrorSummary, LoadingState } from './research';

type S = components['schemas'];
type PatientDetail = S['PatientDetail'];
type ObservationSummary = S['ObservationSummary'];
type ObservationPage = S['ObservationPage'];
type VisitPage = S['VisitPage'];
type ClinicalRecord = S['ClinicalRecord'];
type BatchReport = S['BatchReport'];
type RetractionInput = S['RetractionInput'];

type Status =
  | { kind: 'needs-selection' }
  | { kind: 'loading' }
  | { kind: 'failed'; message: string }
  | { kind: 'ready' };

function useSelection(): { project: string | null; patient: string | null } {
  const [selection] = useState<{ project: string | null; patient: string | null }>(() => {
    if (typeof window === 'undefined') return { project: null, patient: null };
    const params = new URLSearchParams(window.location.search);
    return { project: params.get('project'), patient: params.get('patient') };
  });
  return selection;
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return { raw: text.slice(0, 500) };
  }
}

function explain(response: Response): string {
  if (response.status === 401) return 'Sign in with an authorized session, then retry. A judge or viewer cannot write through this form.';
  if (response.status === 403) return 'This action is restricted for your role. Ask an administrator for access.';
  if (response.status === 404) return 'The case was not found or is not visible to your role.';
  if (response.status === 409) return 'The record or revision changed. Reload the case before resubmitting; nothing was overwritten.';
  if (response.status === 412) return 'The case revision changed while you were editing. Reload the exact case and reapply your safe change.';
  if (response.status === 422) return 'The server rejected a field value. Correct the highlighted field and retry.';
  return `The request failed (status ${response.status}).`;
}

type ObservationFilters = { kind: string; cursor: string | null; items: ObservationSummary[] };

async function fetchObservations(
  project: string,
  patient: string,
  kind: string | null,
  cursor: string | null,
  signal: AbortSignal,
): Promise<{ items: ObservationSummary[]; snapshot: string }> {
  const response = await fetch(
    `/api/case-observations?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`,
    {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        kind: kind && kind !== 'all' ? kind : null,
        concept: null,
        visit_id: null,
        cursor,
        limit: 25,
      }),
      cache: 'no-store',
      signal,
    },
  );
  if (!response.ok) throw new Error(explain(response));
  const page = (await readJson(response)) as ObservationPage;
  return { items: page.items ?? [], snapshot: page.snapshot_cursor };
}

function recordSummary(record: ClinicalRecord): string {
  const item = record.item as { kind?: string; concept?: string; label?: string; original_term?: string };
  const label = item.label ?? item.original_term ?? item.concept ?? item.kind ?? 'record';
  const quality = record.quality as { status?: string } | undefined;
  return `${label} · availability ${record.availability} · quality ${quality?.status ?? 'unknown'}`;
}

function ReceptorRow({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value == null || value === '' ? 'Not recorded' : value}</dd>
    </div>
  );
}

function fieldOf(record: ClinicalRecord, name: string): string | null {
  const item = record.item as Record<string, unknown>;
  const value = item[name];
  return typeof value === 'string' ? value : null;
}

export function CaseWorkspace() {
  const { project, patient } = useSelection();
  const [status, setStatus] = useState<Status>(() =>
    project && patient ? { kind: 'loading' } : { kind: 'needs-selection' },
  );
  const [detail, setDetail] = useState<PatientDetail | null>(null);
  const [visits, setVisits] = useState<VisitPage | null>(null);
  const [filters, setFilters] = useState<ObservationFilters>({ kind: 'all', cursor: null, items: [] });
  const [snapshot, setSnapshot] = useState<string | null>(null);
  const [records, setRecords] = useState<Record<string, ClinicalRecord>>({});
  const [message, setMessage] = useState(
    'Overview leads with what is known, what is missing and what the selected capability needs next.',
  );
  const [kindFilter, setKindFilter] = useState('all');
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  const load = useCallback(async () => {
    if (!project || !patient) {
      setStatus({ kind: 'needs-selection' });
      return;
    }
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setStatus({ kind: 'loading' });
    try {
      const detailResponse = await fetch(
        `/api/case-detail?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`,
        { cache: 'no-store', signal: controller.signal },
      );
      if (!detailResponse.ok) throw new Error(explain(detailResponse));
      const detailBody = (await readJson(detailResponse)) as PatientDetail;
      const visitResponse = await fetch(
        `/api/case-visits?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`,
        { cache: 'no-store', signal: controller.signal },
      );
      if (!visitResponse.ok) throw new Error(explain(visitResponse));
      const visitBody = (await readJson(visitResponse)) as VisitPage;
      const observed = await fetchObservations(project, patient, 'all', null, controller.signal);
      if (controller.signal.aborted) return;
      setDetail(detailBody);
      setVisits(visitBody);
      setFilters({ kind: 'all', cursor: null, items: observed.items });
      setSnapshot(observed.snapshot);
      setRecords({});
      setStatus({ kind: 'ready' });
      setMessage(
        `Case ${detailBody.display_code} · revision ${detailBody.data_revision} · ${detailBody.observation_count} observations in ${detailBody.visit_count} visits. Unknown values stay “Not recorded”.`,
      );
    } catch (error) {
      if (controller.signal.aborted) return;
      setStatus({ kind: 'failed', message: error instanceof Error ? error.message : 'The case could not load.' });
    }
  }, [project, patient]);

  useEffect(() => {
    if (!project || !patient) return;
    let cancelled = false;
    (async () => {
      try {
        await load();
      } catch {
        if (!cancelled) setStatus({ kind: 'failed', message: 'The case could not load.' });
      }
    })();
    return () => {
      cancelled = true;
    };
    // load is stable for a fixed project/patient pair; re-running on its identity would refetch needlessly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [project, patient]);

  async function applyKindFilter(kind: string) {
    if (!project || !patient) return;
    setKindFilter(kind);
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    try {
      const observed = await fetchObservations(project, patient, kind, null, controller.signal);
      if (controller.signal.aborted) return;
      setFilters({ kind, cursor: null, items: observed.items });
      setSnapshot(observed.snapshot);
      setMessage(
        observed.items.length
          ? `${observed.items.length} records shown for ${kind === 'all' ? 'all observation kinds' : kind}.`
          : `No ${kind === 'all' ? '' : `${kind} `}records are available. Missing records are not zero or normal.`,
      );
    } catch (error) {
      if (!controller.signal.aborted) setMessage(error instanceof Error ? error.message : 'Filter failed.');
    }
  }

  async function openRecord(recordId: string) {
    if (!project || !patient) return;
    if (records[recordId]) return;
    const controller = new AbortController();
    try {
      const response = await fetch(
        `/api/case-record?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&record=${encodeURIComponent(recordId)}`,
        { cache: 'no-store', signal: controller.signal },
      );
      if (!response.ok) throw new Error(explain(response));
      const body = (await readJson(response)) as ClinicalRecord;
      setRecords(previous => ({ ...previous, [recordId]: body }));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'The record could not load.');
    }
  }

  if (!project || !patient) {
    return (
      <section className="card">
        <h2>No case selected</h2>
        <p>
          Open a case from the <Link href="/cases">research case library</Link> with an authorized project and
          patient, then continue to its <Link href="/cases/detail">profile and sources</Link>. The workspace never
          guesses a project or substitutes another case.
        </p>
      </section>
    );
  }
  if (status.kind === 'loading') return <LoadingState />;
  if (status.kind === 'failed') {
    return (
      <section className="card">
        <ErrorSummary message={status.message} />
        <p>
          <button type="button" onClick={() => void load()}>
            Retry loading case
          </button>
        </p>
      </section>
    );
  }
  if (!detail) return <LoadingState />;

  const byKind = new Map<string, number>();
  for (const item of filters.items) byKind.set(item.kind, (byKind.get(item.kind) ?? 0) + 1);
  const kinds = ['all', 'laboratory', 'vital', 'diagnosis', 'treatment', 'symptom', 'visit', 'note'];
  const diagnosisRecords = Object.values(records).filter(
    record => (record.item as { kind?: string }).kind === 'diagnosis',
  );
  const receptor = (name: string): string | null => {
    for (const record of diagnosisRecords) {
      const value = fieldOf(record, name);
      if (value) return value;
    }
    return null;
  };

  return (
    <>
      <p role="status" aria-live="polite">
        {message}
      </p>
      <section className="card" aria-label="Case overview">
        <p className="eyebrow">Overview · Observed case facts</p>
        <h2>{detail.display_code}</h2>
        <dl className="case-fields">
          <div>
            <dt>Case</dt>
            <dd>{detail.display_code}</dd>
          </div>
          <div>
            <dt>Data revision</dt>
            <dd>{detail.data_revision}</dd>
          </div>
          <div>
            <dt>Observations</dt>
            <dd>{detail.observation_count}</dd>
          </div>
          <div>
            <dt>Visits</dt>
            <dd>{detail.visit_count}</dd>
          </div>
          <div>
            <dt>Next action</dt>
            <dd>{detail.next_action}</dd>
          </div>
        </dl>
        <p>
          Pseudonymous research case. Source-backed facts appear below; unknown receptor or pathology values stay
          “Not recorded” and are never inferred from a scenario.
        </p>
        <dl className="case-fields">
          <ReceptorRow label="Side" value={receptor('laterality') ?? receptor('side')} />
          <ReceptorRow label="Pathology" value={receptor('histology') ?? receptor('diagnosis_text')} />
          <ReceptorRow label="Estrogen receptor" value={receptor('er_status')} />
          <ReceptorRow label="Progesterone receptor" value={receptor('pr_status')} />
          <ReceptorRow label="HER2" value={receptor('her2_status')} />
        </dl>
        <p>
          Two-state comparison within this history stays available from the Twin workspace. Branch switching is
          sequential and never invents intermediate geometry.
        </p>
      </section>

      <section className="card" aria-label="Record completeness">
        <h2>Completeness by capability</h2>
        <p>
          Completeness describes record availability for each research capability. It is not a patient health or
          trust score, and missing records are not normal values.
        </p>
        <ul>
          <li>
            Case facts: {detail.observation_count > 0 ? 'available' : 'not recorded'} ({detail.observation_count}{' '}
            observations)
          </li>
          <li>
            Visit history: {detail.visit_count > 0 ? 'available' : 'not recorded'} ({detail.visit_count} visits)
          </li>
          {['laboratory', 'vital', 'diagnosis', 'treatment', 'symptom', 'visit', 'note'].map(kind => (
            <li key={kind}>
              {kind}: {byKind.get(kind) ?? 0} loaded in this view ·{' '}
              {(byKind.get(kind) ?? 0) > 0 ? 'available' : 'not recorded or restricted'}
            </li>
          ))}
        </ul>
        <p>Restricted capabilities show “access restricted”. Pending review and invalid records stay distinct.</p>
      </section>

      <section className="card" aria-label="Observations">
        <h2>Observations and source drill-down</h2>
        <p>
          <label htmlFor="kind-filter">Filter by observation kind </label>
          <select id="kind-filter" value={kindFilter} onChange={event => void applyKindFilter(event.target.value)}>
            {kinds.map(kind => (
              <option key={kind} value={kind}>
                {kind}
              </option>
            ))}
          </select>
        </p>
        {snapshot ? <p>Snapshot cursor: {snapshot.slice(0, 12)}…</p> : null}
        {filters.items.length === 0 ? (
          <p>No records match this filter. Missing, invalid and restricted records are never shown as zero.</p>
        ) : (
          <ul>
            {filters.items.map(item => {
              const record = records[item.record_id];
              return (
                <li key={item.record_id}>
                  <details onToggle={event => {
                    if ((event.target as HTMLDetailsElement).open) void openRecord(item.record_id);
                  }}>
                    <summary>
                      {item.kind} · {item.concept}
                      {item.superseded ? ' · superseded' : ''}
                    </summary>
                    {record ? (
                      <>
                        <p>{recordSummary(record)}</p>
                        <p>Source hash: {item.source_hash.slice(0, 12)}… (locator summary only; no raw identifiers).</p>
                        <RetractionForm
                          project={project}
                          patient={patient}
                          recordId={item.record_id}
                          revision={detail.data_revision}
                          onDone={note => setMessage(note)}
                        />
                      </>
                    ) : (
                      <p>Opening loads the exact record revision with source lineage.</p>
                    )}
                  </details>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <section className="card" aria-label="Visit history">
        <h2>Visit history</h2>
        {visits && visits.items.length > 0 ? (
          <ul>
            {visits.items.map(visit => (
              <li key={visit.visit_id}>
                Visit {visit.visit_id.slice(0, 8)}… · {visit.observation_count} observations · time basis{' '}
                {visit.time_basis}
              </li>
            ))}
          </ul>
        ) : (
          <p>No visits are recorded for this case. Unknown-time records stay unplaced.</p>
        )}
      </section>

      <ObservationEditor
        project={project}
        patient={patient}
        revision={detail.data_revision}
        onDone={note => {
          setMessage(note);
          void load();
        }}
      />
      <AdminImportReview
        project={project}
        patient={patient}
        onDone={note => setMessage(note)}
      />
    </>
  );
}

function RetractionForm({
  project,
  patient,
  recordId,
  revision,
  onDone,
}: {
  project: string;
  patient: string;
  recordId: string;
  revision: number;
  onDone: (note: string) => void;
}) {
  const [reason, setReason] = useState<RetractionInput['reason_code']>('entered_in_error');
  const [busy, setBusy] = useState(false);
  async function submit() {
    if (!window.confirm('Retract this observation? The correction history is retained.')) return;
    setBusy(true);
    try {
      const response = await fetch(
        `/api/case-record?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&record=${encodeURIComponent(recordId)}&action=retract`,
        {
          method: 'POST',
          headers: { 'content-type': 'application/json', 'idempotency-key': `retract-${recordId}` },
          body: JSON.stringify({ expected_revision: revision, reason_code: reason } satisfies RetractionInput),
        },
      );
      if (!response.ok) throw new Error(explain(response));
      onDone(`Retraction receipt saved for ${recordId.slice(0, 8)}…. History is retained; the current snapshot is unchanged until review.`);
    } catch (error) {
      onDone(error instanceof Error ? error.message : 'Retraction failed.');
    } finally {
      setBusy(false);
    }
  }
  return (
    <p>
      <label htmlFor={`retract-${recordId}`}>Retraction reason </label>
      <select
        id={`retract-${recordId}`}
        value={reason}
        onChange={event => setReason(event.target.value as RetractionInput['reason_code'])}
      >
        <option value="entered_in_error">Entered in error</option>
        <option value="source_corrected">Source corrected</option>
        <option value="identity_review">Identity review</option>
        <option value="withdrawn_source">Withdrawn source</option>
      </select>{' '}
      <button type="button" disabled={busy} onClick={() => void submit()}>
        Retract with history
      </button>
    </p>
  );
}

function ObservationEditor({
  project,
  patient,
  revision,
  onDone,
}: {
  project: string;
  patient: string;
  revision: number;
  onDone: (note: string) => void;
}) {
  const [artifact, setArtifact] = useState('');
  const [busy, setBusy] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState(() => `editor-${crypto.randomUUID()}`);

  async function validateThenAccept() {
    if (!artifact) {
      onDone('Select an approved source artifact before staging an observation. The browser never approves sources.');
      return;
    }
    setBusy(true);
    try {
      const body = { source_artifact_id: artifact, expected_revision: revision };
      const validate = await fetch(
        `/api/case-batch?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&action=validate`,
        {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(body),
          cache: 'no-store',
        },
      );
      if (!validate.ok) throw new Error(`Validation: ${explain(validate)}`);
      const accept = await fetch(
        `/api/case-batch?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`,
        {
          method: 'POST',
          headers: { 'content-type': 'application/json', 'idempotency-key': idempotencyKey },
          body: JSON.stringify(body),
          cache: 'no-store',
        },
      );
      if (!accept.ok) throw new Error(explain(accept));
      const report = (await accept.json()) as BatchReport;
      onDone(
        report.status === 'accepted'
          ? `Observation batch accepted (${report.accepted_count} records). Publication remains separate.`
          : `Batch ${report.status}: ${report.accepted_count} accepted, ${report.rejected_count} rejected, ${report.quarantined_count} quarantined. ${report.next_action}`,
      );
      setIdempotencyKey(`editor-${crypto.randomUUID()}`);
    } catch (error) {
      onDone(error instanceof Error ? error.message : 'Observation batch failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" aria-label="Editor observation workflow">
      <h2>Add or correct an observation</h2>
      <p>
        Editors stage source-backed records only. A staged artifact carries its private source rows; this form
        validates the artifact then accepts it as one atomic batch. Publication follows its separate contract.
        Idempotency keys are retained when a response is lost. Diagnose a correction by opening the exact record
        above and using its drill-down; corrections append evidence rather than overwriting it.
      </p>
      <p>
        <label htmlFor="editor-artifact">Staged source artifact ID </label>
        <input
          id="editor-artifact"
          value={artifact}
          onChange={event => setArtifact(event.target.value.trim())}
          placeholder="artifact UUID"
          inputMode="text"
        />
      </p>
      <p>
        The editable observation payload lives inside the staged private source artifact (uploaded by an
        administrator through the review panel below). This keeps the browser from inventing clinical values.
      </p>
      <p>
        <button type="button" disabled={busy} onClick={() => void validateThenAccept()}>
          Validate then accept batch
        </button>
      </p>
      <p>Corrections append evidence; retractions require a concrete reason and retain history above.</p>
    </section>
  );
}

function AdminImportReview({
  project,
  patient,
  onDone,
}: {
  project: string;
  patient: string;
  onDone: (note: string) => void;
}) {
  const [artifacts, setArtifacts] = useState<string>('No staged sources loaded yet.');
  async function loadSources() {
    try {
      const response = await fetch(
        `/api/case-sources?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`,
        { cache: 'no-store' },
      );
      if (!response.ok) throw new Error(explain(response));
      const body = await response.text();
      setArtifacts(body.slice(0, 2000));
      onDone('Staged sources loaded. Upload completion is not publication; rights and QC decide approval.');
    } catch (error) {
      onDone(error instanceof Error ? error.message : 'Source review unavailable.');
    }
  }
  return (
    <section className="card" aria-label="Limited admin import review">
      <h2>Data administration review</h2>
      <p>
        Admins review staged artifacts with rights, linkage and QC evidence. An unapproved import can never become an
        approved case from this screen, and the browser never solicits real patient uploads from visitors.
      </p>
      <p>
        <button type="button" onClick={() => void loadSources()}>
          Load staged source review
        </button>
      </p>
      <pre aria-live="polite">{artifacts}</pre>
    </section>
  );
}
