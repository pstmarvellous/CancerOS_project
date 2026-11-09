'use client';

import Link from 'next/link';
import { Suspense } from 'react';
import { CaseBoundPage } from '../../components/case-bound-page';
import { LoadingState } from '../../components/research';
import { SimulationBuilder } from '../../components/simulation-builder';

export default function SimulationPage() {
  return (
    <>
      <p><Link href="/">← Research workspace</Link> · <Link href="/states">History &amp; states</Link> · <Link href="/activity">Editor activity</Link></p>
      <div className="intro">
        <p className="eyebrow">Private engineering workflow</p>
        <h1>Configure a hypothetical research branch</h1>
        <p className="lead">Inspect an owned baseline, review explicit assumptions and follow a complete run through validation and separate private publication. All five scenario families stay labeled; generation never changes actual history. Context comes from the last opened case — no UUID or token paste needed.</p>
      </div>
      <Suspense fallback={<LoadingState />}>
        <CaseBoundPage>
          {(selection) => <SimulationBuilder project={selection.project!} patient={selection.patient!} selectedBranch={selection.branch} />}
        </CaseBoundPage>
      </Suspense>
    </>
  );
}
