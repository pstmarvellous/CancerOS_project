import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { StateTimelineExplorer } from './state-timeline-explorer';

const PROJECT = '11111111-1111-1111-1111-111111111111';
const PATIENT = '22222222-2222-2222-2222-222222222222';
const BRANCH = '33333333-3333-3333-3333-333333333333';
const STATE_A = '44444444-4444-4444-4444-444444444444';
const STATE_B = '55555555-5555-5555-5555-555555555555';
const HASH = 'a'.repeat(64);

function snapshot(id: string) {
  return {
    id,
    patient_id: PATIENT,
    branch_id: BRANCH,
    context: 'SYNTHETIC',
    origin: 'SYNTHETIC_GENERATED',
    time: { basis: 'relative_day', value: '20', time_domain: 'simulation', timeline_origin_id: BRANCH, anchor_state_id: null },
    input_revision: 2,
    patient_event_head: 1,
    assembly_policy_version: 'exact-membership/1',
    request_manifest_hash: HASH,
    revision_manifest_hash: HASH,
    baseline_hash: HASH,
    clinical_members: [],
    imaging_members: [],
    generated_geometry_members: [],
    generated_clinical_members: [],
    missing: [],
    conflicts: [],
    status: 'ready',
    technical_readiness: 'ready',
    scientific_review: 'pending',
    publication: 'draft',
    next_action: 'Inspect retained membership',
  };
}

function stateView(id: string) {
  return {
    snapshot: snapshot(id),
    snapshot_hash: HASH,
    stale: false,
    current_use_allowed: true,
    restrictions: [],
    review: null,
    publication: null,
    available_actions: ['inspect_history'],
    next_action: 'Inspect retained membership',
  };
}

function stubFetch() {
  return vi.fn(async (input: unknown) => {
    const url = String(input);
    if (url.includes('resource=branches')) {
      return { ok: true, text: async () => JSON.stringify({ items: [{ branch_id: BRANCH, baseline_hash: HASH, mode: 'simulation', observed_baseline_verified: true }] }) };
    }
    if (url.includes('resource=states')) {
      return { ok: true, text: async () => JSON.stringify({ items: [stateView(STATE_A), stateView(STATE_B)], next_cursor: null, snapshot_revision: 2 }) };
    }
    if (url.includes('resource=fusion')) {
      return { ok: true, text: async () => JSON.stringify(null) };
    }
    if (url.includes('resource=state')) {
      const id = url.includes(STATE_B) ? STATE_B : STATE_A;
      return { ok: true, text: async () => JSON.stringify(stateView(id)) };
    }
    return { ok: false, status: 404, text: async () => '{}' };
  });
}

describe('COS-076 state timeline explorer', () => {
  it('asks for a case instead of guessing one', () => {
    Object.defineProperty(window, 'location', { value: { search: '' }, writable: true });
    render(<StateTimelineExplorer />);
    expect(screen.getByText(/Open a case to inspect its history/)).toBeVisible();
  });

  it('loads persisted states with a labeled slider and no interpolation', async () => {
    Object.defineProperty(window, 'location', {
      value: { search: `?project=${PROJECT}&patient=${PATIENT}` },
      writable: true,
    });
    vi.stubGlobal('fetch', stubFetch());
    render(<StateTimelineExplorer />);
    await waitFor(() => expect(screen.getByText(/Persisted discrete states/)).toBeVisible(), { timeout: 10000 });
    expect(screen.getByLabelText('State slider')).toBeVisible();
    expect(screen.getByText(/Observation sequence 1 of 2/)).toBeVisible();
    expect(screen.getByText(/Persisted discrete states/)).toBeVisible();
    vi.unstubAllGlobals();
  });

  it('pins a second state without recomputing quantities in the browser', async () => {
    Object.defineProperty(window, 'location', {
      value: { search: `?project=${PROJECT}&patient=${PATIENT}` },
      writable: true,
    });
    const fetchMock = stubFetch();
    vi.stubGlobal('fetch', fetchMock);
    render(<StateTimelineExplorer />);
    const pinB = await screen.findByLabelText('Pin B', {}, { timeout: 10000 });
    fireEvent.change(pinB, { target: { value: STATE_B } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining(STATE_B), expect.anything()));
    vi.unstubAllGlobals();
  });
});
