'use client';

import Link from 'next/link';
import { CaseBoundPage } from '../../components/case-bound-page';
import { StateTimelineExplorer } from '../../components/state-timeline-explorer';

export default function StatesPage() {
  return (
    <>
      <div className="intro">
        <p className="eyebrow">Synchronized history</p>
        <h1>Inspect one saved timepoint at a time</h1>
        <p className="lead">
          One URL-owned branch and state stays synchronized across the header, mesh, measurements, charts and
          interpretation scope. Only saved discrete snapshots load; nothing morphs, interpolates or autoplays.
        </p>
      </div>
      <CaseBoundPage>
        {(selection) => <StateTimelineExplorer project={selection.project} patient={selection.patient} />}
      </CaseBoundPage>
      <p>
        <Link href="/cases">← Case library</Link> · <Link href="/twin">Twin workspace</Link> · <Link href="/timeline">Observation timeline</Link>
      </p>
    </>
  );
}
