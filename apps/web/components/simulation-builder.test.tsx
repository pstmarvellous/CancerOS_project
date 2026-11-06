import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import type { Mock } from 'vitest';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SimulationBuilder } from './simulation-builder';

const project = '00000000-0000-4000-8000-000000000001';
const patient = '00000000-0000-4000-8000-000000000002';
const branch = '00000000-0000-4000-8000-000000000003';
const hash = 'a'.repeat(64);
const branchSummary = { branch_id: branch, baseline_hash: hash, mode: 'engineering_fixture', observed_baseline_verified: false };
const branchReport = { id: branch, baseline_hash: hash, baseline_state_id: null, input: { baseline_measurement_id: project, run_id: patient, timeline_origin_id: branch }, mode: 'engineering_fixture', observed_baseline_verified: false, origin: 'SYNTHETIC_GENERATED', scientific_review: 'pending' };

function configBody(fetch: Mock) {
  const call = fetch.mock.calls.find((call: unknown[]) => String(call[0]).includes('resource=config&branch='));
  return JSON.parse(String((call?.[1] as { body?: unknown } | undefined)?.body ?? '{}'));
}

function response(value: unknown, status = 200) {
  return { ok: status < 400, status, text: async () => JSON.stringify(value) };
}

function stubFetch(overrides: Record<string, unknown> = {}) {
  return vi.fn(async (input: unknown) => {
    const url = String(input);
    if (url.includes('resource=branches')) return response({ items: [branchSummary] });
    if (url.includes('resource=branch&')) return response(branchReport);
    if (url.includes('resource=current')) return response({ publication: null, current_use_allowed: true, restrictions: [], next_action: 'Available' });
    if (url.includes('resource=config&branch=')) return response({ id: patient, branch_id: branch, draft_revision: 1, config_hash: 'b'.repeat(64), config: { branch_id: branch, scenario: { family: 'SC-01' }, geometry_policy: 'none' }, summary: { disclosure: 'Hypothetical simulation', available_actions: [], blocking_reasons: [] } });
    if (url.includes('resource=eligibility')) return response({ result: { status: 'sufficient' } });
    if (url.includes('resource=preview')) return response({ slots: [{ slot_id: 'slot-1', modality: 'imaging', configured_day: '10', relative_day: '10' }], tumor_targets: [{ slot_id: 'slot-1', target_mm3: '120.5' }] });
    if (url in overrides) return overrides[url] as never;
    throw new Error(`unexpected simulation proxy call: ${url}`);
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('simulation builder without manual UUID or JSON paste', () => {
  it('loads branches from the workspace case and generates owned JSON', async () => {
    const fetch = stubFetch();
    vi.stubGlobal('fetch', fetch);
    render(<SimulationBuilder project={project} patient={patient} />);
    const picker = await screen.findByLabelText('Branch in this case', {}, { timeout: 10000 });
    expect(picker).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Load baseline branch' }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('resource=current'), expect.anything()));
    expect(screen.queryByLabelText('Project UUID')).toBeNull();
    expect(screen.queryByLabelText('Administrator access token')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Save immutable draft version' }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('resource=config&branch='), expect.objectContaining({ method: 'POST' })));
    const body = configBody(fetch);
    expect(body.config.branch_id).toBe(branch);
    expect(body.config.baseline_hash).toBe(hash);
    expect(body.config.scenario.family).toBe('SC-01');
    expect(body.config.treatment).toEqual({ exposure: 'none' });
    expect(body.config.tumor_profile.unit).toBe('mm3');
    expect(screen.queryByLabelText('Simulation configuration JSON')).toBeNull();
  });

  it('keeps treatment exposure locked while allowing family, days, and targets', async () => {
    const fetch = stubFetch();
    vi.stubGlobal('fetch', fetch);
    render(<SimulationBuilder project={project} patient={patient} />);
    await screen.findByLabelText('Branch in this case', {}, { timeout: 10000 });
    fireEvent.click(screen.getByRole('button', { name: 'Load baseline branch' }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('resource=current'), expect.anything()));
    fireEvent.click(screen.getByRole('button', { name: /SC-02/ }));
    fireEvent.change(screen.getByLabelText(/Follow-up days/), { target: { value: '7, 35, 91' } });
    fireEvent.change(screen.getByLabelText(/Explicit target volume/), { target: { value: '90' } });
    expect(screen.getByText(/Treatment exposure:/)).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Save immutable draft version' }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('resource=config&branch='), expect.objectContaining({ method: 'POST' })));
    const body = configBody(fetch);
    expect(body.config.scenario.family).toBe('SC-02');
    expect(body.config.treatment).toEqual({ exposure: 'none' });
    expect(body.config.schedule.slots.map((slot: { relative_day: string }) => slot.relative_day)).toEqual(['7', '35', '91']);
  });
});
