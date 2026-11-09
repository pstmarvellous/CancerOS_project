'use client';

import Link from 'next/link';
import { CaseBoundPage } from '../../components/case-bound-page';
import { ObservationTimeline } from '../../components/observation-timeline';

export default function TimelinePage() {
  return (
    <>
      <p><Link href="/">← Research workspace</Link> · <Link href="/simulation">Simulation workflow</Link></p>
      <div className="intro">
        <p className="eyebrow">Private research history · advanced exact-window tool</p>
        <h1>Inspect an exact observation timeline</h1>
        <p className="lead">Choose a source or published simulation context and inspect immutable observations at a declared revision and knowledge cutoff. The case binds automatically; branch, run, completion and origin identifiers stay explicit because each names a different server-side window.</p>
      </div>
      <CaseBoundPage>
        {(selection) => <ObservationTimeline project={selection.project} patient={selection.patient} />}
      </CaseBoundPage>
    </>
  );
}
