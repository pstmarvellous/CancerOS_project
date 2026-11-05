'use client';

import { useEffect, useRef, useState } from 'react';
import type { ResearchProject } from '../lib/research-session';
export type { ResearchProject } from '../lib/research-session';

type SessionResponse = { authenticated: boolean; projects: ResearchProject[]; expiresAt?: string };
type Props = { selectedProjectId?: string | null; onProjectChange: (projectId: string | null) => void;
  onSessionChange?: (authenticated: boolean) => void };

export function ResearchSessionPanel({ selectedProjectId, onProjectChange, onSessionChange }: Props) {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState('');
  const credential = useRef<HTMLInputElement>(null);
  const callbacks = useRef({ onProjectChange, onSessionChange });
  const selected = useRef(selectedProjectId);
  useEffect(() => { callbacks.current = { onProjectChange, onSessionChange }; selected.current = selectedProjectId; });

  function applySession(value: SessionResponse) {
    setSession(value);
    callbacks.current.onSessionChange?.(value.authenticated);
    const project = value.projects.find(item => item.project_id === selected.current) ?? value.projects[0];
    callbacks.current.onProjectChange(value.authenticated ? project?.project_id ?? null : null);
  }

  useEffect(() => {
    const controller = new AbortController();
    void fetch('/api/research-session', { cache: 'no-store', signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error('Research access could not be checked. Retry signing in when the API is available.');
        const value = await response.json() as SessionResponse;
        if (!controller.signal.aborted) applySession(value);
      }).catch(() => { if (!controller.signal.aborted) setMessage('Research access could not be checked. Retry signing in when the API is available.'); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!session?.authenticated || !session.expiresAt) return;
    const timer = setTimeout(() => {
      applySession({ authenticated: false, projects: [] });
      setMessage('Your research session expired. Sign in again to continue.');
    }, Math.max(0, Date.parse(session.expiresAt) - Date.now()));
    return () => clearTimeout(timer);
  }, [session]);

  async function signIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const token = credential.current?.value.trim() ?? '';
    if (!token) { setMessage('Enter the access token provided by your research administrator.'); return; }
    setBusy(true); setMessage('');
    try {
      const response = await fetch('/api/research-session', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ token }), cache: 'no-store' });
      if (credential.current) credential.current.value = '';
      if (!response.ok) {
        setMessage(response.status === 502 ? 'The research API is unavailable. Your credential was not saved. Retry when it is available.' : 'Sign in failed. Check your current authorized research access token.');
        return;
      }
      applySession(await response.json() as SessionResponse);
    } catch { setMessage('Sign in could not complete. Check the connection and retry.'); }
    finally { if (credential.current) credential.current.value = ''; setBusy(false); }
  }

  async function signOut() {
    setBusy(true); setMessage('');
    try {
      const response = await fetch('/api/research-session', { method: 'DELETE', cache: 'no-store' });
      if (!response.ok) throw new Error();
      applySession({ authenticated: false, projects: [] });
    } catch { setMessage('Sign out could not complete. Retry to close the research session.'); }
    finally { setBusy(false); }
  }

  return <section className="card research-session" aria-labelledby="research-session-title">
    <div className="section-heading"><div><h2 id="research-session-title">Research access</h2>
      <p>Use your existing authorized research credential. Synthetic demo access is separate.</p></div>
      {session?.authenticated ? <button type="button" className="button secondary" onClick={() => void signOut()} disabled={busy}>Sign out</button> : null}</div>
    {message ? <p role="alert">{message}</p> : null}
    {busy && session === null ? <p role="status">Checking research access…</p> : null}
    {session?.authenticated ? <>
      {session.projects.length ? <label>Research project
        <select value={selectedProjectId ?? ''} onChange={event => onProjectChange(event.target.value)} disabled={busy}>
          {!selectedProjectId ? <option value="" disabled>Select a project</option> : null}
          {session.projects.map(project => <option key={project.project_id} value={project.project_id}>{project.name} · {project.role}</option>)}
        </select></label> : <p role="status">You are signed in, but no projects are assigned. Ask your research administrator for project access.</p>}
      {session.expiresAt ? <p className="muted">Session ends at {new Date(session.expiresAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.</p> : null}
    </> : <form onSubmit={event => void signIn(event)} autoComplete="off">
      <label htmlFor="research-credential">Research access token</label>
      <input id="research-credential" ref={credential} type="password" autoComplete="off" spellCheck={false} maxLength={16384} disabled={busy} aria-describedby="research-credential-help" />
      <p id="research-credential-help" className="muted">Provided by your research administrator. The browser stores only a short-lived, protected session cookie.</p>
      <button type="submit" className="button primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in to research workspace'}</button>
    </form>}
  </section>;
}
