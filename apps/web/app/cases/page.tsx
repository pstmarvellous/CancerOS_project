import Link from 'next/link';
import { CaseLibrary } from '../../components/case-library';

export default function CasesPage() {
  return <>
    <div className="intro"><p className="eyebrow">Research cases</p><h1>Open an authorized case</h1><p className="lead">Cases come from the authorized patient list. Unknown values stay “Not recorded”. Opening a case binds the header, viewer, charts and insights to one selection.</p></div>
    <CaseLibrary/>
    <p><Link href="/">← Research workspace</Link> · <Link href="/guided-demo">Start guided demo</Link></p>
  </>;
}
