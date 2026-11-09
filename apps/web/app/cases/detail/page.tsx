import Link from 'next/link';
import { UnifiedWorkspace } from '../../../components/unified-workspace';

export default function CaseDetailPage() {
  return (
    <>
      <div className="intro">
        <p className="eyebrow">Research case · unified workspace</p>
        <h1>Overview, clinical records, charts & imaging</h1>
        <p className="lead">
          One case-centered workspace: profile, timeline of source-backed observations, clinical charts without invented values, imaging and re-open after refresh via secure session. Missing stays “Not recorded”; synthetic stays simulated.
        </p>
      </div>
      <UnifiedWorkspace />
      <nav className="case-footer-links" aria-label="Continue exploring">
        <Link href="/cases">← Case library</Link>
        <Link href="/demo">Explore synthetic demo</Link>
        <Link href="/guided-demo">Guided demo</Link>
      </nav>
    </>
  );
}
