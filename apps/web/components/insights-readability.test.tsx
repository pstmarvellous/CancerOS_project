import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { InsightsExplorer } from './insights-explorer';

const query = vi.hoisted(() => ({ search: '' }));
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(query.search),
}));

const MEASURE = '44444444-4444-4444-4444-444444444444';
const HASH = 'a'.repeat(64);

function stubFetch() {
  return vi.fn(async (input: unknown) => {
    const url = String(input);
    if (url.includes('action=context')) {
      return {
        ok: true,
        text: async () => JSON.stringify({
          branch_id: '33333333-3333-3333-3333-333333333333', comparison_snapshot_id: null, comparison_stale: null,
          context_hash: HASH, exportable: false,
          limitations: ['Snapshot-bound research context only.'],
          missing_modalities: [], measurements: [{ reference_id: MEASURE, metric_code: 'hemoglobin', value: '9', unit: 'g_dL', member_time: 'Source-relative day 1', origin: 'REAL_OBSERVED', context: 'observed' }],
          assertions: [{ reference_id: '55555555-5555-5555-5555-555555555555', excerpt: 'Background passage.', source_note_id: 'n1', certainty: 'unknown' }],
          missing: [], conflicts: [],
        }),
      };
    }
    if (url.includes('action=interpret')) {
      return {
        ok: true,
        text: async () => JSON.stringify({
          schema_version: 'interpretation/1', context_snapshot_id: '33333333-3333-3333-3333-333333333333', context_hash: HASH, snapshot_hash: HASH,
          execution_mode: 'rule_based_summary', summary: 'Rule-based summary.',
          findings: [{ kind: 'observed_measurement', text: 'Retained hemoglobin value.', measurement_refs: [MEASURE], passage_refs: [] }],
          uncertainties: [], limitations: [], visibility: 'visible_template', next_action: 'proceed',
        }),
      };
    }
    return { ok: false, status: 404, text: async () => '{}' };
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('insights readability without inference changes', () => {
  it('presents grouped evidence and a grounding status in plain language', async () => {
    query.search = `?project=11111111-1111-1111-1111-111111111111&patient=22222222-2222-2222-2222-222222222222&state=33333333-3333-3333-3333-333333333333`;
    vi.stubGlobal('fetch', stubFetch());
    render(<InsightsExplorer />);
    fireEvent.click(screen.getByRole('button', { name: 'Load exact context' }));
    await waitFor(() => expect(screen.getByText(/Snapshot context in plain language/)).toBeVisible(), { timeout: 10000 });
    expect(screen.getByText(/1 case measurement/)).toBeVisible();
    expect(screen.getByText(/1 background passage/)).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Generate rule-based summary' }));
    await waitFor(() => expect(screen.getByText('Rule-based summary.')).toBeVisible(), { timeout: 10000 });
    expect(screen.getByText(/Grounding: Rule-based summary/)).toBeVisible();
    fireEvent.click(screen.getByText(/observed measurement/));
    expect(await screen.findByText(/Case evidence:/)).toBeVisible();
  });
});
