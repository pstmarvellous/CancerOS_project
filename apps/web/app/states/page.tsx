import Link from 'next/link';
import { StateTimelineExplorer } from '../../components/state-timeline-explorer';

export default function StatesPage() {
  return (
    <>
      <div className="intro">
        <p className="eyebrow">Synchronized history</p>
        <h1>Inspect one persisted state at a time</h1>
        <p className="lead">
          One URL-owned branch and state stays synchronized across the header, mesh, measurements, charts and
          interpretation scope. Only persisted discrete snapshots load; nothing morphs, interpolates or autoplays.
        </p>
      </div>
      <StateTimelineExplorer />
      <p>
        <Link href="/cases">← Case library</Link> · <Link href="/twin">Twin workspace</Link> · <Link href="/timeline">Observation timeline</Link>
      </p>
    </>
  );
}
