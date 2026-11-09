import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { StateTimelineExplorer } from './state-timeline-explorer';

const query = vi.hoisted(() => ({ search: '' }));
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(query.search),
}));

const PROJECT = '11111111-1111-1111-1111-111111111111';
const PATIENT = '22222222-2222-2222-2222-222222222222';
const BRANCH = '33333333-3333-3333-3333-333333333333';
const STATE = '44444444-4444-4444-4444-444444444444';
const HASH = 'a'.repeat(64);

function snapshot() {
  return {
    id: STATE,
    patient_id: PATIENT,
    branch_id: BRANCH,
    context: 'SYNTHETIC',
    origin: 'SYNTHETIC_GENERATED',
    time: { basis: 'relative_day', value: '37', time_domain: 'simulation', timeline_origin_id: BRANCH, anchor_state_id: null },
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

function stubFetch() {
  return vi.fn(async (input: unknown) => {
    const url = String(input);
    if (url.includes('resource=branches')) {
      return { ok: true, text: async () => JSON.stringify({ items: [{ branch_id: BRANCH, baseline_hash: HASH, mode: 'simulation', observed_baseline_verified: true }] }) };
    }
    if (url.includes('resource=states')) {
      return { ok: true, text: async () => JSON.stringify({ items: [{ snapshot: snapshot(), snapshot_hash: HASH, stale: false, current_use_allowed: true, restrictions: [], review: null, publication: null, available_actions: ['inspect_history'], next_action: 'Inspect retained membership' }], next_cursor: null, snapshot_revision: 2 }) };
    }
    if (url.includes('resource=fusion')) {
      return { ok: true, text: async () => JSON.stringify(null) };
    }
    if (url.includes('resource=state&') || url.includes('resource=state?') || /resource=state$/.test(url)) {
      return { ok: true, text: async () => JSON.stringify({ snapshot: snapshot(), snapshot_hash: HASH, stale: false, current_use_allowed: true, restrictions: [], review: null, publication: null, available_actions: ['inspect_history'], next_action: 'Inspect retained membership', view: undefined }) };
    }
    return { ok: false, status: 404, text: async () => '{}' };
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('REC-07 timeline to insights link', () => {
  it('offers an exact-state insights link derived from the workspace selection', async () => {
    query.search = `?project=${PROJECT}&patient=${PATIENT}`;
    vi.stubGlobal('fetch', stubFetch());
    render(<StateTimelineExplorer project={PROJECT} patient={PATIENT} />);
    await waitFor(() => expect(screen.getByText(/Selected state/)).toBeVisible(), { timeout: 10000 });
    const link = screen.getByRole('link', { name: 'Explain this state in Insights →' });
    expect(link).toHaveAttribute(
      'href',
      `/insights?project=${PROJECT}&patient=${PATIENT}&branch=${BRANCH}&state=${STATE}`,
    );
    expect(screen.queryByRole('textbox')).toBeNull();
  });
});
