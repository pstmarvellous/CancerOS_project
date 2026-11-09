import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { forgetCase, useRestoredCaseSelection } from './case-selection';

const route = vi.hoisted(() => ({ query: '' }));
vi.mock('next/navigation', () => ({ useSearchParams: () => new URLSearchParams(route.query) }));
const project = '00000000-0000-4000-8000-000000000001';
const patientA = '00000000-0000-4000-8000-000000000002';
const patientB = '00000000-0000-4000-8000-000000000003';
beforeEach(() => { forgetCase(); route.query = `project=${project}&patient=${patientA}`; });
afterEach(() => vi.unstubAllGlobals());

it('rebinds case and snapshot when query changes, including browser-back', async () => {
  const { result, rerender } = renderHook(useRestoredCaseSelection);
  await waitFor(() => expect(result.current?.patient).toBe(patientA));
  const first = route.query;
  route.query = `project=${project}&patient=${patientB}&state=${patientA}`;
  rerender();
  await waitFor(() => expect(result.current).toMatchObject({ patient: patientB, state: patientA }));
  route.query = first;
  rerender();
  await waitFor(() => expect(result.current).toMatchObject({ patient: patientA, state: null }));
});

it('does not let late session restoration overwrite a newly selected case', async () => {
  route.query = '';
  let finish!: (value: Response) => void;
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { finish = resolve; })));
  const { result, rerender } = renderHook(useRestoredCaseSelection);
  route.query = `project=${project}&patient=${patientB}`;
  rerender();
  await act(async () => { finish(Response.json({ project, patient: patientA })); });
  await waitFor(() => expect(result.current?.patient).toBe(patientB));
});
