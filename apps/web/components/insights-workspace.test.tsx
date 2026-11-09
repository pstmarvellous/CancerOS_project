import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { InsightsExplorer } from './insights-explorer';

const query = vi.hoisted(() => ({ search: '' }));
vi.mock('next/navigation', () => ({
  useSearchParams: () => new URLSearchParams(query.search),
}));

const PROJECT = '11111111-1111-1111-1111-111111111111';
const PATIENT = '22222222-2222-2222-2222-222222222222';
const BRANCH = '33333333-3333-3333-3333-333333333333';
const STATE = '44444444-4444-4444-4444-444444444444';
const OTHER_STATE = '55555555-5555-5555-5555-555555555555';
const MEASURE = '66666666-6666-6666-6666-666666666666';
const HASH = 'b'.repeat(64);

const CONTEXT = {
  branch_id: BRANCH,
  snapshot_id: STATE,
  snapshot_hash: HASH,
  context_hash: HASH,
  payload_hash: HASH,
  patient_id: PATIENT,
  purpose: 'research_summary',
  stale: false,
  exportable: false,
  measurements: [{ reference_id: MEASURE, metric_code: 'hemoglobin', value: '9', unit: 'g_dL', member_time: 'Source-relative day 1', origin: 'REAL_OBSERVED', context: 'observed' }],
  assertions: [],
  passages: [],
  treatment_history: [],
  missing_modalities: [],
  conflicts: [],
  limitations: ['Snapshot-bound research context only; no clinical interpretation or advice.'],
  omitted: [],
};
const REPORT = {
  schema_version: 'interpretation/1',
  context_snapshot_id: STATE,
  context_hash: HASH,
  snapshot_hash: HASH,
  execution_mode: 'rule_based_summary',
  summary: 'Rule-based summary of 1 retained measurements.',
  findings: [{ kind: 'observed_measurement', text: 'Retained hemoglobin value 9 g_dL.', measurement_refs: [MEASURE], passage_refs: [], metric_code: 'hemoglobin', metric_value: '9', metric_unit: 'g_dL' }],
  uncertainties: [],
  limitations: [],
  visibility: 'visible_template',
  next_action: 'proceed',
};
const CAPABILITIES = {
  schema_version: 'provider-capabilities/1',
  local_summary_available: true,
  external_model_available: false,
  external_status: 'policy_access_and_grounding_review_required',
  candidate_publication_available: false,
  note_extraction_available: false,
  local_note_extraction_available: true,
  local_note_extraction_scope: 'four_symptom_templates_synthetic_fixture_only',
  next_action: 'use_local_mode',
};

function stubFetch() {
  return vi.fn(async (input: unknown) => {
    const url = String(input);
    if (url.includes('provider-capabilities')) return { ok: true, text: async () => JSON.stringify(CAPABILITIES) };
    if (url.includes('resource=branches')) return { ok: true, text: async () => JSON.stringify({ items: [{ branch_id: BRANCH, mode: 'observed' }] }) };
    if (url.includes('resource=states')) return { ok: true, text: async () => JSON.stringify({ items: [{ snapshot: { id: STATE, input_revision: 1, status: 'ready' } }, { snapshot: { id: OTHER_STATE, input_revision: 1, status: 'ready' } }] }) };
    if (url.includes('action=context')) return { ok: true, text: async () => JSON.stringify(url.includes(`state=${OTHER_STATE}`) ? { ...CONTEXT, snapshot_id: OTHER_STATE, measurements: [{ ...CONTEXT.measurements[0], value: '10' }] } : CONTEXT) };
    if (url.includes('action=interpret')) return { ok: true, text: async () => JSON.stringify(REPORT) };
    return { ok: false, status: 404, text: async () => '{}' };
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('REC-07 workspace-connected interpretation', () => {
  it('derives branch and state from the authorized workspace link with no UUID typing', async () => {
    query.search = `?project=${PROJECT}&patient=${PATIENT}&branch=${BRANCH}&state=${STATE}`;
    const fetch = stubFetch();
    vi.stubGlobal('fetch', fetch);
    render(<InsightsExplorer />);
    await waitFor(() => expect(screen.getByText(/Snapshot context in plain language/)).toBeVisible(), { timeout: 10000 });
    expect(screen.queryByRole('textbox')).toBeNull();
    expect(screen.getByText(/hemoglobin/)).toBeVisible();
    const contextCall = fetch.mock.calls.find(call => String(call[0]).includes('action=context'));
    expect(contextCall).toBeDefined();
  });

  it('labels verified provider status: local usable, live blocked', async () => {
    query.search = `?project=${PROJECT}&patient=${PATIENT}&state=${STATE}`;
    vi.stubGlobal('fetch', stubFetch());
    render(<InsightsExplorer />);
    await waitFor(() => expect(screen.getByText(/Live result:/)).toBeVisible(), { timeout: 10000 });
    expect(screen.getByText(/Live model unavailable/)).toBeVisible();
    expect(screen.getByText(/deterministic template from the exact context/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Request private candidate (gate closed)' })).toBeDisabled();
  });

  it('reports exact selected values in the rule-based summary and clears stale results on state change', async () => {
    query.search = `?project=${PROJECT}&patient=${PATIENT}&branch=${BRANCH}&state=${STATE}`;
    vi.stubGlobal('fetch', stubFetch());
    render(<InsightsExplorer />);
    await waitFor(() => expect(screen.getByText(/Snapshot context in plain language/)).toBeVisible(), { timeout: 10000 });
    fireEvent.click(screen.getByRole('button', { name: 'Generate rule-based summary' }));
    await waitFor(() => expect(screen.getByText('Rule-based summary of 1 retained measurements.')).toBeVisible(), { timeout: 10000 });
    expect(screen.getAllByText(/Retained hemoglobin value 9 g_dL/).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText('State'), { target: { value: OTHER_STATE } });
    expect(screen.queryByText('Rule-based summary of 1 retained measurements.')).toBeNull();
    expect(screen.queryByText(/Snapshot context in plain language/)).toBeNull();
    expect(screen.queryByRole('button', { name: 'Generate rule-based summary' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Load exact context' }));
    await waitFor(() => expect(screen.getByText(/Snapshot context in plain language/)).toBeVisible());
    expect(screen.getByText(/hemoglobin.*10 g_dL/)).toBeVisible();
    const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
    expect(calls.some(call => String(call[0]).includes(`action=context&state=${OTHER_STATE}`))).toBe(true);
  });

  it('discards a late summary after changing the selected state, even when transport ignores abort', async () => {
    query.search = `?project=${PROJECT}&patient=${PATIENT}&branch=${BRANCH}&state=${STATE}`;
    let finish: ((value: unknown) => void) | undefined;
    const normalFetch = stubFetch();
    vi.stubGlobal('fetch', vi.fn((input: unknown) => String(input).includes('action=interpret')
      ? new Promise(resolve => { finish = resolve; }) : normalFetch(input)));
    render(<InsightsExplorer />);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate rule-based summary' })).toBeVisible());
    fireEvent.click(screen.getByRole('button', { name: 'Generate rule-based summary' }));
    await waitFor(() => expect(finish).toBeDefined());
    fireEvent.change(screen.getByLabelText('State'), { target: { value: OTHER_STATE } });
    finish?.({ ok: true, text: async () => JSON.stringify(REPORT) });
    await waitFor(() => expect(screen.getByText(/Selection changed/)).toBeVisible());
    expect(screen.queryByText(REPORT.summary)).toBeNull();
    expect(screen.queryByText(/Snapshot context in plain language/)).toBeNull();
  });

  it('separates negated patient note assertions from cited background passages', async () => {
    query.search = `?project=${PROJECT}&patient=${PATIENT}&state=${STATE}`;
    const normalFetch = stubFetch();
    vi.stubGlobal('fetch', vi.fn((input: unknown) => String(input).includes('action=context')
      ? Promise.resolve({ ok: true, text: async () => JSON.stringify({ ...CONTEXT,
        assertions: [{ reference_id: MEASURE, concept: 'pain', excerpt: 'No pain.', negated: true, certainty: 'documented', source_note_id: OTHER_STATE }],
        passages: [{ passage_id: BRANCH, document_id: PROJECT, corpus_id: PATIENT, excerpt: 'General research background.', locator: 'paragraph:0-28' }],
      }) }) : normalFetch(input)));
    render(<InsightsExplorer />);
    await waitFor(() => expect(screen.getByRole('region', { name: 'Unverified note assertions' })).toBeVisible());
    expect(screen.getByText(/No pain.*negated/)).toBeVisible();
    expect(screen.getByText(/1 background passage/)).toBeVisible();
    expect(screen.getByText(/Background evidence · 1 unreviewed passage/)).toBeInTheDocument();
    expect(screen.queryByText(/Source note:.*Certainty:/)).toBeNull();
  });

  it('pins an explicit prior state in context and interpretation requests', async () => {
    query.search = `?project=${PROJECT}&patient=${PATIENT}&branch=${BRANCH}&state=${STATE}`;
    const normalFetch = stubFetch();
    const fetch = vi.fn((input: unknown, init?: { body?: string }) => {
      void init;
      return String(input).includes('resource=states')
        ? Promise.resolve({ ok: true, text: async () => JSON.stringify({ items: [
          { snapshot: { id: STATE, time: { value: '37' }, input_revision: 1, status: 'ready' } },
          { snapshot: { id: OTHER_STATE, time: { value: '0' }, input_revision: 1, status: 'ready' } },
        ] }) }) : normalFetch(input);
    });
    vi.stubGlobal('fetch', fetch);
    render(<InsightsExplorer />);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate rule-based summary' })).toBeVisible());
    fireEvent.change(screen.getByLabelText('Compare with prior state'), { target: { value: OTHER_STATE } });
    expect(screen.queryByRole('button', { name: 'Generate rule-based summary' })).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Load exact context' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Generate rule-based summary' })).toBeVisible());
    fireEvent.click(screen.getByRole('button', { name: 'Generate rule-based summary' }));
    await waitFor(() => expect(screen.getByText(REPORT.summary)).toBeVisible());
    const call = fetch.mock.calls.find(row => String(row[0]).includes('action=interpret'));
    expect(JSON.parse(call?.[1]?.body ?? '{}').context_input.comparison_snapshot_id).toBe(OTHER_STATE);
  });

  it('keeps an unverifiable provider status distinct from a verified block', async () => {
    query.search = `?project=${PROJECT}&patient=${PATIENT}&state=${STATE}`;
    vi.stubGlobal('fetch', vi.fn(async (input: unknown) => {
      const url = String(input);
      if (url.includes('provider-capabilities')) return { ok: false, status: 502, text: async () => '{}' };
      if (url.includes('action=context')) return { ok: true, text: async () => JSON.stringify(CONTEXT) };
      return { ok: false, status: 404, text: async () => '{}' };
    }));
    render(<InsightsExplorer />);
    await waitFor(() => expect(screen.getByText(/Provider status could not be verified/)).toBeVisible(), { timeout: 10000 });
    expect(screen.queryByText(/Live model unavailable/)).toBeNull();
  });
});
