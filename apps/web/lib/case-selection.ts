'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
export type CaseSelection = {
  project: string | null;
  patient: string | null;
  branch: string | null;
  state: string | null;
  run: string | null;
  lesion: string | null;
  tab: string | null;
};

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
let lastCase: { project: string | null; patient: string | null } = { project: null, patient: null };

function clean(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  return UUID.test(trimmed) ? trimmed : null;
}

function readRememberedCase(): { project: string | null; patient: string | null } {
  return lastCase;
}

function clearLegacyStorage(): void {
  try {
    localStorage.removeItem('canceros:last_case');
    localStorage.removeItem('canceros:last_project');
  } catch {
    /* Cleanup also works when persistent storage is unavailable. */
  }
}

/** URL selection survives refresh; memory supports navigation within this tab. */
export function readCaseSelection(params: URLSearchParams): CaseSelection & { restored: boolean } {
  const project = clean(params.get('project'));
  const patient = clean(params.get('patient'));
  // Never combine one project's URL with another project's remembered patient.
  const stored = params.has('project') || params.has('patient') ? null : readRememberedCase();
  const branch = clean(params.get('branch'));
  const state = clean(params.get('state'));
  const run = clean(params.get('run'));
  const lesion = clean(params.get('lesion'));
  const tab = params.get('tab');
  return {
    project: project ?? stored?.project ?? null,
    patient: patient ?? stored?.patient ?? null,
    branch,
    state,
    run,
    lesion,
    tab: tab && /^[a-z_]{1,32}$/.test(tab) ? tab : null,
    restored: (!project || !patient) && !!(stored?.project && stored?.patient),
  };
}

export function rememberCase(project: string, patient: string): void {
  const selectedProject = clean(project);
  const selectedPatient = clean(patient);
  lastCase = selectedProject && selectedPatient
    ? { project: selectedProject, patient: selectedPatient }
    : { project: null, patient: null };
  clearLegacyStorage();
}

export function forgetCase(): void {
  lastCase = { project: null, patient: null };
  clearLegacyStorage();
}

/** Preserve the authoritative selection on case-scoped navigation targets. */
export function withCaseSelection(href: string, selection: Pick<CaseSelection, 'project' | 'patient' | 'branch' | 'state' | 'run' | 'lesion'>): string {
  const params = new URLSearchParams();
  if (selection.project) params.set('project', selection.project);
  if (selection.patient) params.set('patient', selection.patient);
  if (selection.branch) params.set('branch', selection.branch);
  if (selection.run) params.set('run', selection.run);
  if (selection.state) params.set('state', selection.state);
  if (selection.lesion) params.set('lesion', selection.lesion);
  const query = params.toString();
  return query ? `${href}?${query}` : href;
}

/** Restore the authorized session's last case into the URL once, so refresh and
 *  browser-back keep the authorized selection. The server still authorizes
 *  every read; this only restores identifiers, never access. */
export function useRestoredCaseSelection(): (CaseSelection & { restored: boolean; ready: boolean }) | null {
  const params = useSearchParams();
  const query = params.toString();
  const restoredQuery = useRef<string | null>(null);
  const [resolved, setResolved] = useState<{ query: string; selection: CaseSelection & { restored: boolean; ready: boolean } } | null>(null);
  useEffect(() => {
    clearLegacyStorage();
    const controller = new AbortController();
    void (async () => {
    const currentParams = new URLSearchParams(query);
    let current = { ...readCaseSelection(currentParams), ready: true };
    if (!currentParams.has('project') && !currentParams.has('patient') && !current.patient) {
      try {
        const response = await fetch('/api/research-selection', { cache: 'no-store', signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]) });
        if (response.ok) {
          const selected = await response.json() as { project?: unknown; patient?: unknown };
          if (!controller.signal.aborted && typeof selected.project === 'string' && typeof selected.patient === 'string') {
            rememberCase(selected.project, selected.patient);
            current = { ...readCaseSelection(currentParams), ready: true };
          }
        }
      } catch { /* Missing session or API leaves the explicit case picker available. */ }
    }
    if (controller.signal.aborted) return;
    if (current.restored && current.project && current.patient) {
      // Same-page query restore: synchronous history update so refresh and
      // browser-back immediately own the authorized selection. Viewers bind
      // from this selection object, so no re-render from the URL is needed.
      const href = withCaseSelection(window.location.pathname, current);
      restoredQuery.current = href.split('?')[1] ?? '';
      window.history.replaceState(null, '', href);
      rememberCase(current.project, current.patient);
    }
    setResolved({ query: current.restored ? restoredQuery.current ?? query : query, selection: { ...current, restored: current.restored || restoredQuery.current === query } });
    })();
    return () => controller.abort();
  }, [query]);
  // Never render the old patient's data for even one frame after URL navigation.
  return resolved?.query === query ? resolved.selection : null;
}
