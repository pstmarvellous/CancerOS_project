import Link from 'next/link';

export default function GuidedDemoPage() {
  return <>
    <div className="intro"><p className="eyebrow">Guided demonstration</p><h1>Follow a pinned authorized path</h1><p className="lead">The guided demo with preflight checks, pinned IDs and reset behavior completes in COS-080. Nothing here runs a model or changes patient state.</p></div>
    <section className="card"><h2>Availability</h2><p>The demo path is not configured in this build. A static preview or recording is labeled and never presented as a live result.</p><p><Link href="/">← Research workspace</Link></p></section>
  </>;
}
