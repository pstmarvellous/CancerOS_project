'use client';

import Link from 'next/link';
import { Fragment, Suspense, type ReactNode } from 'react';
import { rememberCase, useRestoredCaseSelection, type CaseSelection } from '../lib/case-selection';
import { LoadingState } from './research';

export function CaseBoundPage({
  children,
}: {
  children: (selection: CaseSelection & { restored: boolean }) => ReactNode;
}) {
  return (
    <Suspense fallback={<LoadingState />}>
      <CaseBoundInner>{children}</CaseBoundInner>
    </Suspense>
  );
}

function CaseBoundInner({
  children,
}: {
  children: (selection: CaseSelection & { restored: boolean }) => ReactNode;
}) {
  const selection = useRestoredCaseSelection();
  if (!selection?.ready) return <LoadingState />;
  const { project, patient, restored } = selection;
  if (project && patient) {
    rememberCase(project, patient);
    return (
      <>
        {restored ? (
          <p className="field-hint" role="status">
            Restored your last opened case ({project.slice(0, 8)}… · {patient.slice(0, 8)}…). Every read below is
            still authorized by the server — switch cases from the <Link href="/cases">case library</Link>.
          </p>
        ) : null}
        <Fragment key={[project, patient, selection.branch, selection.state, selection.run, selection.lesion].join('/')}>
          {children({ ...selection, restored })}
        </Fragment>
      </>
    );
  }
  return (
    <section className="card">
      <h2>Open a case first</h2>
      <p>
        This view binds to one authorized case. <Link href="/cases">Open a case from the library</Link> — the
        selection persists across navigation, refresh and browser-back. No UUID entry is needed.
      </p>
    </section>
  );
}
