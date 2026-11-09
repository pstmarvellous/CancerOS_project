'use client';

import Link from 'next/link';
import { CaseBoundPage } from '../../components/case-bound-page';
import { InsightsExplorer } from '../../components/insights-explorer';

export default function InsightsPage() {
  return (
    <>
      <div className="intro">
        <p className="eyebrow">Evidence-linked insights</p>
        <h1>Supported findings with honest uncertainty</h1>
        <p className="lead">
          Each finding opens its exact case observation or approved passage. Case evidence stays separate
          from background passages; unknown uncertainty is never a confidence gauge.
        </p>
      </div>
      <CaseBoundPage>
        {(selection) => <InsightsExplorer project={selection.project} patient={selection.patient} />}
      </CaseBoundPage>
      <p>
        <Link href="/cases">← Case library</Link> · <Link href="/states">History &amp; states</Link> · <Link href="/charts">Clinical charts</Link>
      </p>
    </>
  );
}
