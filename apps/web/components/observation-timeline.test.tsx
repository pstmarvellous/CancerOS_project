import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ObservationTimeline } from './observation-timeline';

vi.mock('next/dynamic', () => ({default: () => function MockRenderer({selected}: {selected: string}) {return <div data-testid="selected-geometry">Geometry {selected}</div>;}}));
vi.mock('./state-fusion-view', () => ({StateFusionView: ({report}: {report: {canonical_state: {snapshot: {id: string}}}}) => <div data-testid="state-fusion-context">State {report.canonical_state.snapshot.id}</div>}));
const project = '00000000-0000-4000-8000-000000000001';
const patient = '00000000-0000-4000-8000-000000000002';
const pointA = '00000000-0000-4000-8000-000000000003';
const pointB = '10000000-0000-4000-8000-000000000004';
const branch = '00000000-0000-4000-8000-000000000005';
const run = '00000000-0000-4000-8000-000000000006';
const completion = '00000000-0000-4000-8000-000000000007';
const origin = '00000000-0000-4000-8000-000000000008';
function point(id: string, geometry = false) {
  return {id, time: {reference: {basis: 'relative_day', value: id === pointA ? '10' : '21', time_domain: 'simulation', timeline_origin_id: origin}, precision: 'relative_day'}, recorded_at: '2026-10-28T12:00:00Z', revision: 1, origin: 'SYNTHETIC_GENERATED', modality: geometry ? 'imaging' : 'laboratory', concept: geometry ? 'numerical_region_volume' : 'hemoglobin', numeric_result: geometry ? {form: 'exact', quantity: {value: '64', unit: 'mm3'}} : {form: 'missing', missing_reason: 'not_collected'}, exact_value: null, ordinal_value: null, instrument: null, instrument_version: null, symptom_presence: null, availability: geometry ? 'available' : 'unavailable', missing_reason: geometry ? null : 'not_collected', conflicts: [], state_ids: [project], geometry_result_id: geometry ? patient : null, lesion_id: null, measurement_basis: geometry ? 'mask_realized' : 'source_record', method_version: 'fixture/1', summary: null, historical_context: false, branch_id: branch, run_id: run, supersedes_id: null};
}
function page(items = [point(pointA)], cursor: string | null = null) {
  return {items, features: {version: 'temporal-features/1', series: [], unresolved_point_ids: [], treatment_point_ids: []}, total_points: 2, next_cursor: cursor, current_patient_revision: 2, historical_revision: true, restrictions: [], next_action: 'Inspect exact observations'};
}
function response(value: unknown, status = 200) {return {ok: status < 400, status, json: async () => value};}
function trends() {
  return {version: 'temporal-trends/1', tolerance: '0', comparison: null, interpretation: 'descriptive_only_no_clinical_significance_or_response_class', series: [{key: 'hemoglobin', concept: 'hemoglobin', metric_definition: null, unit: 'g/dL', lesion_id: null, method_version: 'fixture/1', origin: 'SYNTHETIC_GENERATED', context: 'SYNTHETIC', instrument: null, instrument_version: null, points: [{point_id: pointB, time: point(pointB).time, x_elapsed_days: '21', y: '12', exact_value: '12', label: 'hemoglobin: 12 g/dL', qualifier: null, reason_codes: [], source_ids: [pointB], origin: 'SYNTHETIC_GENERATED', context: 'SYNTHETIC'}], segments: [], endpoint: null, usable_count: 1, description: 'Descriptive observed changes only.'}]};
}
function credentials() {
  fireEvent.change(screen.getByLabelText('Project UUID'), {target: {value: project}});
  fireEvent.change(screen.getByLabelText('Patient UUID'), {target: {value: patient}});
  fireEvent.change(screen.getByLabelText('Access token'), {target: {value: 'fixture-access-token'}});
  fireEvent.change(screen.getByLabelText('Knowledge as of (ISO timestamp with timezone)'), {target: {value: '2026-10-28T13:00:00Z'}});
}
afterEach(() => vi.unstubAllGlobals());

describe('exact observation timeline', () => {
  it('pins the same source window across cursor pages and preserves the first page on cursor rejection', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(page([point(pointA)], 'pinned-cursor'))).mockResolvedValueOnce(response({}, 409)).mockResolvedValueOnce(response(page([point(pointB)])));
    vi.stubGlobal('fetch', fetch); render(<ObservationTimeline/>); credentials();
    fireEvent.change(screen.getByLabelText('Observation context'), {target: {value: 'source_fixture'}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    await screen.findByText('1 loaded of 2 points. Revision 1 · historical revision. Current patient revision: 2.');
    fireEvent.click(screen.getByRole('button', {name: 'Load next pinned page'}));
    await screen.findByText(/Timeline revision, publication, permissions or cursor changed/);
    expect(screen.getByRole('button', {name: 'Inspect 00000000'})).toBeVisible();
    fireEvent.click(screen.getByRole('button', {name: 'Load next pinned page'}));
    await screen.findByRole('button', {name: 'Inspect 10000000'});
    const first = JSON.parse(fetch.mock.calls[0][1].body);
    const next = JSON.parse(fetch.mock.calls[1][1].body);
    expect(first.window.scope).toEqual({mode: 'source_fixture', data_revision: 1});
    expect(next).toEqual({...first, cursor: 'pinned-cursor'});
    expect(JSON.parse(fetch.mock.calls[2][1].body)).toEqual(next);
    expect(screen.queryByText('fixture-access-token')).toBeNull();
    expect(fetch.mock.calls[0][1].headers).not.toHaveProperty('Idempotency-Key');
  });
  it('uses exact simulation identifiers and removes geometry immediately when selecting a missing laboratory point', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(page([point(pointA, true), point(pointB)]))).mockResolvedValueOnce(response({geometry_id: pointA, origin: 'SYNTHETIC_GENERATED', surface: {vertices: []}}));
    vi.stubGlobal('fetch', fetch); render(<ObservationTimeline/>); credentials();
    fireEvent.change(screen.getByLabelText('Observation context'), {target: {value: 'simulation'}});
    for (const [label, value] of [['Branch UUID', branch], ['Run UUID', run], ['Published completion UUID', completion], ['Simulation event cutoff day (optional)', '30'], ['Timeline origin UUID (for cutoff)', origin]]) fireEvent.change(screen.getByLabelText(label), {target: {value}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    await screen.findByRole('button', {name: 'Inspect 00000000'});
    const query = JSON.parse(fetch.mock.calls[0][1].body);
    expect(query.window.scope).toEqual({mode: 'simulation', data_revision: 1, branch_id: branch, run_id: run});
    expect(query.completion_id).toBe(completion);
    expect(query.window.event_cutoff.timeline_origin_id).toBe(origin);
    fireEvent.click(screen.getByRole('button', {name: 'Inspect 00000000'}));
    expect(await screen.findByTestId('selected-geometry')).toHaveTextContent(pointA);
    fireEvent.click(screen.getByRole('button', {name: 'Inspect 10000000'}));
    expect(screen.queryByTestId('selected-geometry')).toBeNull();
    expect(screen.getByText(/No geometry at this observation/)).toBeVisible();
    expect(screen.getAllByText('not_collected').length).toBeGreaterThan(0);
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it('rejects a naive knowledge timestamp and clears a pending selected view when context changes', async () => {
    const fetch = vi.fn(); vi.stubGlobal('fetch', fetch); render(<ObservationTimeline/>); credentials();
    fireEvent.change(screen.getByLabelText('Knowledge as of (ISO timestamp with timezone)'), {target: {value: '2026-10-28T12:00:00'}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    await screen.findByText(/Enter a timezone-aware knowledge cutoff/); expect(fetch).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', {name: 'Clear private view'}));
    await waitFor(() => expect(screen.getByLabelText('Access token')).toHaveValue(''));
    expect(screen.queryByRole('heading', {name: 'Observation points'})).toBeNull();
  });
  it('queries trends over the full pinned window and never substitutes geometry for an unloaded point', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(page([point(pointA)], 'pinned-cursor'))).mockResolvedValueOnce(response(trends()));
    vi.stubGlobal('fetch', fetch); render(<ObservationTimeline/>); credentials();
    fireEvent.change(screen.getByLabelText('Observation context'), {target: {value: 'simulation'}});
    for (const [label, value] of [['Branch UUID', branch], ['Run UUID', run], ['Published completion UUID', completion]]) fireEvent.change(screen.getByLabelText(label), {target: {value}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    await screen.findByRole('button', {name: 'Load descriptive trends for this window'});
    fireEvent.click(screen.getByRole('button', {name: 'Load descriptive trends for this window'}));
    await screen.findByRole('heading', {name: 'Descriptive trends'});
    const original = JSON.parse(fetch.mock.calls[0][1].body);
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({timeline: {...original, cursor: null}, tolerance: '0'});
    expect(fetch.mock.calls[1][0]).toContain('/trend-queries');
    expect(fetch.mock.calls[1][1].credentials).toBe('omit');
    fireEvent.click(screen.getByRole('button', {name: 'Open point 10000000'}));
    expect(screen.getByText(/is not in the loaded timeline pages/)).toBeVisible();
    expect(screen.queryByTestId('selected-geometry')).toBeNull();
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it('aborts a pending trend read and discards its result after context changes', async () => {
    let finish: (value: ReturnType<typeof response>) => void = () => {};
    const fetch = vi.fn().mockResolvedValueOnce(response(page())).mockImplementationOnce(() => new Promise(resolve => {finish = resolve;}));
    vi.stubGlobal('fetch', fetch); render(<ObservationTimeline/>); credentials();
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    await screen.findByRole('button', {name: 'Load descriptive trends for this window'});
    fireEvent.click(screen.getByRole('button', {name: 'Load descriptive trends for this window'}));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    const signal = fetch.mock.calls[1][1].signal;
    fireEvent.change(screen.getByLabelText('Exact data revision'), {target: {value: '2'}});
    expect(signal.aborted).toBe(true);
    finish(response(trends()));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Selection changed. Reload the exact timeline window.'));
    expect(screen.queryByRole('heading', {name: 'Descriptive trends'})).toBeNull();
    expect(screen.queryByRole('heading', {name: 'Observation points'})).toBeNull();
  });
  it('requires explicit selection when one observation belongs to several states and posts the pinned simulation window', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(page([{...point(pointA), state_ids: [project, patient]}]))).mockResolvedValueOnce(response({canonical_state: {snapshot: {id: patient}}}));
    vi.stubGlobal('fetch', fetch); render(<ObservationTimeline/>); credentials();
    fireEvent.change(screen.getByLabelText('Observation context'), {target: {value: 'simulation'}});
    for (const [label, value] of [['Branch UUID', branch], ['Run UUID', run], ['Published completion UUID', completion]]) fireEvent.change(screen.getByLabelText(label), {target: {value}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Inspect 00000000'}));
    expect(screen.getByRole('button', {name: 'Load exact state overview'})).toBeDisabled();
    expect(screen.getByLabelText('Exact state membership')).toHaveValue('');
    fireEvent.change(screen.getByLabelText('Exact state membership'), {target: {value: patient}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact state overview'}));
    expect(await screen.findByTestId('state-fusion-context')).toHaveTextContent(patient);
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({state_id: patient, timeline: {...JSON.parse(fetch.mock.calls[0][1].body), cursor: null}});
    expect(fetch.mock.calls[1][0]).toContain('/fusion-queries');
    fireEvent.change(screen.getByLabelText('Exact state membership'), {target: {value: project}});
    expect(screen.queryByTestId('state-fusion-context')).toBeNull();
  });
  it('aborts and clears fusion on a different point or context and never reuses a late result', async () => {
    let finish: (value: ReturnType<typeof response>) => void = () => {};
    const fetch = vi.fn().mockResolvedValueOnce(response(page([point(pointA), {...point(pointB), state_ids: []}]))).mockImplementationOnce(() => new Promise(resolve => {finish = resolve;}));
    vi.stubGlobal('fetch', fetch); render(<ObservationTimeline/>); credentials();
    fireEvent.change(screen.getByLabelText('Observation context'), {target: {value: 'source_fixture'}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Inspect 00000000'}));
    fireEvent.click(screen.getByRole('button', {name: 'Load exact state overview'}));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({state_id: project, timeline: null});
    const signal = fetch.mock.calls[1][1].signal;
    fireEvent.click(screen.getByRole('button', {name: 'Inspect 10000000'}));
    expect(signal.aborted).toBe(true);
    expect(screen.getByText(/No canonical state membership is available/)).toBeVisible();
    finish(response({canonical_state: {snapshot: {id: project}}}));
    await waitFor(() => expect(screen.queryByTestId('state-fusion-context')).toBeNull());
    fireEvent.change(screen.getByLabelText('Exact data revision'), {target: {value: '2'}});
    expect(screen.queryByRole('heading', {name: 'Exact state overview'})).toBeNull();
  });
  it('keeps authentic observed-state fusion disabled and reports request failure without carrying an old state', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(page())).mockResolvedValueOnce(response(page())).mockResolvedValueOnce(response({}, 403));
    vi.stubGlobal('fetch', fetch); render(<ObservationTimeline/>); credentials();
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Inspect 00000000'}));
    expect(screen.getByText(/Authentic observed-state fusion is not established/)).toBeVisible();
    expect(screen.queryByRole('button', {name: 'Load exact state overview'})).toBeNull();
    fireEvent.change(screen.getByLabelText('Observation context'), {target: {value: 'source_fixture'}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Inspect 00000000'}));
    fireEvent.click(screen.getByRole('button', {name: 'Load exact state overview'}));
    expect(await screen.findByText('Access denied for this timeline context.')).toBeVisible();
    expect(screen.queryByTestId('state-fusion-context')).toBeNull();
    expect(screen.getByRole('button', {name: 'Load exact state overview'})).toBeEnabled();
  });
  it.each(['state', 'context'])('discards pending fusion when its %s selection changes', async change => {
    let finish: (value: ReturnType<typeof response>) => void = () => {};
    const fetch = vi.fn().mockResolvedValueOnce(response(page([{...point(pointA), state_ids: [project, patient]}]))).mockImplementationOnce(() => new Promise(resolve => {finish = resolve;}));
    vi.stubGlobal('fetch', fetch); render(<ObservationTimeline/>); credentials();
    fireEvent.change(screen.getByLabelText('Observation context'), {target: {value: 'source_fixture'}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Inspect 00000000'}));
    fireEvent.change(screen.getByLabelText('Exact state membership'), {target: {value: project}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact state overview'}));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    const signal = fetch.mock.calls[1][1].signal;
    if (change === 'state') fireEvent.change(screen.getByLabelText('Exact state membership'), {target: {value: patient}});
    else fireEvent.change(screen.getByLabelText('Patient UUID'), {target: {value: project}});
    expect(signal.aborted).toBe(true);
    finish(response({canonical_state: {snapshot: {id: project}}}));
    await waitFor(() => expect(screen.queryByTestId('state-fusion-context')).toBeNull());
  });
  it('rejects an overview whose canonical identity differs from the explicitly selected state', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(page())).mockResolvedValueOnce(response({canonical_state: {snapshot: {id: patient}}}));
    vi.stubGlobal('fetch', fetch); render(<ObservationTimeline/>); credentials();
    fireEvent.change(screen.getByLabelText('Observation context'), {target: {value: 'source_fixture'}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Inspect 00000000'}));
    fireEvent.click(screen.getByRole('button', {name: 'Load exact state overview'}));
    expect(await screen.findByText('State overview identity does not match the selected state.')).toBeVisible();
    expect(screen.queryByTestId('state-fusion-context')).toBeNull();
  });
  it('retains the exact selected geometry while updates are pending and aborts old update status after another point is selected', async () => {
    let finish: (value: ReturnType<typeof response>) => void = () => {};
    const pendingView = {status: 'pending', current_patient_revision: 2, requested_revision: 2, job_id: patient, job_status: 'running', last_ready: null, restrictions: [], baseline_superseded: false, eligible_event: null, next_action: 'Keep the last valid selected view'};
    const fetch = vi.fn().mockResolvedValueOnce(response(page([point(pointA, true), point(pointB)]))).mockResolvedValueOnce(response({geometry_id: pointA, origin: 'SYNTHETIC_GENERATED', surface: {vertices: []}})).mockResolvedValueOnce(response(pendingView)).mockImplementationOnce(() => new Promise(resolve => {finish = resolve;}));
    vi.stubGlobal('fetch', fetch); render(<ObservationTimeline/>); credentials();
    fireEvent.change(screen.getByLabelText('Observation context'), {target: {value: 'simulation'}});
    for (const [label, value] of [['Branch UUID', branch], ['Run UUID', run], ['Published completion UUID', completion]]) fireEvent.change(screen.getByLabelText(label), {target: {value}});
    fireEvent.click(screen.getByRole('button', {name: 'Load exact timeline'}));
    fireEvent.click(await screen.findByRole('button', {name: 'Inspect 00000000'}));
    await screen.findByTestId('selected-geometry');
    fireEvent.click(screen.getByRole('button', {name: 'Check revision update status'}));
    await screen.findByText(/Update status: pending/);
    expect(screen.getByTestId('selected-geometry')).toHaveTextContent(pointA);
    expect(screen.getByLabelText('Exact data revision')).toHaveValue('1');
    expect(screen.getByLabelText('Branch UUID')).toHaveValue(branch);
    fireEvent.click(screen.getByRole('button', {name: 'Check revision update status'}));
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(4));
    const signal = fetch.mock.calls[3][1].signal;
    fireEvent.click(screen.getByRole('button', {name: 'Inspect 10000000'}));
    expect(signal.aborted).toBe(true);
    finish(response({...pendingView, status: 'failed'}));
    await waitFor(() => expect(screen.queryByText(/Update status: failed/)).toBeNull());
    expect(screen.queryByTestId('selected-geometry')).toBeNull();
    expect(screen.getByText(/No geometry at this observation/)).toBeVisible();
    expect(fetch.mock.calls.filter(call => call[1].method === 'POST')).toHaveLength(1);
  });
});
