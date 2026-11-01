import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ClinicalChartsExplorer } from './clinical-charts-explorer';

const PROJECT = '11111111-1111-1111-1111-111111111111';
const PATIENT = '22222222-2222-2222-2222-222222222222';
const RECORD = '33333333-3333-3333-3333-333333333333';

function stubFetch() {
  return vi.fn(async (input: unknown) => {
    const url = String(input);
    if (url.includes('/api/clinical-charts')) {
      return {
        ok: true,
        text: async () =>
          JSON.stringify({
            items: [{ record_id: RECORD, kind: 'laboratory', concept: 'hemoglobin', source_hash: 'a'.repeat(64), superseded: false }],
            snapshot_cursor: 'b'.repeat(64),
          }),
      };
    }
    if (url.includes('/api/case-record')) {
      return {
        ok: true,
        text: async () =>
          JSON.stringify({
            id: RECORD,
            item: { kind: 'laboratory', concept: 'hemoglobin', original_term: 'Hemoglobin', original_unit: 'g/dL', original_value: '9.123456789' },
            availability: 'available',
            origin: 'REAL_OBSERVED',
            quality: { status: 'verified' },
          }),
      };
    }
    return { ok: false, status: 404, text: async () => '{}' };
  });
}

describe('COS-077 clinical charts explorer', () => {
  it('asks for a case instead of guessing one', () => {
    Object.defineProperty(window, 'location', { value: { search: '' }, writable: true });
    render(<ClinicalChartsExplorer />);
    expect(screen.getByText(/Open a case to inspect its clinical charts/)).toBeVisible();
  });

  it('loads bounded history and preserves exact decimal strings', async () => {
    Object.defineProperty(window, 'location', {
      value: { search: `?project=${PROJECT}&patient=${PATIENT}` },
      writable: true,
    });
    vi.stubGlobal('fetch', stubFetch());
    render(<ClinicalChartsExplorer />);
    await waitFor(() => expect(screen.getByText(/authorized records across/)).toBeVisible(), { timeout: 10000 });
    expect(screen.getAllByText(/9.123456789/).length).toBeGreaterThan(0);
    vi.unstubAllGlobals();
  }, 15000);
});
