'use client';

import { useEffect, useRef, useState } from 'react';
import type { components } from '../../../packages/contracts/generated/api';
import { TimeLabel } from './research';

type S = components['schemas'];

export function RevisionUpdatePanel({query, baseUrl}: {query: S['TimelineQuery']; baseUrl: string}) {
  async function request<T>(action: string, signal: AbortSignal, body?: unknown, idempotencyKey?: string): Promise<T> {
    const headers: Record<string, string> = {};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
    const response = await fetch(baseUrl + '&action=' + action, {method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store', credentials: 'omit', redirect: 'error', signal});
    if (!response.ok) throw new Error(response.status === 401 || response.status === 403 ? 'Access denied for this revision update.' : 'Revision update request failed (status ' + response.status + ').');
    return (await response.json()) as T;
  }
  const [view, setView] = useState<S['DependentUpdateView'] | null>(null);
  const [receipt, setReceipt] = useState<S['DependentUpdateReceipt'] | null>(null);
  const [job, setJob] = useState<S['ImagingJobRecord'] | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('Check update status explicitly. Opening this view does not queue or publish work.');
  const pending = useRef<AbortController | null>(null);
  const retries = useRef(new Map<string, string>());
  useEffect(() => () => {pending.current?.abort();}, []);
  const scope = query.window.scope;
  const latest = 'updates-latest' + (scope.mode === 'simulation' && scope.branch_id ? '&branch_id=' + encodeURIComponent(scope.branch_id) : '');
  async function act(action: (signal: AbortSignal) => Promise<void>) {
    pending.current?.abort(); const controller = new AbortController(); pending.current = controller; setBusy(true);
    try {await action(controller.signal);} catch (error) {if (!controller.signal.aborted) {const detail = error instanceof Error ? error.message : 'Update request unavailable. Keep the loaded exact view and retry this request.'; if (detail.startsWith('Access denied')) {setView(null); setReceipt(null); setJob(null);} setMessage(detail);}}
    finally {if (!controller.signal.aborted) setBusy(false);}
  }
  async function refresh(signal: AbortSignal) {
    const result = await request<S['DependentUpdateView']>(latest, signal);
    if (signal.aborted) return;
    setView(result); setJob(previous => previous?.id === result.job_id ? previous : null); setMessage(result.next_action);
  }
  async function queue(signal: AbortSignal) {
    const event = view?.eligible_event;
    if (!view || !event || scope.mode !== 'source_fixture' || event.revision !== scope.data_revision || event.revision !== view.current_patient_revision) return;
    const body: S['DependentUpdateInput'] = {event_id: event.event_id, expected_revision: event.revision, revision_hash: event.revision_hash, timeline: {...query, cursor: null}, state_input: null};
    const fingerprint = JSON.stringify(body);
    if (!retries.current.has(fingerprint)) retries.current.set(fingerprint, crypto.randomUUID());
    const result = await request<S['DependentUpdateReceipt']>('updates', signal, body, retries.current.get(fingerprint));
    if (signal.aborted) return;
    if (result.event_id !== event.event_id || result.data_revision !== event.revision) throw new Error('Update receipt does not match the selected revision. Keep the loaded exact view.');
    retries.current.delete(fingerprint); setReceipt(result); setJob(null); setMessage(result.next_action);
    await refresh(signal);
  }
  const jobId = view?.job_id ?? receipt?.job_id;
  async function refreshJob(signal: AbortSignal) {
    if (!jobId) return;
    const result = await request<S['ImagingJobRecord']>('job&job=' + encodeURIComponent(jobId), signal);
    if (signal.aborted) return;
    if (result.id !== jobId || result.operation !== 'dependent_update') throw new Error('Worker status does not match the revision update. Keep the loaded exact view.');
    setJob(result); await refresh(signal);
  }
  async function cancelJob(signal: AbortSignal) {
    if (!jobId) return;
    const result = await request<S['ImagingJobRecord']>('job-cancel&job=' + encodeURIComponent(jobId), signal, {});
    if (signal.aborted) return;
    if (result.id !== jobId || result.operation !== 'dependent_update') throw new Error('Cancellation receipt does not match the revision update.');
    setJob(result); setMessage(result.cancel_requested && result.status !== 'cancelled' ? 'Cancellation requested. Refresh worker status for server acknowledgement; the loaded view is retained.' : result.next_action);
  }
  const canQueue = scope.mode === 'source_fixture' && !!view?.eligible_event && view.eligible_event.revision === scope.data_revision && view.current_patient_revision === scope.data_revision && view.restrictions.every(reason => reason === 'retained_view_is_historical_revision') && !receipt && !(['pending', 'failed'].includes(view.status) && view.requested_revision === view.current_patient_revision);
  const jobStatus = job?.status ?? view?.job_status ?? (receipt ? 'queued' : null);
  const activeJob = jobStatus !== null && ['queued', 'running'].includes(jobStatus);
  const ready = view?.last_ready;
  return <section aria-label="Revision update status"><h2>Revision updates</h2>
    <p>The loaded timeline remains pinned to revision {scope.data_revision}. Updates keep its selected patient, branch and observation time; no new values replace it automatically.</p>
    {scope.mode === 'observed' ? <p>Observed-source worker execution is not enabled. Source observations remain readable through their existing authorized window.</p> : <>
      <button disabled={busy} onClick={() => void act(refresh)}>Check revision update status</button>
      <p role="status" aria-live="polite">{message}</p>
      {view && <><p>Update status: {view.status}. Current patient revision: {view.current_patient_revision}. Requested revision: {view.requested_revision ?? 'None'}. Worker: {view.job_status ?? 'None'}.</p>
        <p>Baseline: {view.baseline_superseded ? 'Superseded; keep its pinned hash and create a new branch for a changed baseline.' : 'No baseline replacement reported.'}</p>
        {view.restrictions.map(reason => <p key={reason}>Update restriction: {reason}</p>)}
        {ready ? <details open><summary>Last valid derived view · revision {ready.data_revision}</summary><p>Report ID: {ready.id}. Status: {ready.status}. State ID: {ready.state_id ?? 'None; no state was inferred'}. Scope: {ready.scope_key}.</p><p>This retained report is separate from the loaded timeline. Geometry recomputed: {String(ready.geometry_recomputed)}. Publication: {ready.publication}. Scientific review: {ready.scientific_review}.</p><p>Original derived event cutoff: {ready.trends.window.event_cutoff ? <TimeLabel time={ready.trends.window.event_cutoff}/> : 'No event cutoff; full pinned window'}. Knowledge cutoff: {ready.trends.window.knowledge_as_of}.</p><details><summary>Exact retained report and dependency hashes</summary><pre>{JSON.stringify(ready, null, 2)}</pre></details></details> : <p>No valid derived report is available. The loaded timeline is retained.</p>}
        {view.status === 'failed' && <p>A dependent calculation failed. Keep the last valid view; inspect the worker error and use the documented corrected-revision or recovery action. Status refresh never creates another job.</p>}
        {scope.mode === 'source_fixture' ? <><p>Explicit fixture recomputation uses the accepted event and exact loaded revision/window. It does not create state membership or rebuild a mesh.</p><button disabled={busy || !canQueue} onClick={() => void act(queue)}>Queue accepted fixture revision</button>{view.eligible_event && view.eligible_event.revision !== scope.data_revision && <p>The accepted event is revision {view.eligible_event.revision}. Load that exact source-fixture revision before queueing; the current selection remains unchanged.</p>}</> : <p>Branch history remains pinned. Creating or rebasing branch states requires an explicit membership command; this status view does not regenerate a scenario.</p>}
      </>}
      {receipt && <p>Queued revision: {receipt.data_revision}. Event: {receipt.event_id}. Job: {receipt.job_id}. Publication remains separate.</p>}
      {jobId && <><button disabled={busy} onClick={() => void act(refreshJob)}>Refresh revision worker</button><button disabled={busy || !activeJob || !!job?.cancel_requested} onClick={() => void act(cancelJob)}>Cancel revision worker</button></>}
      {job && <p>Revision worker: {job.status} · stage {job.stage}. {job.cancel_requested && job.status !== 'cancelled' ? 'Cancellation requested; awaiting server acknowledgement. ' : ''}{job.error_code ? `Error: ${job.error_code}. ` : ''}{job.next_action}</p>}
    </>}
  </section>;
}
