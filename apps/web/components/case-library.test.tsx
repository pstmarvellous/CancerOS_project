import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CaseLibrary } from './case-library';

describe('COS-073 case library', () => {
  it('asks for a project instead of guessing one', () => {
    render(<CaseLibrary initialProject={null}/>);
    expect(screen.getByText(/No project selected/)).toBeVisible();
  });
  it('lists authorized cases with counts from visible records only', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({items: [
        {patient_id: 'a', display_code: 'CASE-01', data_revision: 2},
        {patient_id: 'b', display_code: 'CASE-02', data_revision: 2},
      ]}),
    }));
    render(<CaseLibrary initialProject="p1"/>);
    expect(await screen.findByText(/2 authorized cases shown/)).toBeVisible();
    expect(screen.getByRole('heading', {name: 'CASE-01'})).toBeVisible();
    expect(screen.getAllByRole('link', {name: 'Open case'})).toHaveLength(2);
    vi.unstubAllGlobals();
  });
  it('explains empty, restricted and failed states with a next action', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok: true, json: async () => ({items: []})}));
    const {unmount} = render(<CaseLibrary initialProject="p1"/>);
    expect(await screen.findByText(/No approved cases yet/)).toBeVisible();
    expect(screen.getByRole('link', {name: 'Start guided demo'})).toBeVisible();
    unmount();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ok: false, status: 403, text: async () => 'denied'}));
    render(<CaseLibrary initialProject="p1"/>);
    await waitFor(() => expect(screen.getByText(/restricted for your role/)).toBeVisible());
    vi.unstubAllGlobals();
  });
});
