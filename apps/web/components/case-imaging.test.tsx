import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CaseImaging } from './case-imaging';

const studies = { items: [{ study_id: 'private-study-id', series_count: 3, import_count: 2,
  status: 'associated', next_action: 'select_study_for_geometry_or_segmentation_review' }] };
const masks = [{ segmentation_id: 'private-mask-id', batch_id: 'private-batch-id', label_value: 1,
  mask_type: 'functional_enhancement', qc_status: 'pending', next_action: 'open_segmentation_qc_or_measurement_selection' }];
afterEach(() => vi.unstubAllGlobals());
describe('case imaging discovery', () => {
  it('keeps a case without imaging available and offers no fake upload or twin link', async () => {
    const fetch = vi.fn().mockResolvedValue(Response.json({ studies: { items: [] }, segmentations: null }));
    vi.stubGlobal('fetch', fetch);
    render(<CaseImaging project="project" patient="patient"/>);
    expect(await screen.findByText('No imaging studies are associated with this case.')).toBeVisible();
    expect(screen.getByText(/saved case, research profile and clinical observations remain available/)).toBeVisible();
    expect(screen.getByText(/separate reviewed workflow for file-level source rights/)).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Open Digital Twin workspace' })).toBeNull();
    expect(screen.queryByRole('button', { name: /upload|import/i })).toBeNull();
    expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: 'same-origin', cache: 'no-store' });
  });
  it('shows returned study counts and mask meaning without inventing scan metadata', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ studies, segmentations: masks })));
    render(<CaseImaging project="project" patient="patient"/>);
    expect(await screen.findByRole('table', { name: 'Associated imaging studies' })).toBeVisible();
    expect(screen.getByRole('row', { name: 'Study 1 3 2 associated' })).toBeVisible();
    expect(screen.getByRole('row', { name: 'Mask 1 functional enhancement 1 Pending' })).toBeVisible();
    expect(screen.getByText(/Acquisition dates, imaging modality and sequence details are not supplied/)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Open Digital Twin workspace' })).toHaveAttribute('href', '/twin?project=project&patient=patient');
    expect(screen.getByText('Study 1: private-study-id')).not.toBeVisible();
    fireEvent.click(screen.getByText('Advanced imaging identifiers'));
    expect(screen.getByText('Study 1: private-study-id')).toBeVisible();
  });
  it('keeps missing segmentation status distinct from zero masks', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ studies, segmentations: null })));
    render(<CaseImaging project="project" patient="patient"/>);
    expect(await screen.findByText(/Segmentation status is unavailable/)).toBeVisible();
    expect(screen.queryByRole('table', { name: 'Accessible segmentation records' })).toBeNull();
  });
  it('explains denied access and retries imaging without changing the case', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(Response.json({}, { status: 401 }))
      .mockResolvedValueOnce(Response.json({ studies: { items: [] }, segmentations: null }));
    vi.stubGlobal('fetch', fetch);
    render(<CaseImaging project="project" patient="patient"/>);
    expect(await screen.findByRole('alert')).toHaveTextContent('Sign in with an authorized research session');
    expect(screen.getByText(/continue working on the case/)).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Retry imaging' }));
    expect(await screen.findByText('No imaging studies are associated with this case.')).toBeVisible();
    expect(fetch).toHaveBeenCalledTimes(2);
  });
  it('never displays a previous patient response under the next case', async () => {
    let resolveOld: (response: Response) => void = () => {};
    const fetch = vi.fn().mockImplementationOnce(() => new Promise<Response>(resolve => { resolveOld = resolve; }))
      .mockResolvedValueOnce(Response.json({ studies: { items: [] }, segmentations: null }));
    vi.stubGlobal('fetch', fetch);
    const { rerender } = render(<CaseImaging project="project" patient="first"/>);
    rerender(<CaseImaging project="project" patient="second"/>);
    await screen.findByText('No imaging studies are associated with this case.');
    await act(async () => { resolveOld(Response.json({ studies, segmentations: masks })); });
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole('table', { name: 'Associated imaging studies' })).toBeNull();
    expect(screen.queryByText('private-study-id')).toBeNull();
  });
});
