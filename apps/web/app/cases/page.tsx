import Link from 'next/link';

export default function CasesPage() {
  return <>
    <div className="intro"><p className="eyebrow">Research cases</p><h1>Open an authorized case</h1><p className="lead">Case browsing with server-backed summaries, pagination and longitudinal availability completes in COS-073. No case is loaded yet.</p></div>
    <section className="card"><h2>What to expect</h2><p>Desktop shows a compact table; narrow screens show labeled cards. Unknown values stay “Not recorded”. Opening a case binds the header, viewer, charts and insights to one selection.</p><p><Link href="/">← Research workspace</Link></p></section>
  </>;
}
