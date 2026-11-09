import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { StateTimelineExplorer } from './state-timeline-explorer';

vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(''),
}));

const PROJECT = '11111111-1111-1111-1111-111111111111';
const PATIENT = '22222222-2222-2222-2222-222222222222';
const BRANCH = '33333333-3333-3333-3333-333333333333';
const STATE_A = '44444444-4444-4444-4444-444444444444';
const HASH = 'a'.repeat(64);

function snapshot(id: string) {
  return {
    id, patient_id: PATIENT, branch_id: BRANCH, context: 'SYNTHETIC', origin: 'SYNTHETIC_GENERATED',
    time: { basis: 'relative_day', value: '20', time_domain: 'simulation', timeline_origin_id: BRANCH, anchor_state_id: null },
    input_revision: 2, patient_event_head: 1, assembly_policy_version: 'exact-membership/1',
    request_manifest_hash: HASH, revision_manifest_hash: HASH, baseline_hash: HASH,
    clinical_members: [], imaging_members: [], generated_geometry_members: [], generated_clinical_members: [],
    missing: [], conflicts: [], status: 'ready', technical_readiness: 'ready', scientific_review: 'pending',
    publication: 'draft', next_action: 'Inspect retained membership',
  };
}

function stubFetch() {
  return vi.fn(async (input: unknown) => {
    const url = String(input);
    if (url.includes('resource=branches')) {
      return { ok: true, text: async () => JSON.stringify({ items: [{ branch_id: BRANCH, baseline_hash: HASH, mode: 'engineering_fixture', observed_baseline_verified: false }] }) };
    }
    if (url.includes('resource=states')) {
      const view = (id: string) => ({ snapshot: snapshot(id), snapshot_hash: HASH, stale: false, current_use_allowed: true, restrictions: [], review: null, publication: null, available_actions: ['inspect_history'], next_action: 'Inspect' });
      return { ok: true, text: async () => JSON.stringify({ items: [view(STATE_A)], next_cursor: null, snapshot_revision: 2 }) };
    }
    if (url.includes('resource=state&')) {
      return { ok: true, text: async () => JSON.stringify({ snapshot: snapshot(STATE_A), snapshot_hash: HASH, stale: false, current_use_allowed: true, restrictions: [], review: null, publication: null, available_actions: ['inspect_history'], next_action: 'Inspect retained membership' }) };
    }
    if (url.includes('resource=fusion&')) {
      return { ok: true, text: async () => JSON.stringify({ canonical_state: { snapshot: snapshot(STATE_A), snapshot_hash: HASH, input_revision: 2, current_use_allowed: true, stale: false, restrictions: [] }, available_modalities: [], version: 'fusion/1', tumor_state: [], clinical_indicators: [], treatment_history: [], temporal_changes: [], conflicts: [], blocks: [], limitations: [], note_assertions: [], source_priority_policy: 'p' }) };
    }
    throw new Error(`unexpected timeline call: ${url}`);
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('workspace timeline without manual UUID entry', () => {
  it('routes workspace case context into branch and state pickers', async () => {
    const fetch = stubFetch();
    vi.stubGlobal('fetch', fetch);
    render(<StateTimelineExplorer project={PROJECT} patient={PATIENT} />);
    await waitFor(() => expect(screen.getByLabelText('History rail: branch in this case')).toBeVisible(), { timeout: 15000 });
    await waitFor(() => expect(screen.getByText(/Saved discrete timepoints/)).toBeVisible(), { timeout: 15000 });
    expect(screen.getByLabelText('State list equivalent')).toBeVisible();
    expect(screen.getByLabelText('Pin B comparison state')).toBeVisible();
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining(`project=${PROJECT}&patient=${PATIENT}&resource=branches`), expect.anything());
  });
});
