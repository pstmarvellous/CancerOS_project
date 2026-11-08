import Link from 'next/link';
import { demoBundle } from '../lib/synthetic-demo';

// Availability must be evaluated per request: the bundle expires and the
// launch environment varies between build time and request time.
export const dynamic = 'force-dynamic';

export default function Home() {
  const demo = demoBundle();
  return <>
    <section className="intro home-intro">
      <p className="eyebrow">CANCER RESEARCH PROTOTYPE</p>
      <h1>Explore How a Tumor Could Change Over Time</h1>
      <p className="lead">
        CancerOS demonstrates how medical images, 3D visualization, hypothetical simulations
        and AI can work together in one research application.
      </p>
      <div style={{display:'flex', flexWrap:'wrap', gap:12, marginTop:20}}>
        {demo ? (
          <Link className="button-primary" href="/demo">Explore Interactive Demo</Link>
        ) : (
          <>
            <span className="button-primary" aria-disabled="true" style={{opacity:0.55}}>Explore Interactive Demo</span>
            <p className="field-hint" role="status" style={{flexBasis:'100%', margin:0}}>
              The interactive demo is being prepared. Run <code>uv run python scripts/prepare_synthetic_demo.py</code> once,
              then reload this page. Research cases remain available below.
            </p>
          </>
        )}
        <Link className="button-secondary" href="/cases">Create or Open a Research Case</Link>
      </div>
      <p className="disclaimer" style={{marginTop:16}}>Demonstration uses only synthetic data — no real patient information. Research prototype; not a medical device.</p>
    </section>
    <div className="grid home-features">
      <section className="card">
        <div className="section-heading"><span className="step">01</span><h2>Explore a 3D model</h2></div>
        <p>Rotate a tumor-region model and inspect its measured size in millimeters.</p>
        <p>{demo ? <Link href="/demo?view=twin">Open 3D in demo →</Link> : <span>Demo preparing…</span>}</p>
      </section>
      <section className="card">
        <div className="section-heading"><span className="step">02</span><h2>Compare hypothetical scenarios</h2></div>
        <p>Five labeled what-if families show how a tumor could evolve. Never presented as real outcomes.</p>
        <p>{demo ? <Link href="/demo?view=scenarios">Open scenarios in demo →</Link> : <span>Demo preparing…</span>}</p>
      </section>
      <section className="card">
        <div className="section-heading"><span className="step">03</span><h2>Understand the associated data</h2></div>
        <p>Timelines, measurements and evidence stay linked to the selected case or scenario.</p>
        <p><Link href="/cases">Start with a research case →</Link></p>
      </section>
    </div>
  </>;
}
