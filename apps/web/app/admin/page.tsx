import Link from 'next/link';

export default function AdminPage() {
  return <>
    <div className="intro"><p className="eyebrow">Data administration</p><h1>Review imports and rights</h1><p className="lead">Limited admin import review completes in COS-074. This page requires an administrator role on the server.</p></div>
    <section className="card"><h2>Availability</h2><p>Administration is unavailable without an authorized admin session. The browser never grants rights or approves sources.</p><p><Link href="/">← Research workspace</Link></p></section>
  </>;
}
