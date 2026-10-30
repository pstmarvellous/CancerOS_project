import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SimulationWorkflow } from './simulation-workflow';

const project = '00000000-0000-4000-8000-000000000001';
const patient = '00000000-0000-4000-8000-000000000002';
const branchId = '00000000-0000-4000-8000-000000000003';
const baselineHash = 'a'.repeat(64);
const config = {branch_id: branchId, baseline_hash: baselineHash, input_revision: 1, scenario: {family: 'SC-02'}, treatment: {category: 'no_specific_assumption'}, geometry_policy: 'none'};
const branch = {id: branchId, baseline_hash: baselineHash, input: {baseline_measurement_id: project}, mode: 'engineering_fixture', observed_baseline_verified: false};
const saved = {id: patient, draft_revision: 1, config_hash: 'b'.repeat(64), config, summary: {disclosure: 'Hypothetical simulation; not a patient-specific prediction', available_actions: ['edit_draft'], blocking_reasons: ['authentic_baseline_and_reviewed_policy_required']}};
function response(value: unknown, status = 200) {return {ok: status < 400, status, json: async () => value};}
function credentials() {
  fireEvent.change(screen.getByLabelText('Project UUID'), {target: {value: project}});
  fireEvent.change(screen.getByLabelText('Patient UUID'), {target: {value: patient}});
  fireEvent.change(screen.getByLabelText('Branch UUID'), {target: {value: branchId}});
  fireEvent.change(screen.getByLabelText('Administrator access token'), {target: {value: 'fixture-token'}});
}
async function baseline() {
  credentials(); fireEvent.click(screen.getByRole('button', {name: 'Load baseline branch'}));
  await screen.findByText('false · engineering_fixture');
}
afterEach(() => vi.unstubAllGlobals());

describe('private simulation workflow', () => {
  it('rejects a saved configuration from another branch without replacing the editable draft', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(branch)).mockResolvedValueOnce(response({publication: null, current_use_allowed: false, restrictions: [], next_action: 'No current run'})).mockResolvedValueOnce(response({...saved, branch_id: project}));
    vi.stubGlobal('fetch', fetch); render(<SimulationWorkflow/>); await baseline();
    fireEvent.change(screen.getByLabelText('Simulation configuration JSON'), {target: {value: '{"draft":"preserve"}'}});
    fireEvent.change(screen.getByLabelText('Saved configuration UUID (optional)'), {target: {value: patient}});
    fireEvent.click(screen.getByRole('button', {name: 'Load saved configuration'}));
    await screen.findByText(/Saved configuration belongs to a different branch/);
    expect(screen.getByLabelText('Simulation configuration JSON')).toHaveValue('{"draft":"preserve"}');
  });
  it('preserves the editable draft after a rejected save and never exposes the token in rendered text', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(branch)).mockResolvedValueOnce(response({publication: null, current_use_allowed: false, restrictions: [], next_action: 'No current run'})).mockResolvedValueOnce(response({}, 422));
    vi.stubGlobal('fetch', fetch); render(<SimulationWorkflow/>); await baseline();
    const draft = JSON.stringify(config, null, 2);
    fireEvent.change(screen.getByLabelText('Simulation configuration JSON'), {target: {value: draft}});
    fireEvent.click(screen.getByRole('button', {name: 'Save immutable draft version'}));
    expect(await screen.findByText(/Configuration rejected/)).toBeVisible();
    expect(screen.getByLabelText('Simulation configuration JSON')).toHaveValue(draft);
    expect(screen.queryByText('fixture-token')).toBeNull();
    expect(screen.getByRole('button', {name: 'Publish complete run privately'})).toBeDisabled();
    const options = fetch.mock.calls[2][1];
    expect(options.headers.Authorization).toBe('Bearer fixture-token');
    expect(options.cache).toBe('no-store'); expect(options.redirect).toBe('error');
  });
  it('keeps normal-development execution disabled after a saved draft and eligibility inspection', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(branch)).mockResolvedValueOnce(response({publication: null, current_use_allowed: false, restrictions: [], next_action: 'No current run'})).mockResolvedValueOnce(response(saved)).mockResolvedValueOnce(response({result: {status: 'insufficient_data', reasons: ['baseline_unverified']}})).mockResolvedValueOnce(response({slots: [{slot_id: 'i1', modality: 'imaging', configured_day: '10', relative_day: '11'}], tumor_targets: [{slot_id: 'i1', target_mm3: null, missing_reason: 'not_acquired'}]}));
    vi.stubGlobal('fetch', fetch); render(<SimulationWorkflow/>); await baseline();
    fireEvent.change(screen.getByLabelText('Simulation configuration JSON'), {target: {value: JSON.stringify(config)}});
    fireEvent.click(screen.getByRole('button', {name: 'Save immutable draft version'}));
    await screen.findByText(/saved revision 1/);
    fireEvent.click(screen.getByRole('button', {name: 'Inspect eligibility and schedule'}));
    await screen.findByText('not_acquired');
    fireEvent.click(screen.getByRole('checkbox'));
    expect(screen.getByRole('button', {name: 'Freeze isolated test run'})).toBeDisabled();
    expect(screen.getByRole('button', {name: 'Generate complete engineering run'})).toBeDisabled();
    expect(screen.getByText(/SYNTHETIC_GENERATED/)).toBeVisible();
    expect(screen.getByText(/Authentic baseline and reviewed scientific-policy gates remain open/)).toBeVisible();
  });
  it('reuses an idempotency key after a failed network write and clears private values explicitly', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(response(branch)).mockResolvedValueOnce(response({publication: null, current_use_allowed: false, restrictions: [], next_action: 'No current run'})).mockRejectedValueOnce(new Error('Network unavailable')).mockResolvedValueOnce(response(saved));
    vi.stubGlobal('fetch', fetch); render(<SimulationWorkflow/>); await baseline();
    fireEvent.change(screen.getByLabelText('Simulation configuration JSON'), {target: {value: JSON.stringify(config)}});
    fireEvent.click(screen.getByRole('button', {name: 'Save immutable draft version'}));
    await screen.findByText('Network unavailable');
    fireEvent.click(screen.getByRole('button', {name: 'Save immutable draft version'}));
    await waitFor(() => expect(screen.getByLabelText('Expected current draft revision')).toHaveValue('1'));
    expect(fetch.mock.calls[2][1].headers['Idempotency-Key']).toBe(fetch.mock.calls[3][1].headers['Idempotency-Key']);
    fireEvent.click(screen.getByRole('button', {name: 'Clear private view'}));
    expect(screen.getByLabelText('Administrator access token')).toHaveValue('');
    expect(screen.getByLabelText('Simulation configuration JSON')).toHaveValue('{}');
  });
  it('requires complete validation and explicit attestation, then publishes against the loaded current pointer', async () => {
    const runId = '00000000-0000-4000-8000-000000000004';
    const completionId = '00000000-0000-4000-8000-000000000005';
    const previousRun = '00000000-0000-4000-8000-000000000006';
    const jobId = '00000000-0000-4000-8000-000000000007';
    const fetch = vi.fn()
      .mockResolvedValueOnce(response(branch))
      .mockResolvedValueOnce(response({publication: {run_id: previousRun}, current_use_allowed: true, restrictions: [], next_action: 'Available'}))
      .mockResolvedValueOnce(response({...saved, summary: {...saved.summary, available_actions: ['freeze_isolated_test_run']}}))
      .mockResolvedValueOnce(response({result: {status: 'insufficient_data'}}))
      .mockResolvedValueOnce(response({slots: [], tumor_targets: []}))
      .mockResolvedValueOnce(response({id: runId, config_hash: saved.config_hash, input_revision: 1}))
      .mockResolvedValueOnce(response({id: jobId, status: 'queued', stage: 'queued', next_action: 'Await worker'}))
      .mockResolvedValueOnce(response({id: jobId, status: 'succeeded', stage: 'completed', result_report_id: completionId, next_action: 'Inspect completion'}))
      .mockResolvedValueOnce(response({id: completionId, branch_id: branchId, run_id: runId, config_hash: saved.config_hash, input_revision: 1, association_head: 3, status: 'ready', stage: 'complete', next_action: 'Explicit private publication required', state_ids: [], validation: {status: 'engineering_passed', findings: [{level: 'V1', status: 'passed', code: 'structure_checked'}], semantic_digest: 'c'.repeat(64)}}))
      .mockResolvedValueOnce(response({id: project}));
    vi.stubGlobal('fetch', fetch); render(<SimulationWorkflow/>); await baseline();
    fireEvent.change(screen.getByLabelText('Simulation configuration JSON'), {target: {value: JSON.stringify(config)}});
    fireEvent.click(screen.getByRole('button', {name: 'Save immutable draft version'}));
    await screen.findByText(/saved revision 1/);
    fireEvent.click(screen.getByRole('button', {name: 'Inspect eligibility and schedule'}));
    await screen.findByText('Eligibility: insufficient_data');
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(screen.getByRole('button', {name: 'Freeze isolated test run'}));
    await waitFor(() => expect(screen.getByRole('button', {name: 'Generate complete engineering run'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button', {name: 'Generate complete engineering run'}));
    await waitFor(() => expect(screen.getByRole('button', {name: 'Refresh worker status'})).toBeEnabled());
    fireEvent.click(screen.getByRole('button', {name: 'Refresh worker status'}));
    await screen.findByText('structure_checked');
    expect(screen.getByRole('button', {name: 'Publish complete run privately'})).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Engineering attestation SHA-256'), {target: {value: 'd'.repeat(64)}});
    fireEvent.click(screen.getByRole('button', {name: 'Publish complete run privately'}));
    await screen.findByText(/Complete run published privately/);
    const publication = JSON.parse(fetch.mock.calls[9][1].body);
    expect(publication.expected_current_run_id).toBe(previousRun);
    expect(publication.expected_association_head).toBe(3);
    expect(publication.expected_config_hash).toBe(saved.config_hash);
    expect(screen.getByRole('button', {name: 'Publish complete run privately'})).toBeDisabled();
  });
});
