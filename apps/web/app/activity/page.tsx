import Link from 'next/link';

export default function ActivityPage() {
  return <>
    <div className="intro"><p className="eyebrow">Editor activity</p><h1>Review authorized work</h1><p className="lead">Editor activity with authorized job discovery completes in COS-078. This page requires editor permission on the server.</p></div>
    <section className="card"><h2>Availability</h2><p>Activity is unavailable without an authorized editor session. No observation or publication runs from this placeholder.</p><p><Link href="/">← Research workspace</Link></p></section>
  </>;
}
