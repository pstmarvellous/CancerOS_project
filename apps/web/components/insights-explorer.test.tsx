import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { InsightsExplorer } from './insights-explorer';

const query = vi.hoisted(() => ({ search: '' }));
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(query.search),
}));

const PROJECT = '11111111-1111-1111-1111-111111111111';
const PATIENT = '22222222-2222-2222-2222-222222222222';
const STATE = '33333333-3333-3333-3333-333333333333';
const MEASURE = '44444444-4444-4444-4444-444444444444';
const HASH = 'a'.repeat(64);

function stubFetch() {
  return vi.fn(async (input: unknown, init?: { body?: unknown }) => {
    void init;
    const url = String(input);
    if (url.includes('action=context')) {
      return {
        ok: true,
        text: async () =>
          JSON.stringify({
            branch_id: STATE,
            comparison_snapshot_id: null,
            comparison_stale: null,
            context_hash: HASH,
            exportable: false,
            limitations: ['Snapshot-bound research context only; no clinical interpretation or advice.'],
            missing_modalities: [],
            measurements: [{ reference_id: MEASURE, metric_code: 'hemoglobin', value: '9', unit: 'g_dL', member_time: 'Source-relative day 1', origin: 'REAL_OBSERVED', context: 'observed' }],
            assertions: [],
            missing: [],
            conflicts: [],
          }),
      };
    }
    if (url.includes('action=interpret')) {
      return {
        ok: true,
        text: async () =>
          JSON.stringify({
            schema_version: 'interpretation/1',
            context_snapshot_id: STATE,
            context_hash: HASH,
            snapshot_hash: HASH,
            execution_mode: 'rule_based_summary',
            summary: 'Rule-based summary.',
            findings: [{ kind: 'observed_measurement', text: 'Retained hemoglobin value.', measurement_refs: [MEASURE], passage_refs: [] }],
            uncertainties: [],
            limitations: [],
            visibility: 'visible_template',
            next_action: 'proceed',
          }),
      };
    }
    return { ok: false, status: 404, text: async () => '{}' };
  });
}

describe('COS-079 insights explorer', () => {
  it('asks for a case instead of guessing one', () => {
    query.search = '';
    render(<InsightsExplorer />);
    expect(screen.getByText(/Open a case to inspect its insights/)).toBeVisible();
  });

  it('loads snapshot-bound context and labels rule-based execution', async () => {
    query.search = `?project=${PROJECT}&patient=${PATIENT}&state=${STATE}`;
    const fetch = stubFetch();
    vi.stubGlobal('fetch', fetch);
    render(<InsightsExplorer />);
    await waitFor(() => expect(screen.getByText(/Snapshot context in plain language/)).toBeVisible(), { timeout: 10000 });
    const contextCall = fetch.mock.calls.find(call => String(call[0]).includes('action=context'));
    expect(contextCall).toBeDefined();
    if (!contextCall) throw new Error('context request missing');
    expect(JSON.parse(String(contextCall[1]?.body))).toEqual({ patient_id: PATIENT, snapshot_id: STATE });
    fireEvent.click(screen.getByRole('button', { name: 'Generate rule-based summary' }));
    await waitFor(() => expect(screen.getByText('Rule-based summary.')).toBeVisible(), { timeout: 10000 });
    expect(screen.getByText(/Each finding below opens its exact case observation/)).toBeVisible();
    vi.unstubAllGlobals();
  });
});
