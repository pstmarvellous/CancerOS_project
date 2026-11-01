'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import type { components } from '../../../packages/contracts/generated/api';
import { ErrorSummary, LoadingState, ProvenanceBadge } from './research';
import { StateFusionView } from './state-fusion-view';

type S = components['schemas'];
type BranchPage = S['BranchPage'];
type StatePage = S['StatePage'];
type StateView = S['StateView'];

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function initialParams(): { project: string | null; patient: string | null; branch: string | null; state: string | null; compare: string | null } {
  if (typeof window === 'undefined') return { project: null, patient: null, branch: null, state: null, compare: null };
  const params = new URLSearchParams(window.location.search);
  return {
    project: params.get('project'),
    patient: params.get('patient'),
    branch: params.get('branch'),
    state: params.get('state'),
    compare: params.get('compare'),
  };
}

type LoadedBranch = { id: string; mode: string };
type LoadedState = { view: StateView; fusion: S['FusionReport'] | null };

async function readJson(response: Response): Promise<unknown> {
  const text = await response.text();
  return text ? (JSON.parse(text) as unknown) : null;
}

function explain(status: number): string {
  if (status === 401) return 'Sign in with an authorized session, then retry. A viewer cannot bypass project rights.';
  if (status === 403) return 'This case, branch or state is restricted for your role. Ask an administrator for access.';
  if (status === 404) return 'The requested branch or state is unavailable in this authorized case. Check the selection.';
  return `The authorized read failed (status ${status}).`;
}

export function StateTimelineExplorer() {
  const [initial] = useState(initialParams);
  return <StateTimelineBody initialProject={initial.project} initialPatient={initial.patient} initialBranch={initial.branch} initialState={initial.state} initialCompare={initial.compare} />;
}

function StateTimelineBody({ initialProject, initialPatient, initialBranch, initialState, initialCompare }: {
  initialProject: string | null; initialPatient: string | null; initialBranch: string | null; initialState: string | null; initialCompare: string | null;
}) {
  const project = initialProject;
  const patient = initialPatient;
  const [branches, setBranches] = useState<LoadedBranch[] | null>(null);
  const [branch, setBranch] = useState<string | null>(initialBranch);
  const [states, setStates] = useState<StateView[] | null>(null);
  const [stateId, setStateId] = useState<string | null>(initialState);
  const [compareId, setCompareId] = useState<string | null>(initialCompare);
  const [loaded, setLoaded] = useState<LoadedState | null>(null);
  const [compared, setCompared] = useState<LoadedState | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [status, setStatus] = useState<'needs-selection' | 'loading' | 'ready' | 'failed'>('needs-selection');
  const [message, setMessage] = useState('Observed history and hypothetical branches stay labeled; nothing is interpolated.');
  const [slider, setSlider] = useState(0);
  const requestId = useRef(0);
  const pending = useRef<AbortController | null>(null);
  useEffect(() => () => pending.current?.abort(), []);

  useEffect(() => {
    if (project && patient) void loadBranches(project, patient);
    // One-shot case bind; later navigation changes flow through branch/state pickers.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function authorized<T>(path: string, signal: AbortSignal): Promise<T> {
    const response = await fetch(path, { cache: 'no-store', signal });
    if (!response.ok) {
      const error = new Error(explain(response.status)) as Error & { status: number };
      error.status = response.status;
      throw error;
    }
    return (await readJson(response)) as T;
  }

  async function loadBranches(nextProject: string, nextPatient: string) {
    const key = ++requestId.current;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setStatus('loading');
    setMessage('Loading authorized branches and states…');
    try {
      const page = await authorized<BranchPage>(
        `/api/state-timeline?project=${encodeURIComponent(nextProject)}&patient=${encodeURIComponent(nextPatient)}&resource=branches`,
        controller.signal,
      );
      if (controller.signal.aborted || key !== requestId.current) return;
      const items = page.items.map(item => ({ id: item.branch_id, mode: item.mode }));
      setBranches(items);
      if (!items.length) {
        setStatus('failed');
        setMessage('No twin branches are recorded for this authorized case. No baseline or follow-up is invented.');
        return;
      }
      const validBranch = branch && items.some(item => item.id === branch) ? branch : null;
      const targetBranch = validBranch ?? items[0].id;
      setBranch(targetBranch);
      await loadStates(nextProject, nextPatient, targetBranch, stateId, key, controller);
    } catch (error) {
      if (controller.signal.aborted || key !== requestId.current) return;
      setStatus('failed');
      setMessage(error instanceof Error ? error.message : 'The branch list could not load.');
    }
  }

  async function loadStates(nextProject: string, nextPatient: string, branchId: string, requested: string | null, key: number, controller: AbortController, nextCursor: string | null = null) {
    try {
      const cursorParam = nextCursor ? `&cursor=${encodeURIComponent(nextCursor)}` : '';
      const page = await authorized<StatePage>(
        `/api/state-timeline?project=${encodeURIComponent(nextProject)}&patient=${encodeURIComponent(nextPatient)}&resource=states&branch=${encodeURIComponent(branchId)}${cursorParam}`,
        controller.signal,
      );
      if (controller.signal.aborted || key !== requestId.current) return;
      const combined = nextCursor && states ? [...states, ...page.items] : page.items;
      setStates(combined);
      setCursor(page.next_cursor);
      if (!combined.length) {
        setStatus('failed');
        setMessage('This branch has no persisted discrete states. Drag preview and autoplay are unavailable by design.');
        return;
      }
      const valid = requested && combined.some(item => item.snapshot.id === requested) ? requested : null;
      const target = valid ?? combined[0].snapshot.id;
      setStateId(target);
      setSlider(Math.max(0, combined.findIndex(item => item.snapshot.id === target)));
      await loadState(nextProject, nextPatient, target, false, key, controller);
      if (initialCompare && combined.some(item => item.snapshot.id === initialCompare)) {
        await loadState(nextProject, nextPatient, initialCompare, true, key, controller);
      }
    } catch (error) {
      if (controller.signal.aborted || key !== requestId.current) return;
      setStatus('failed');
      setMessage(error instanceof Error ? error.message : 'The state list could not load.');
    }
  }

  async function loadState(nextProject: string, nextPatient: string, target: string, asComparison: boolean, key: number, controller: AbortController) {
    setStatus('loading');
    if (!asComparison) {
      setLoaded(null);
      setMessage('Loading the exact persisted snapshot… The previous state is cleared while the new one loads.');
    }
    try {
      const view = await authorized<StateView>(
        `/api/state-timeline?project=${encodeURIComponent(nextProject)}&patient=${encodeURIComponent(nextPatient)}&resource=state&state=${encodeURIComponent(target)}`,
        controller.signal,
      );
      if (controller.signal.aborted || key !== requestId.current) return;
      let fusion: S['FusionReport'] | null = null;
      try {
        fusion = await authorized<S['FusionReport']>(
          `/api/state-timeline?project=${encodeURIComponent(nextProject)}&patient=${encodeURIComponent(nextPatient)}&resource=fusion&state=${encodeURIComponent(target)}`,
          controller.signal,
        );
      } catch {
        fusion = null;
      }
      if (controller.signal.aborted || key !== requestId.current) return;
      if (asComparison) setCompared({ view, fusion });
      else {
        setLoaded({ view, fusion });
        setStatus('ready');
        setMessage(`State ${target.slice(0, 8)}… · branch ${view.snapshot.branch_id.slice(0, 8)}… · revision ${view.snapshot.input_revision}. Header, mesh, quantities and interpretation scope belong to this same state.`);
      }
    } catch (error) {
      if (controller.signal.aborted || key !== requestId.current) return;
      if (asComparison) {
        setCompared(null);
        setMessage(error instanceof Error ? error.message : 'The comparison state could not load.');
      } else {
        setStatus('failed');
        setMessage(error instanceof Error ? error.message : 'The selected state could not load.');
      }
    }
  }

  function switchBranch(next: string) {
    if (!project || !patient || !UUID.test(next) || next === branch) return;
    const key = ++requestId.current;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setBranch(next);
    setStates(null);
    setStateId(null);
    setCompareId(null);
    setLoaded(null);
    setCompared(null);
    setCursor(null);
    setStatus('loading');
    setMessage('Branch changed. Resolving an existing persisted state on the new branch; no day is assumed.');
    void loadStates(project, patient, next, null, key, controller);
  }

  function switchState(next: string) {
    if (!project || !patient || !UUID.test(next) || next === stateId) return;
    const key = ++requestId.current;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setStateId(next);
    if (states) setSlider(Math.max(0, states.findIndex(item => item.snapshot.id === next)));
    void loadState(project, patient, next, false, key, controller);
  }

  function step(delta: 1 | -1) {
    if (!states || !states.length) return;
    const next = Math.min(states.length - 1, Math.max(0, slider + delta));
    setSlider(next);
    switchState(states[next].snapshot.id);
  }

  function pinComparison(next: string | null) {
    if (!project || !patient) return;
    setCompareId(next);
    if (!next) {
      setCompared(null);
      return;
    }
    if (next === stateId) {
      setCompared(loaded);
      return;
    }
    const key = ++requestId.current;
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    void loadState(project, patient, next, true, key, controller);
  }

  function describeTime(snapshot: StateView['snapshot']): string {
    return `${snapshot.time.time_domain === 'simulation' ? 'Simulation' : 'Source-relative'} day ${snapshot.time.value}`;
  }

  if (!project || !patient) {
    return (
      <section className="card">
        <h2>Open a case to inspect its history</h2>
        <p>
          The timeline binds to the active case selection. <Link href="/cases">Open an authorized case</Link>, then
          return here. The browser never guesses a project or patient.
        </p>
      </section>
    );
  }

  const indexLabel = states && states.length ? `Observation sequence ${slider + 1} of ${states.length}` : 'No persisted states';
  const comparisonTarget = compareId && states ? states.find(item => item.snapshot.id === compareId) ?? null : null;
  const comparability = loaded && compared
    ? loaded.view.snapshot.branch_id === compared.view.snapshot.branch_id
      ? 'Same-branch discrete states · matched physical display scale; spatial alignment is not established unless a permitted registration/QC record says so.'
      : 'Cross-branch discrete states · sequential comparison only; spatial alignment not established.'
    : null;

  return (
    <div>
      <p role="status" aria-live="polite">{message}</p>
      <p>
        Case: {patient.slice(0, 8)}… · Branch: {branch ? `${branch.slice(0, 8)}…` : 'select below'} · State:{' '}
        {stateId ? `${stateId.slice(0, 8)}…` : 'select below'} ·{' '}
        <Link href={`/cases/detail?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`}>Back to case profile</Link>
      </p>
      {status === 'loading' && !loaded ? <LoadingState /> : null}
      {status === 'failed' && !loaded ? <ErrorSummary message={message} /> : null}
      {branches && branches.length > 0 ? (
        <p>
          <label htmlFor="branch-picker">History rail </label>
          <select id="branch-picker" value={branch ?? ''} onChange={event => switchBranch(event.target.value)}>
            {branches.map(item => (
              <option key={item.id} value={item.id}>
                {item.mode === 'observed' ? 'Real observed history' : `Hypothetical branch ${item.id.slice(0, 8)}…`} · {item.mode}
              </option>
            ))}
          </select>
        </p>
      ) : null}
      {states && states.length > 0 ? (
        <section aria-label="Persisted state selection">
          <h2>Persisted discrete states</h2>
          <p>{indexLabel}. Branch begins at the shared observed baseline followed by labeled simulated follow-ups. Lab-only states carry no current scan.</p>
          <div>
            <button type="button" onClick={() => step(-1)} disabled={slider <= 0}>Previous state</button>
            <label htmlFor="state-slider"> State slider
              <input
                id="state-slider"
                type="range"
                min={0}
                max={states.length - 1}
                step={1}
                value={slider}
                onChange={event => {
                  const next = Number(event.target.value);
                  setSlider(next);
                  switchState(states[next].snapshot.id);
                }}
                aria-valuetext={states[slider] ? `${describeTime(states[slider].snapshot)} · revision ${states[slider].snapshot.input_revision}` : indexLabel}
              />
            </label>
            <button type="button" onClick={() => step(1)} disabled={slider >= states.length - 1}>Next state</button>
          </div>
          <p>
            <label htmlFor="state-picker">State list equivalent </label>
            <select id="state-picker" value={stateId ?? ''} onChange={event => switchState(event.target.value)}>
              {states.map((item, index) => (
                <option key={item.snapshot.id} value={item.snapshot.id}>
                  {index + 1}. {describeTime(item.snapshot)} · {item.snapshot.origin} · rev {item.snapshot.input_revision}
                </option>
              ))}
            </select>
          </p>
          <ol>
            {states.map((item, index) => (
              <li key={item.snapshot.id} aria-current={item.snapshot.id === stateId ? 'true' : undefined}>
                <button type="button" onClick={() => switchState(item.snapshot.id)}>
                  {index + 1}. {describeTime(item.snapshot)}
                </button>{' '}
                <ProvenanceBadge origin={item.snapshot.origin} /> · rev {item.snapshot.input_revision} · {item.snapshot.status}
              </li>
            ))}
          </ol>
          {cursor ? (
            <p>
              <button
                type="button"
                onClick={() => {
                  if (!branch) return;
                  const key = ++requestId.current;
                  const controller = new AbortController();
                  pending.current?.abort();
                  pending.current = controller;
                  void loadStates(project, patient, branch, stateId, key, controller, cursor);
                }}
              >
                Load more persisted states
              </button>
            </p>
          ) : null}
        </section>
      ) : null}
      {loaded ? (
        <section aria-label="Selected state detail">
          <h2>Selected state</h2>
          <p>
            State {loaded.view.snapshot.id.slice(0, 8)}… · <ProvenanceBadge origin={loaded.view.snapshot.origin} /> ·{' '}
            {describeTime(loaded.view.snapshot)} · revision {loaded.view.snapshot.input_revision} · {loaded.view.snapshot.status}
          </p>
          <p>DCE phases and examinations use separate selectors; phase changes never create visits. Historical geometry is opt-in with its own source time.</p>
          {loaded.view.stale ? <p>Historical revision or association head; current use is restricted.</p> : null}
          {loaded.view.restrictions.map(reason => <p key={reason}>Restriction: {reason}</p>)}
          {loaded.fusion ? <StateFusionView report={loaded.fusion} /> : <p>Exact state overview is unavailable for this state. No state is inferred.</p>}
        </section>
      ) : null}
      {states && states.length > 0 ? (
        <section aria-label="Two-state comparison">
          <h2>Pin A/B two-state comparison</h2>
          <p>Comparison uses persisted snapshots only. Server temporal records are authoritative; the browser recomputes no quantities.</p>
          <p>
            <label htmlFor="compare-a">Pin A (current state) </label>
            <select id="compare-a" value={stateId ?? ''} onChange={event => switchState(event.target.value)}>
              {states.map(item => (
                <option key={item.snapshot.id} value={item.snapshot.id}>
                  {describeTime(item.snapshot)} · {item.snapshot.id.slice(0, 8)}…
                </option>
              ))}
            </select>
          </p>
          <p>
            <label htmlFor="compare-b">Pin B </label>
            <select id="compare-b" value={compareId ?? ''} onChange={event => pinComparison(event.target.value || null)}>
              <option value="">No comparison pinned</option>
              {states.filter(item => item.snapshot.id !== stateId).map(item => (
                <option key={item.snapshot.id} value={item.snapshot.id}>
                  {describeTime(item.snapshot)} · {item.snapshot.id.slice(0, 8)}…
                </option>
              ))}
            </select>
          </p>
          {comparability ? <p>{comparability}</p> : <p>Pin a second persisted state to compare. Unregistered views state that spatial alignment is not established.</p>}
          {compared && comparisonTarget ? (
            <div>
              <h3>Side-by-side persisted states</h3>
              <p>
                A: {loaded?.view.snapshot.id.slice(0, 8) ?? '—'} · {loaded ? describeTime(loaded.view.snapshot) : '—'} ·{' '}
                {loaded ? <ProvenanceBadge origin={loaded.view.snapshot.origin} /> : null}
              </p>
              <p>
                B: {comparisonTarget.snapshot.id.slice(0, 8)}… · {describeTime(comparisonTarget.snapshot)} ·{' '}
                <ProvenanceBadge origin={comparisonTarget.snapshot.origin} />
              </p>
              {compared.fusion && compared.fusion.temporal_changes.length > 0 ? (
                <ul>
                  {compared.fusion.temporal_changes.map((change, index) => (
                    <li key={index}>
                      <p>{change.description}</p>
                      <p>Status: {change.status} · Method: {change.method} · Context: {change.comparison_context}</p>
                      {change.absolute_change ? <p>Absolute change: {change.absolute_change}</p> : null}
                      {change.elapsed_days ? <p>Elapsed days: {change.elapsed_days}</p> : null}
                      <p>Reasons: {change.reason_codes.join(' · ') || 'No additional reason codes'}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No compatible server temporal comparison is available for this pair. Tumor and clinical directions stay independent; no overall score is shown.</p>
              )}
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
