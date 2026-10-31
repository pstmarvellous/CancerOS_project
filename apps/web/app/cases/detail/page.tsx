import Link from 'next/link';
import { CaseWorkspace } from '../../../components/case-workspace';

export default function CaseDetailPage() {
  return (
    <>
      <div className="intro">
        <p className="eyebrow">Research case</p>
        <h1>Profile, sources and completeness</h1>
        <p className="lead">
          Observed facts, source drill-down and editor workflows bind to one authorized case. Missing values stay
          “Not recorded”; simulated descendants stay simulated.
        </p>
      </div>
      <CaseWorkspace />
      <p>
        <Link href="/cases">← Case library</Link> · <Link href="/guided-demo">Start guided demo</Link>
      </p>
    </>
  );
}
