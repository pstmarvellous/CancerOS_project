import Link from 'next/link';

export default function Home() {
  return <>
    <section className="intro home-intro">
      <p className="eyebrow">BREAST CANCER RESEARCH</p>
      <h1>CancerOS <span>Explore Cancer<br/>Evolution in 3D</span></h1>
      <p className="lead">
        An AI-assisted breast cancer research prototype that visualizes tumor geometry, explores hypothetical
        changes over time, and connects imaging with clinical observations.
      </p>
      <p className="actions">
        <Link className="button-primary" href="/cases">Create Research Case</Link>{' '}
        <Link className="button-secondary" href="/demo">Explore Synthetic Demonstration</Link>{' '}
        <span className="field-hint">Demo link preserved for verified regression: <Link href="/demo">Launch Digital Twin Demo</Link></span>
      </p>
      <p className="disclaimer">The demo uses synthetic data. Research prototype, not a diagnostic or treatment-recommendation tool.</p>
    </section>
    <div className="grid home-features">
      <section className="card">
        <div className="section-heading"><span className="step">01</span><h2>See the tumor in 3D</h2></div>
        <p>Rotate a synthetic tumor-region model built from a processed mask. Inspect backend measurements and see where each value comes from.</p>
      </section>
      <section className="card">
        <div className="section-heading"><span className="step">02</span><h2>Explore what-if scenarios</h2></div>
        <p>Five labeled hypothetical families show how the tumor could evolve. Simulations are clearly marked — never presented as real outcomes.</p>
      </section>
      <section className="card">
        <div className="section-heading"><span className="step">03</span><h2>Follow the timeline</h2></div>
        <p>Move across observed and simulated states. Charts, measurements and interpretations stay synchronized to the selected state.</p>
      </section>
    </div>
  </>;
}
