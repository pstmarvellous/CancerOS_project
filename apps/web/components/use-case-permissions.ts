'use client';

import { useCallback, useEffect, useState } from 'react';
import { researchError, researchJson } from '../lib/research-client';

export type CasePermissions = {
  status: 'loading' | 'ready' | 'failed';
  origin: 'real_source' | 'synthetic_engineering_fixture' | null;
  canWrite: boolean;
  message: string;
  reload: () => void;
};

type Profile = { origin?: unknown; profile_revision?: unknown };
type Session = { projects?: { project_id?: unknown; role?: unknown }[] };

/** Workspace-level permission source: independent of which tab mounts, so
 *  Clinical Records never gets stuck on "Loading observation permissions…"
 *  after refresh. Cleared whenever the selected case changes. */
export function useCasePermissions(project: string | null, patient: string | null): CasePermissions {
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>('loading');
  const [origin, setOrigin] = useState<CasePermissions['origin']>(null);
  const [canWrite, setCanWrite] = useState(false);
  const [message, setMessage] = useState('Loading observation permissions…');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!project || !patient) {
      queueMicrotask(() => {
        setStatus('loading');
        setOrigin(null);
        setCanWrite(false);
        setMessage('Loading observation permissions…');
      });
      return;
    }
    const controller = new AbortController();
    queueMicrotask(() => {
      setStatus('loading');
      setOrigin(null);
      setCanWrite(false);
      setMessage('Loading observation permissions…');
    });
    void (async () => {
      try {
        const body = await researchJson<Profile>(
          `/api/research-profile?project=${encodeURIComponent(project)}&patient=${encodeURIComponent(patient)}`,
          { signal: controller.signal },
        );
        const session = await researchJson<Session>('/api/research-session', { signal: controller.signal });
        if (controller.signal.aborted) return;
        const nextOrigin = body.origin === 'real_source' || body.origin === 'synthetic_engineering_fixture' ? body.origin : null;
        const editable = Array.isArray(session.projects) && session.projects.some((p: { project_id?: unknown; role?: unknown } | undefined) => p?.project_id === project && p?.role === 'admin');
        setOrigin(nextOrigin);
        setCanWrite(editable);
        setStatus('ready');
        setMessage('');
      } catch (cause) {
        if (!controller.signal.aborted) {
          setStatus('failed');
          setMessage(researchError(cause));
        }
      }
    })();
    return () => controller.abort();
  }, [project, patient, attempt]);

  const reload = useCallback(() => setAttempt(value => value + 1), []);
  return { status, origin, canWrite, message, reload };
}
