import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ResearchSessionPanel } from './research-session';

const project = { project_id: '00000000-0000-4000-8000-000000000001', name: 'Authorized study', role: 'editor' };
afterEach(() => vi.unstubAllGlobals());

describe('research session panel', () => {
  it('signs in with a transient password field and selects named authorized projects', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(Response.json({ authenticated: false, projects: [] }))
      .mockResolvedValueOnce(Response.json({ authenticated: true, projects: [project] }))
      .mockResolvedValueOnce(Response.json({ authenticated: false, projects: [] }));
    vi.stubGlobal('fetch', fetchMock);
    const onProjectChange = vi.fn(); const onSessionChange = vi.fn();
    render(<ResearchSessionPanel selectedProjectId={project.project_id} onProjectChange={onProjectChange} onSessionChange={onSessionChange}/>);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Sign in to research workspace' })).toBeEnabled());
    const credential = screen.getByLabelText('Research access token');
    expect(credential).toHaveAttribute('type', 'password');
    fireEvent.change(credential, { target: { value: 'existing-credential' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in to research workspace' }));
    expect(await screen.findByRole('option', { name: 'Authorized study · Editor — can add clinical observations' })).toBeVisible();
    expect(credential).toHaveValue('');
    expect(onProjectChange).toHaveBeenLastCalledWith(project.project_id);
    expect(onSessionChange).toHaveBeenLastCalledWith(true);
    expect(fetchMock.mock.calls[1][0]).toBe('/api/research-session');
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ token: 'existing-credential' });
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }));
    await waitFor(() => expect(onSessionChange).toHaveBeenLastCalledWith(false));
    expect(onProjectChange).toHaveBeenLastCalledWith(null);
  });

  it('clears submitted credentials after a failed sign-in and allows retry', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(Response.json({ authenticated: false, projects: [] }))
      .mockResolvedValueOnce(Response.json({}, { status: 401 })));
    render(<ResearchSessionPanel onProjectChange={vi.fn()}/>);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Sign in to research workspace' })).toBeEnabled());
    const credential = screen.getByLabelText('Research access token');
    fireEvent.change(credential, { target: { value: 'rejected-credential' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in to research workspace' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Sign in failed');
    expect(credential).toHaveValue('');
    expect(screen.getByRole('button', { name: 'Sign in to research workspace' })).toBeEnabled();
  });

  it('retains the no-project state without guessing or offering a UUID field', async () => {
    const onProjectChange = vi.fn();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ authenticated: true, projects: [] })));
    render(<ResearchSessionPanel onProjectChange={onProjectChange}/>);
    expect(await screen.findByText(/No projects yet/)).toBeVisible();
    expect(onProjectChange).toHaveBeenLastCalledWith(null);
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });
});
