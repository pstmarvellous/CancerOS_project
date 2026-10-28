'use client';
import { useState } from 'react';
import type { paths } from '@canceros/contracts';

type Health = paths['/health/live']['get']['responses'][200]['content']['application/json'];

export function Connectivity() {
  const [status, setStatus] = useState('Not checked');
  const [busy, setBusy] = useState(false);
  async function check() {
    setBusy(true);
    setStatus('Checking API process…');
    try {
      const response = await fetch('/api/health', {cache: 'no-store', signal: AbortSignal.timeout(5000)});
      if (!response.ok) throw new Error('Unavailable');
      const data: Health = await response.json();
      if (data.status !== 'ok') throw new Error('Unexpected health response');
      setStatus('API process reachable. Dependency and scientific readiness are separate checks.');
    } catch {
      setStatus('API process unavailable. Start the local API and retry.');
    } finally {
      setBusy(false);
    }
  }
  return <div className="connectivity"><p role="status" aria-live="polite">{status}</p><button onClick={check} disabled={busy}>{busy ? 'Checking…' : 'Check API connection'}</button></div>;
}
