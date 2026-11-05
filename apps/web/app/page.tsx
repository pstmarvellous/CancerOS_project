import Link from 'next/link';

export default function Home() {
  return <>
    <section className="intro home-intro">
      <p className="eyebrow">BREAST CANCER RESEARCH · DIGITAL TWIN</p>
      <h1>CancerOS <span>Explore Cancer<br/>Evolution in 3D</span></h1>
      <p className="lead">
        An AI-assisted breast cancer research prototype that visualizes tumor geometry, explores hypothetical
        changes over time, and connects imaging with clinical observations. Two ways to start — no UUID typing required.
      </p>
      <div style={{display:'grid', gridTemplateColumns:'1.2fr 1fr', gap:16, marginTop:20}}>
        <div className="card" style={{padding:20}}>
          <p className="eyebrow" style={{margin:0}}>FOR RESEARCHERS WITH ACCESS</p>
          <h3 style={{margin:'8px 0'}}>Create & manage research cases</h3>
          <p className="field-hint">Sign in with your RS256 JWT research token (provided by administrator), select project, create pseudonymized case, add source-backed observations, view history & charts, reopen after refresh — secure cookie persists.</p>
          <Link className="button-primary" href="/cases">Open research case library</Link>
          <p className="field-hint" style={{marginTop:8}}>Role determines capability: admin creates cases, editor adds observations, viewer reads. Source eligibility gated by privacy + linkage review.</p>
        </div>
        <div className="card" style={{padding:20, background:'#f7f5ff'}}>
          <p className="eyebrow" style={{margin:0}}>NO TOKEN NEEDED</p>
          <h3 style={{margin:'8px 0'}}>Explore synthetic demonstration</h3>
          <p className="field-hint">Full 3D viewer, 5 scenario families (SC-01..05) sharing baseline + 3 follow-ups each, timeline, measurements mm, clinical charts, AI insights — same UI code as real cases, synthetic data only.</p>
          <Link className="button-secondary" href="/demo">Launch synthetic demo</Link> <Link className="button-ghost" href="/guided-demo" style={{marginLeft:8}}>Guided tour</Link>
        </div>
      </div>
      <p className="disclaimer" style={{marginTop:16}}>Both paths use same viewer code. Real research requires token + project provisioning; demo requires nothing. Research prototype, not diagnostic or treatment-recommendation tool.</p>
    </section>
    <div className="grid home-features">
      <section className="card">
        <div className="section-heading"><span className="step">01</span><h2>See the tumor in 3D</h2></div>
        <p>Rotate tumor-region model, inspect measurements mm, provenance badge. Viewer preserves RAS frame, shared physical center translation before GPU upload.</p>
        <p><Link href="/demo?view=twin">Open 3D in demo →</Link></p>
      </section>
      <section className="card">
        <div className="section-heading"><span className="step">02</span><h2>Explore what-if scenarios</h2></div>
        <p>Five hypothetical families show how tumor could evolve. Simulations labeled synthetic, never presented as real outcomes. Baseline shared.</p>
        <p><Link href="/demo?view=scenarios">Open scenarios in demo →</Link></p>
      </section>
      <section className="card">
        <div className="section-heading"><span className="step">03</span><h2>Follow timeline & clinical charts</h2></div>
        <p>Progressive observation timeline + lab small multiples: missing stays missing, censored with comparator, units separate, no interpolation. Reopen case after refresh.</p>
        <p><Link href="/cases">Start with real case →</Link></p>
      </section>
    </div>
  </>;
}
