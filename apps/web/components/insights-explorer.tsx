'use client';

import { Suspense, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import type { components } from '../../../packages/contracts/generated/api';
import { ErrorSummary, LoadingState, ProvenanceBadge } from './research';
import { InterpretationPanel } from './interpretation-panel';

type S = components['schemas'];
type InterpretationReport = S['InterpretationReport'];
type GroundingReport = S['GroundingReport'];
type InterpretationContext = S['InterpretationContext'];

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function initialParams(params: URLSearchParams): { project: string | null; patient: string | null; branch: string | null; state: string | null } {
  return { project: params.get('project'), patient: params.get('patient'), branch: params.get('branch'), state: params.get('state') };
}

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  return text ? (JSON.parse(text) as unknown) : null;
}

function explain(status: number): string {
  if (status === 401) return 'Sign in with an authorized session, then retry. Insights never bypass project rights.';
  if (status === 403) return 'This insight or its evidence is restricted for your role. Ask an administrator for access.';
  if (status === 404) return 'The selected state, interpretation or evidence is unavailable in this authorized case. Check the selection.';
  if (status === 409) return 'Current grounding, safety or source permission blocks display. Verified measurements and tables below remain usable.';
  return `The authorized read failed (status ${status}).`;
}

type LoadedContext = { context: InterpretationContext; fetchedAt: string; stale: boolean };

function shortId(value: string | null | undefined): string {
  return typeof value === 'string' && value ? `${value.slice(0, 8)}…` : 'not recorded';
}

function contextTitle(context: InterpretationContext, fetchedAt: string): string {
  const measurements = context.measurements.length;
  const passages = context.assertions.length;
  const missing = (context.missing_modalities ?? []).join(', ') || 'none recorded';
  return `Snapshot ${shortId(context.context_hash)} · ${measurements} case measurement${measurements === 1 ? '' : 's'} · ${passages} background passage${passages === 1 ? '' : 's'} · missing: ${missing} · loaded ${fetchedAt}`;
}

function groundingStatus(grounding: GroundingReport | null, report: InterpretationReport | null): string {
  if (!report) return 'Not generated';
  if (report.execution_mode === 'rule_based_summary') return 'Rule-based summary · deterministic template, no external model';
  if (!grounding) return 'Private candidate · grounding not checked yet';
  if (grounding.verdict === 'published') return `Grounded · ${grounding.supported_claims} supported, ${grounding.unsupported_claims} unsupported`;
  return `Not published · grounding ${grounding.verdict} · ${grounding.supported_claims} supported, ${grounding.unsupported_claims} unsupported`;
}

export function InsightsExplorer() {
  return <Suspense fallback={<LoadingState/>}><InsightsFromQuery /></Suspense>;
}

function InsightsFromQuery() {
  const initial = initialParams(useSearchParams());
  const { project, patient } = initial;
  const [branch, setBranch] = useState<string | null>(initial.branch);
  const [stateId, setStateId] = useState<string | null>(initial.state);
  const [context, setContext] = useState<LoadedContext | null>(null);
  const [report, setReport] = useState<InterpretationReport | null>(null);
  const [grounding, setGrounding] = useState<GroundingReport | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [status, setStatus] = useState<'needs-selection' | 'loading' | 'ready' | 'failed'>('needs-selection');
  const [message, setMessage] = useState('Insights stay scoped to one exact snapshot hash, branch, run and state; selection changes cancel stale requests.');
  const [drawer, setDrawer] = useState<string | null>(null);
  const requestId = useRef(0);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  async function authorized<T>(path: string, body: unknown, signal: AbortSignal, idempotencyKey?: string): Promise<T> {
    const headers: Record<string, string> = { 'content-type': 'application/json' };
    if (idempotencyKey) headers['idempotency-key'] = idempotencyKey;
    const response = await fetch(path, { method: 'POST', headers, body: JSON.stringify(body), cache: 'no-store', signal });
    if (!response.ok) {
      const error = new Error(explain(response.status)) as Error & { status: number };
      error.status = response.status;
      throw error;
    }
    return (await readJson(response)) as T;
  }

  async function loadContext(nextState: string) {
    if (!project || !patient) return;
    const key = ++requestId.current;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setStatus('loading');
    setReport(null);
    setGrounding(null);
    setSavedId(null);
    setDrawer(null);
    setContext(null);
    setMessage('Loading the exact snapshot-bound research context… The previous result is cleared while the new one loads.');
    try {
      const loaded = await authorized<InterpretationContext>(
        `/api/insights?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&action=context&state=${encodeURIComponent(nextState)}`,
        { branch_id: branch && UUID.test(branch) ? branch : undefined },
        controller.signal,
      );
      if (controller.signal.aborted || key !== requestId.current) return;
      setContext({ context: loaded, fetchedAt: new Date().toISOString(), stale: false });
      setStatus('ready');
      setMessage(`Context bound to snapshot ${loaded.context_hash.slice(0, 12)}… · exportable: ${loaded.exportable ? 'yes' : 'no; policy or access gates closed'}. Findings below stay within this hash.`);
    } catch (error) {
      if (controller.signal.aborted || key !== requestId.current) return;
      setStatus('failed');
      setMessage(error instanceof Error ? error.message : 'The insight context could not load. Verified measurements and tables remain usable.');
    }
  }

  async function generateSummary(mode: 'rule_based' | 'external_private') {
    if (!project || !patient || !stateId || !context) return;
    const key = ++requestId.current;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setStatus('loading');
    setMessage(mode === 'rule_based' ? 'Generating the deterministic rule-based summary for this exact context…' : 'Requesting a separately permitted private candidate; nothing streams and nothing publishes automatically…');
    try {
      const loaded = await authorized<InterpretationReport>(
        `/api/insights?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&action=interpret&state=${encodeURIComponent(stateId)}`,
        { mode },
        controller.signal,
      );
      if (controller.signal.aborted || key !== requestId.current) return;
      setReport(loaded);
      setStatus('ready');
      setMessage(
        loaded.execution_mode === 'rule_based_summary'
          ? `Rule-based summary ready · snapshot ${loaded.snapshot_hash.slice(0, 12)}… · context ${loaded.context_hash.slice(0, 12)}….`
          : 'Private external candidate ready for grounding review. Nothing is published; run grounding before saving.',
      );
    } catch (error) {
      if (controller.signal.aborted || key !== requestId.current) return;
      setStatus('failed');
      setMessage(error instanceof Error ? error.message : 'Summary generation failed. Verified measurements and tables remain usable.');
    }
  }

  async function checkGrounding() {
    if (!project || !patient || !stateId || !report) return;
    const key = ++requestId.current;
    const controller = new AbortController();
    pending.current?.abort();
    pending.current = controller;
    setMessage('Checking grounding against the exact context snapshot…');
    try {
      const loaded = await authorized<GroundingReport>(
        `/api/insights?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&action=ground&state=${encodeURIComponent(stateId)}`,
        { interpretation: report },
        controller.signal,
      );
      if (controller.signal.aborted || key !== requestId.current) return;
      setGrounding(loaded);
      setMessage(
        loaded.verdict === 'published'
          ? `Grounding passed · ${loaded.supported_claims} supported, ${loaded.unsupported_claims} unsupported.`
          : `Grounding ${loaded.verdict} · ${loaded.supported_claims} supported, ${loaded.unsupported_claims} unsupported. Withheld prose stays withheld; inspect reasons below.`,
      );
    } catch (error) {
      if (controller.signal.aborted) return;
      setMessage(error instanceof Error ? error.message : 'Grounding failed. Verified measurements and tables remain usable.');
    }
  }

  async function saveResult() {
    if (!project || !patient || !stateId || !report) return;
    const fingerprint = `${stateId}:${report.snapshot_hash}:${report.context_hash}`;
    const response = await fetch(
      `/api/insights?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&action=save&state=${encodeURIComponent(stateId)}`,
      { method: 'POST', headers: { 'content-type': 'application/json', 'idempotency-key': `insight-${fingerprint}`.slice(0, 80) }, body: JSON.stringify({ interpretation: report }), cache: 'no-store' },
    );
    if (!response.ok) {
      setMessage(explain(response.status));
      return;
    }
    const body = (await readJson(response)) as { id?: string };
    if (typeof body.id === 'string') {
      setSavedId(body.id);
      setMessage(`Saved result ${body.id.slice(0, 8)}… recorded. Publication and scientific review remain separate gates.`);
    }
  }

  if (!project || !patient) {
    return (
      <section className="card">
        <h2>Open a case to inspect its insights</h2>
        <p>
          Insights bind to the active workspace case. <Link href="/cases">Open an authorized case</Link>, then use
          its Timeline or Charts tab to pick a state first. The browser never guesses a project or patient.
        </p>
      </section>
    );
  }

  return (
    <div>
      <p role="status" aria-live="polite">{message}</p>
      <p>
        Case: {patient.slice(0, 8)}… · State: {stateId ? `${stateId.slice(0, 8)}…` : 'enter below'} ·{' '}
        <Link href={`/cases/detail?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}&tab=overview`}>Back to case workspace</Link>
      </p>
      <section aria-label="Insight scope">
        <h2>Exact insight scope</h2>
        <p>Editors may request a research summary with an explicit permitted execution choice; viewers inspect approved results. Never streams private model tokens.</p>
        <p className="field-hint">Tip: open the workspace Timeline tab, select a persisted state, then paste its state ID here once. Branch is optional; when omitted the server resolves the owning branch.</p>
        <p>
          <label htmlFor="insight-branch">Branch (optional, authorized list value) </label>
          <input id="insight-branch" value={branch ?? ''} onChange={event => setBranch(event.target.value.trim() || null)} spellCheck={false} placeholder="Optional branch UUID" />
        </p>
        <p>
          <label htmlFor="insight-state">State </label>
          <input id="insight-state" value={stateId ?? ''} onChange={event => setStateId(event.target.value.trim() || null)} spellCheck={false} placeholder="Persisted state UUID from Timeline" />
          <button type="button" disabled={!stateId || !UUID.test(stateId)} onClick={() => stateId && void loadContext(stateId)}>Load exact context</button>
        </p>
      </section>
      {status === 'loading' && !context ? <LoadingState /> : null}
      {status === 'failed' && !context ? (
        <section className="card">
          <ErrorSummary message={message} />
          <p><button type="button" disabled={!stateId || !UUID.test(stateId ?? '')} onClick={() => stateId && void loadContext(stateId)}>Retry authorized load</button></p>
        </section>
      ) : null}
      {context ? (
        <section aria-label="Snapshot-bound context">
          <h2>Snapshot context in plain language</h2>
          <p><strong>{contextTitle(context.context, context.fetchedAt)}</strong></p>
          <p>
            Snapshot hash: {context.context.context_hash.slice(0, 12)}… (advanced reference) ·{' '}
            {context.stale ? 'Superseded for the current timeline; valid for its selected older snapshot. Open the latest view instead of silently changing it.' : 'Current for the selected snapshot.'}
          </p>
          <p>Exportable: {context.context.exportable ? 'yes' : 'no; policy or access gates closed'}. Findings stay within this snapshot.</p>
          <p>Supported findings, changes, missing information and limitations stay in this section. Each finding below opens its exact case observation or approved passage.</p>
          <h3>Case evidence · {context.context.measurements.length} measurement{context.context.measurements.length === 1 ? '' : 's'}</h3>
          <ul>
            {context.context.measurements.map(item => (
              <li key={item.reference_id}>
                <button type="button" onClick={() => setDrawer(drawer === item.reference_id ? null : item.reference_id)}>
                  {drawer === item.reference_id ? 'Close' : 'Open'} measurement {item.reference_id.slice(0, 8)}…
                </button>{' '}
                {item.metric_code ?? 'untyped metric'} · {item.value ?? 'no value'} {item.unit ?? ''} · <ProvenanceBadge origin={item.origin} />
                {drawer === item.reference_id ? (
                  <span> · Case evidence: {item.reference_id}. Source time: {item.member_time}. Unknown uncertainty is not a confidence gauge.</span>
                ) : null}
              </li>
            ))}
          </ul>
          {context.context.assertions.length > 0 ? (
            <details open={false}>
              <summary>Background evidence · {context.context.assertions.length} unreviewed passage{context.context.assertions.length === 1 ? '' : 's'} (not patient-specific support)</summary>
              <p>Metadata-only sources stay metadata-only; a passage link alone is not patient-specific support.</p>
              <ul>
                {context.context.assertions.map(item => (
                  <li key={item.reference_id}>
                    <button type="button" onClick={() => setDrawer(drawer === item.reference_id ? null : item.reference_id)}>
                      {drawer === item.reference_id ? 'Close' : 'Open'} passage {item.reference_id.slice(0, 8)}…
                    </button>{' '}
                    {item.excerpt.slice(0, 120)}
                    {drawer === item.reference_id ? <span> · Background evidence only. Source note: {item.source_note_id}. Certainty: {item.certainty}.</span> : null}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
          {context.context.limitations.map(reason => <p key={reason}>Limitation: {reason}</p>)}
          <div>
            <button type="button" onClick={() => void generateSummary('rule_based')}>Generate rule-based summary</button>{' '}
            <button type="button" onClick={() => void generateSummary('external_private')}>Request private candidate (permitted execution only)</button>
          </div>
        </section>
      ) : null}
      {report ? <InterpretationPanel report={report} groundingStatus={groundingStatus(grounding, report)} /> : null}
      {report && report.execution_mode !== 'rule_based_summary' ? (
        <section aria-label="Grounding and save">
          <h2>Grounding and save</h2>
          <p>Only published and validated output is shown to viewers. A denied external request explains the policy and offers the rule-based summary above.</p>
          <p><button type="button" onClick={() => void checkGrounding()}>Check grounding</button></p>
          {grounding ? (
            <div>
              <p><strong>Grounding status: {grounding.verdict}</strong> · Supported: {grounding.supported_claims} · Unsupported: {grounding.unsupported_claims} · Numeric matched: {grounding.numeric_matched}/{grounding.numeric_statements}</p>
              {grounding.reason_codes.map(reason => <p key={reason}>Grounding reason: {reason}</p>)}
              <p>{grounding.next_action}</p>
            </div>
          ) : null}
          <p><button type="button" disabled={!grounding || grounding.verdict !== 'published'} onClick={() => void saveResult()}>Save grounded result</button></p>
          {savedId ? <p>Saved result: {savedId.slice(0, 8)}… · Safe fallback stays labeled and source-linked.</p> : null}
        </section>
      ) : null}
    </div>
  );
}
