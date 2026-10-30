import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { components } from '../../../packages/contracts/generated/api';
import { RevisionUpdatePanel } from './revision-update-panel';

type S = components['schemas'];
const id = '00000000-0000-4000-8000-000000000001';
const jobId = '00000000-0000-4000-8000-000000000002';
const hash = 'a'.repeat(64);
const query: S['TimelineQuery'] = {window: {scope: {mode: 'source_fixture', data_revision: 3}, knowledge_as_of: '2026-10-29T16:00:00Z', event_cutoff: null}, completion_id: null, cursor: null, limit: 25};
function ready(): S['DependentUpdateReport'] {
  return {version: 'dependent-update/1', id, event_id: id, data_revision: 2, revision_hash: hash, scope_key: 'source_fixture', status: 'ready', features: {version: 'temporal-features/1', scope: {...query.window.scope, data_revision: 2}, series: [], selected_point_ids: [], unresolved_point_ids: [], treatment_point_ids: []}, trends: {version: 'temporal-trends/1', window: {...query.window, scope: {...query.window.scope, data_revision: 2}}, tolerance: '0', series: [], comparison: null, interpretation: 'descriptive_only_no_clinical_significance_or_response_class'}, fusion: null, state_id: null, dependency_hashes: {clinical_membership: hash}, input_dependency_hashes: {revision: hash}, source_ids: [id], restrictions: [], geometry_recomputed: false, scientific_review: 'pending', publication: 'draft', next_action: 'Inspect retained result'};
}
function view(status: S['DependentUpdateView']['status'] = 'stale'): S['DependentUpdateView'] {
  return {status, current_patient_revision: 3, requested_revision: 3, job_id: status === 'pending' || status === 'failed' ? jobId : null, job_status: status === 'pending' ? 'queued' : status === 'failed' ? 'failed' : null, last_ready: ready(), restrictions: [], baseline_superseded: false, eligible_event: {event_id: id, revision: 3, revision_hash: hash}, next_action: 'Inspect update dependencies'};
}
const receipt: S['DependentUpdateReceipt'] = {event_id: id, job_id: jobId, data_revision: 3, scope_key: 'source_fixture', status: 'queued', next_action: 'Refresh worker status'};

describe('explicit revision update controls', () => {
  it.each(['stale', 'pending', 'failed'] as const)('allows a newly accepted revision after an older %s calculation without discarding the retained report', async status => {
    const older = {...view(status), requested_revision: 2, restrictions: ['retained_view_is_historical_revision']};
    const request = vi.fn().mockResolvedValueOnce(older).mockResolvedValueOnce(receipt).mockResolvedValueOnce(view('pending'));
    render(<RevisionUpdatePanel query={query} request={request}/>);
    fireEvent.click(screen.getByRole('button', {name:'Check revision update status'}));
    await screen.findByText('Last valid derived view · revision 2');
    const queue = screen.getByRole('button', {name:'Queue accepted fixture revision'});
    expect(queue).toBeEnabled(); fireEvent.click(queue);
    await screen.findByText(/Queued revision: 3/);
    expect(request.mock.calls[1][2].expected_revision).toBe(3);
    expect(screen.getByText('Last valid derived view · revision 2')).toBeVisible();
  });
  it('keeps current source restrictions distinct from historical freshness', async () => {
    const request = vi.fn().mockResolvedValue({...view(), restrictions:['retained_result_access_restricted']});
    render(<RevisionUpdatePanel query={query} request={request}/>);
    fireEvent.click(screen.getByRole('button', {name:'Check revision update status'}));
    await screen.findByText(/Update restriction: retained_result_access_restricted/);
    expect(screen.getByRole('button', {name:'Queue accepted fixture revision'})).toBeDisabled();
  });
  it.each(['pending', 'current', 'stale', 'failed'] as const)('shows %s separately from the pinned last-valid report without queueing on read', async status => {
    const request = vi.fn().mockResolvedValue(view(status)); render(<RevisionUpdatePanel query={query} request={request}/>);
    expect(request).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', {name: 'Check revision update status'}));
    expect(await screen.findByText(new RegExp(`Update status: ${status}`))).toBeVisible();
    expect(screen.getByText('Last valid derived view · revision 2')).toBeVisible();
    expect(screen.getByText(/loaded timeline remains pinned to revision 3/)).toBeVisible();
    expect(screen.getByText(/no new values replace it automatically/)).toBeVisible();
    expect(request).toHaveBeenCalledTimes(1);
    expect(request.mock.calls[0][0]).toBe('/dependent-updates/latest');
    if (status === 'failed') expect(screen.getByRole('button', {name: 'Queue accepted fixture revision'})).toBeDisabled();
  });
  it('retries a transport failure with the same immutable request key and queues only the explicit selected revision', async () => {
    const request = vi.fn().mockResolvedValueOnce(view()).mockRejectedValueOnce(new Error('Network unavailable; retry the same explicit request.')).mockResolvedValueOnce(receipt).mockResolvedValueOnce(view('pending'));
    render(<RevisionUpdatePanel query={query} request={request}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Check revision update status'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Queue accepted fixture revision'}));
    expect(await screen.findByText('Network unavailable; retry the same explicit request.')).toBeVisible();
    expect(screen.getByText('Last valid derived view · revision 2')).toBeVisible();
    fireEvent.click(screen.getByRole('button', {name: 'Queue accepted fixture revision'}));
    await screen.findByText(/Queued revision: 3/);
    expect(request.mock.calls[1][2]).toEqual({event_id: id, expected_revision: 3, revision_hash: hash, timeline: query, state_input: null});
    expect(request.mock.calls[1][3]).toBeTruthy();
    expect(request.mock.calls[2][3]).toBe(request.mock.calls[1][3]);
    expect(request.mock.calls[2][2]).toEqual(request.mock.calls[1][2]);
    expect(screen.getByText(/Geometry recomputed: false/)).toBeVisible();
  });
  it('keeps a source revision mismatch explicit and uses branch status without enabling branch regeneration', async () => {
    const mismatch = view(); mismatch.eligible_event!.revision = 4;
    const request = vi.fn().mockResolvedValueOnce(mismatch).mockResolvedValueOnce({...view('stale'), baseline_superseded: true});
    const {rerender} = render(<RevisionUpdatePanel query={query} request={request}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Check revision update status'}));
    await screen.findByText(/The accepted event is revision 4/);
    expect(screen.getByRole('button', {name: 'Queue accepted fixture revision'})).toBeDisabled();
    const simulation = {...query, window: {...query.window, scope: {mode: 'simulation' as const, data_revision: 3, branch_id: id, run_id: jobId}}, completion_id: id};
    rerender(<RevisionUpdatePanel key="new-scope" query={simulation} request={request}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Check revision update status'}));
    await screen.findByText(/Superseded; keep its pinned hash/);
    expect(request.mock.calls[1][0]).toBe(`/dependent-updates/latest?branch_id=${id}`);
    expect(screen.queryByRole('button', {name: 'Queue accepted fixture revision'})).toBeNull();
  });
  it('aborts late status results after the selected context is replaced', async () => {
    let finish: (value: S['DependentUpdateView']) => void = () => {};
    const request = vi.fn().mockImplementationOnce(() => new Promise(resolve => {finish = resolve;}));
    const {rerender} = render(<RevisionUpdatePanel query={query} request={request}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Check revision update status'}));
    const signal = request.mock.calls[0][1];
    rerender(<RevisionUpdatePanel key="changed-state" query={query} request={request}/>);
    expect(signal.aborted).toBe(true); finish(view('failed'));
    await waitFor(() => expect(screen.queryByText(/Update status: failed/)).toBeNull());
    expect(screen.getByText(/Opening this view does not queue or publish work/)).toBeVisible();
  });
  it('keeps observed execution gated without sending a worker or status request', () => {
    const request = vi.fn(); render(<RevisionUpdatePanel query={{...query, window: {...query.window, scope: {mode: 'observed', data_revision: 3}}}} request={request}/>);
    expect(screen.getByText(/Observed-source worker execution is not enabled/)).toBeVisible();
    expect(screen.queryByRole('button')).toBeNull(); expect(request).not.toHaveBeenCalled();
  });
  it('requests existing durable-job cancellation without claiming acknowledgement early', async () => {
    const cancelled = {id: jobId, operation: 'dependent_update', status: 'running', stage: 'processing', cancel_requested: true, next_action: 'Refresh worker status'};
    const request = vi.fn().mockResolvedValueOnce(view('pending')).mockResolvedValueOnce(cancelled);
    render(<RevisionUpdatePanel query={query} request={request}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Check revision update status'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Cancel revision worker'}));
    expect(await screen.findByText(/Cancellation requested. Refresh worker status for server acknowledgement/)).toBeVisible();
    expect(request.mock.calls[1][0]).toBe(`/imaging-jobs/${jobId}/cancellations`);
    expect(request.mock.calls[1][2]).toEqual({});
    expect(screen.getByRole('button', {name: 'Cancel revision worker'})).toBeDisabled();
    expect(screen.getByText('Last valid derived view · revision 2')).toBeVisible();
  });
  it('clears a retained derived report when the server denies its current access', async () => {
    const request = vi.fn().mockResolvedValueOnce(view('current')).mockRejectedValueOnce(new Error('Access denied for this project, patient or action.'));
    render(<RevisionUpdatePanel query={query} request={request}/>);
    fireEvent.click(screen.getByRole('button', {name: 'Check revision update status'}));
    await screen.findByText('Last valid derived view · revision 2');
    fireEvent.click(screen.getByRole('button', {name: 'Check revision update status'}));
    await screen.findByText('Access denied for this project, patient or action.');
    expect(screen.queryByText('Last valid derived view · revision 2')).toBeNull();
  });
});

