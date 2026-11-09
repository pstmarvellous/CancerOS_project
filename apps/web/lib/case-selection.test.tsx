import { beforeEach, expect, it } from 'vitest';
import { forgetCase, readCaseSelection, rememberCase, withCaseSelection } from './case-selection';

const project = '00000000-0000-4000-8000-000000000001';
const patient = '00000000-0000-4000-8000-000000000002';
const otherProject = '00000000-0000-4000-8000-000000000003';

beforeEach(() => { forgetCase(); localStorage.clear(); sessionStorage.clear(); });

it('remembers navigation in memory without persisting case identifiers', () => {
  rememberCase(project, patient);
  expect(readCaseSelection(new URLSearchParams())).toMatchObject({ project, patient, restored: true });
  expect(localStorage.length).toBe(0);
  expect(sessionStorage.length).toBe(0);
});

it('preserves a complete selection in the URL after memory is cleared', () => {
  rememberCase(project, patient);
  const url = withCaseSelection('/simulation', readCaseSelection(new URLSearchParams()));
  forgetCase();
  expect(readCaseSelection(new URL(url, 'https://example.org').searchParams)).toMatchObject({ project, patient, restored: false });
  expect(readCaseSelection(new URLSearchParams()).patient).toBeNull();
});

it('does not combine a partial or invalid URL with a different remembered case', () => {
  rememberCase(project, patient);
  expect(readCaseSelection(new URLSearchParams({ project: otherProject }))).toMatchObject({ project: otherProject, patient: null, restored: false });
  expect(readCaseSelection(new URLSearchParams({ patient }))).toMatchObject({ project: null, patient, restored: false });
  expect(readCaseSelection(new URLSearchParams({ project: 'invalid' }))).toMatchObject({ project: null, patient: null, restored: false });
});

it('sign-out clears memory and both legacy persistent keys without restoring them', () => {
  localStorage.setItem('canceros:last_case', JSON.stringify({ project, patient }));
  localStorage.setItem('canceros:last_project', project);
  expect(readCaseSelection(new URLSearchParams()).patient).toBeNull();
  rememberCase(project, patient);
  forgetCase();
  expect(readCaseSelection(new URLSearchParams()).patient).toBeNull();
  expect(localStorage.length).toBe(0);
});
