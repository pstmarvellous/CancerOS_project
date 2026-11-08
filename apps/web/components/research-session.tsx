'use client';

import { useEffect, useRef, useState } from 'react';
import type { ResearchProject } from '../lib/research-session';
export type { ResearchProject } from '../lib/research-session';
import { forgetCase } from '../lib/case-selection';

type SessionResponse = { authenticated: boolean; projects: ResearchProject[]; expiresAt?: string };
type Props = { selectedProjectId?: string | null; onProjectChange: (projectId: string | null) => void;
  onSessionChange?: (authenticated: boolean) => void };

export function ResearchSessionPanel({ selectedProjectId, onProjectChange, onSessionChange }: Props) {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState('');
  const [devHintOpen, setDevHintOpen] = useState(false);
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
        setMessage(response.status === 502 ? 'The research API is unavailable. Your credential was not saved. Retry when it is available.' : 'Sign in failed. Check your current authorized research access token. Contact your administrator if you do not have a token.');
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
      // Signed-out browsers must not retain protected case content or a
      // restorable selection: clear the stored case and reload into gated states.
      forgetCase();
      window.location.reload();
    } catch { setMessage('Sign out could not complete. Retry to close the research session.'); }
    finally { setBusy(false); }
  }

  function roleLabel(role: string) {
    if (role === 'admin') return 'Administrator — can create cases and edit profiles';
    if (role === 'editor') return 'Editor — can add clinical observations';
    return 'Viewer — read only';
  }

  return <section className="card research-session" aria-labelledby="research-session-title">
    <div className="section-heading">
      <div>
        <h2 id="research-session-title">Research access</h2>
        <p>Use your existing authorized research credential. Synthetic demo access does not require a token.</p>
      </div>
      {session?.authenticated ? <button type="button" className="button-ghost" onClick={() => void signOut()} disabled={busy}>Sign out</button> : null}
    </div>

    {message ? <p role="alert" className="error">{message}</p> : null}
    {busy && session === null ? <p role="status">Checking research access…</p> : null}

    {session?.authenticated ? <>
      {session.projects.length ? <>
        <p className="field-hint">Select a project to view its research cases. Your role determines what you can create and edit.</p>
        <label>Research project
          <select value={selectedProjectId ?? ''} onChange={event => onProjectChange(event.target.value)} disabled={busy}>
            {!selectedProjectId ? <option value="" disabled>Choose a project…</option> : null}
            {session.projects.map(project => <option key={project.project_id} value={project.project_id}>{project.name} · {roleLabel(project.role)}</option>)}
          </select>
        </label>
        <p className="field-hint">{session.projects.length} project{session.projects.length === 1 ? '' : 's'} assigned to your account.</p>
      </> : <div className="card" style={{marginTop: 12}}>
        <h3>No projects yet</h3>
        <p>You are signed in, but no research projects are assigned. Ask your administrator to invite you to a project, or create a project via the admin bootstrap workflow.</p>
        <p className="field-hint">For local development, run the bootstrap script from <code>scripts/</code> to generate a disposable project and token.</p>
      </div>}
      {session.expiresAt ? <p className="muted">Session ends at {new Date(session.expiresAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.</p> : null}
    </> : <>
      <div className="research-choices" style={{display:'grid', gridTemplateColumns:'1.2fr 1fr', gap:16, marginBottom:16}}>
        <div className="card" style={{padding:16}}>
          <p className="eyebrow">OPTION 1 — NO TOKEN NEEDED</p>
          <h3>Explore synthetic demo</h3>
          <p className="field-hint">Try the full CancerOS experience with synthetic geometry, 5 hypothetical scenarios, timeline and 3D viewer — no credential required.</p>
          <a className="button-secondary" href="/demo">Launch synthetic demonstration</a>
        </div>
        <div className="card" style={{padding:16}}>
          <p className="eyebrow">OPTION 2 — RESEARCH DATA</p>
          <h3>Sign in to research workspace</h3>
          <p className="field-hint">Access real research cases with your authorized project token. Contact your research administrator if you do not have a token.</p>
        </div>
      </div>
      <form onSubmit={event => void signIn(event)} autoComplete="off" className="card" style={{padding:20}}>
        <label htmlFor="research-credential">Research access token</label>
        <input id="research-credential" ref={credential} type="password" autoComplete="off" spellCheck={false} maxLength={16384} disabled={busy} placeholder="Paste your RS256 JWT research token" aria-describedby="research-credential-help" />
        <p id="research-credential-help" className="muted">Provided by your research administrator. The browser stores only a short-lived, httpOnly session cookie, not the raw token.</p>
        <div style={{display:'flex', gap: 8, flexWrap:'wrap', alignItems:'center'}}>
          <button type="submit" className="button-primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in to research workspace'}</button>
          <button type="button" className="button-ghost" onClick={()=>setDevHintOpen(v=>!v)}>How to obtain a token?</button>
        </div>
        {devHintOpen && <div className="card" style={{marginTop:12, padding:12}}>
          <h4>How to obtain access</h4>
          <ul className="step-list">
            <li>Ask your research administrator to create a project and invite your account — you will receive a short-lived RS256 JWT.</li>
            <li>For local development, generate a disposable project: run <code>python scripts/dev.py start foundation</code> then use admin bootstrap utilities in <code>scripts/</code> or <code>src/canceros/identity.py</code> test helpers.</li>
            <li>Source registration requires admin role + linkage key; without an eligible source, case creation is blocked with an actionable message and your existing cases remain available.</li>
            <li>Synthetic demo is always available without a token and demonstrates the full 3D + timeline workflow.</li>
          </ul>
        </div>}
      </form>
    </>}
  </section>;
}
