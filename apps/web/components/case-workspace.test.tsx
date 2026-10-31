import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CaseWorkspace } from './case-workspace';

const DETAIL = {
  patient_id: '11111111-1111-1111-1111-111111111111',
  display_code: 'CASE-01',
  data_revision: 3,
  observation_count: 2,
  visit_count: 1,
  next_action: 'review_observations_or_stage_source_update',
};

function stubFetch() {
  return vi.fn(async (input: unknown, init?: { method?: string }) => {
    const url = String(input);
    if (url.startsWith('/api/case-detail')) return { ok: true, text: async () => JSON.stringify(DETAIL) };
    if (url.startsWith('/api/case-visits')) {
      return { ok: true, text: async () => JSON.stringify({ items: [], next_action: 'none' }) };
    }
    if (url.startsWith('/api/case-record') && (init?.method ?? 'GET') === 'GET') {
      return {
        ok: true,
        text: async () =>
          JSON.stringify({
            id: '22222222-2222-2222-2222-222222222222',
            item: { kind: 'diagnosis', concept: 'invasive_ductal', label: 'Invasive ductal carcinoma' },
            availability: 'available',
            quality: { status: 'verified' },
          }),
      };
    }
    return {
      ok: true,
      text: async () =>
        JSON.stringify({
          items: [{ record_id: '22222222-2222-2222-2222-222222222222', kind: 'diagnosis', concept: 'invasive_ductal', source_hash: 'a'.repeat(64), superseded: false }],
          snapshot_cursor: 'b'.repeat(64),
        }),
    };
  });
}

describe('COS-074 case workspace', () => {
  it('requires an explicit project and patient selection', () => {
    Object.defineProperty(window, 'location', { value: { search: '' }, writable: true });
    render(<CaseWorkspace />);
    expect(screen.getByText(/No case selected/)).toBeVisible();
  });

  it('shows observed facts with unknown values as not recorded', async () => {
    Object.defineProperty(window, 'location', {
      value: {
        search: '?project=33333333-3333-3333-3333-333333333333&patient=11111111-1111-1111-1111-111111111111',
      },
      writable: true,
    });
    vi.stubGlobal('fetch', stubFetch());
    render(<CaseWorkspace />);
    expect(await screen.findByRole('heading', { name: 'CASE-01' }, { timeout: 10000 })).toBeVisible();
    expect(screen.getByText(/Unknown values stay/)).toBeVisible();
    expect(screen.getAllByText('Not recorded').length).toBeGreaterThan(0);
    const toggle = await screen.findByText(/invasive_ductal/);
    fireEvent.click(toggle);
    await waitFor(() => expect(screen.getByText(/exact record revision/)).toBeVisible());
    vi.unstubAllGlobals();
  });
});
