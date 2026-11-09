'use client';

import Link from 'next/link';
import { CaseBoundPage } from '../../components/case-bound-page';
import { ClinicalChartsExplorer } from '../../components/clinical-charts-explorer';

export default function ChartsPage() {
  return (
    <>
      <div className="intro">
        <p className="eyebrow">Linked clinical history</p>
        <h1>Charts and tables without invented values</h1>
        <p className="lead">
          Laboratory, vital-sign, symptom and treatment tracks show actual collection times and equivalent
          tables. Missing stays missing; censored values keep their comparator and threshold.
        </p>
      </div>
      <CaseBoundPage>
        {(selection) => <ClinicalChartsExplorer project={selection.project} patient={selection.patient} />}
      </CaseBoundPage>
      <p>
        <Link href="/cases">← Case library</Link> · <Link href="/cases/detail">Case profile</Link> · <Link href="/states">History &amp; states</Link>
      </p>
    </>
  );
}
