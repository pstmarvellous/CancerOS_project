import Link from 'next/link';
import { LesionViewer } from '../../components/lesion-viewer';

export default function TwinPage() {
  return (
    <>
      <div className="intro">
        <p className="eyebrow">Twin workspace</p>
        <h1>Inspect the lesion in physical scale</h1>
        <p className="lead">
          Rotate, pan, zoom, fit and reset one authorized lesion with labeled keyboard and button controls. Server
          mask measurements stay authoritative; the browser never normalizes or mixes quantities.
        </p>
        <p className="field-hint">
          Prefer the case workspace Imaging & 3D tab: open a case from the{' '}
          <Link href="/cases">case library</Link> and continue without entering UUIDs. This page keeps direct
          <code>?project=&amp;patient=</code> links working for compatibility.
        </p>
      </div>
      <LesionViewer />
      <p>
        <Link href="/cases">← Case library</Link> · <Link href="/timeline">Observation timeline</Link>
      </p>
    </>
  );
}
