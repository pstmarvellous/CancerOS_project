'use client';

import Link from 'next/link';
import { CaseBoundPage } from '../../components/case-bound-page';
import { LesionViewer } from '../../components/lesion-viewer';

export default function TwinPage() {
  return (
    <>
      <div className="intro">
        <p className="eyebrow">Twin workspace</p>
        <h1>Inspect the source region in physical scale</h1>
        <p className="lead">
          Rotate, pan, zoom, fit and reset one authorized source region with labeled keyboard and button controls. Server
          mask measurements stay authoritative; the browser never normalizes or mixes quantities.
        </p>
      </div>
      <CaseBoundPage>
        {(selection) => <LesionViewer project={selection.project} patient={selection.patient} />}
      </CaseBoundPage>
      <p>
        <Link href="/cases">← Case library</Link> · <Link href="/timeline">Observation timeline</Link>
      </p>
    </>
  );
}
