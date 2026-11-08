'use client';

import { useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
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
const LAST_CASE_KEY = 'canceros:last_case';

function clean(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  return UUID.test(trimmed) ? trimmed : null;
}

function readStoredCase(): { project: string | null; patient: string | null } {
  try {
    const raw = localStorage.getItem(LAST_CASE_KEY);
    if (!raw) return { project: null, patient: null };
    const parsed = JSON.parse(raw) as { project?: unknown; patient?: unknown };
    return {
      project: typeof parsed.project === 'string' ? clean(parsed.project) : null,
      patient: typeof parsed.patient === 'string' ? clean(parsed.patient) : null,
    };
  } catch {
    return { project: null, patient: null };
  }
}

/** Single authoritative case selection: URL params win; the stored last case
 *  restores direct entries and refreshes. Invalid identifiers never propagate. */
export function readCaseSelection(params: URLSearchParams): CaseSelection & { restored: boolean } {
  const project = clean(params.get('project'));
  const patient = clean(params.get('patient'));
  const stored = project && patient ? null : readStoredCase();
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
  try {
    localStorage.setItem(LAST_CASE_KEY, JSON.stringify({ project, patient, at: Date.now() }));
  } catch {
    /* private-mode storage may be unavailable; the URL remains authoritative */
  }
}

export function forgetCase(): void {
  try {
    localStorage.removeItem(LAST_CASE_KEY);
  } catch {
    /* keep sign-out robust when storage is unavailable */
  }
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

/** Restore the stored last case into the URL once, so refresh and
 *  browser-back keep the authorized selection. The server still authorizes
 *  every read; this only restores identifiers, never access. */
export function useRestoredCaseSelection(): (CaseSelection & { restored: boolean; ready: boolean }) | null {
  const params = useSearchParams();
  // Server prerender has no local storage; resolve the stored case on the
  // client so hydration never locks in an unrestored selection.
  const [selection, setSelection] = useState<(CaseSelection & { restored: boolean; ready: boolean }) | null>(null);
  useEffect(() => {
    const current = { ...readCaseSelection(params), ready: true };
    if (current.restored && current.project && current.patient) {
      // Same-page query restore: synchronous history update so refresh and
      // browser-back immediately own the authorized selection. Viewers bind
      // from this selection object, so no re-render from the URL is needed.
      window.history.replaceState(null, '', withCaseSelection(window.location.pathname, current));
      rememberCase(current.project, current.patient);
    }
    // Local-storage restore is an external subscription applied once per
    // page load; later changes flow through navigation.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelection(current);
    // One-shot restore per page load; later changes flow through navigation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return selection;
}
