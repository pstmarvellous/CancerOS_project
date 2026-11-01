import { Connectivity } from '../components/connectivity';
import Link from 'next/link';
import { ModalityStatus, ProvenanceBadge, TimeLabel } from '../components/research';

export default function Home() {
  return <>
    <section className="intro"><p className="eyebrow">BREAST CANCER RESEARCH</p><h1>A foundation for traceable research.</h1><p className="lead">Explore imaging and longitudinal observations with clear source history. This foundation has no patient case loaded.</p></section>
    <div className="grid">
      <section className="card"><div className="section-heading"><span className="step">01</span><h2>Research workspace</h2></div><p>Case browsing, measured lesion geometry, synchronized states, charts, scenarios and grounded insights are implemented against authorized APIs with fixture-tested evidence.</p><ul className="capabilities"><li>Case browser <span>Fixture-tested</span></li><li>Imaging and twin viewer <span>Fixture-tested</span></li><li>Five hypothetical scenarios <span>Engineering workflow; scientific gates open</span></li><li>Evidence-linked interpretation <span>Fixture-tested</span></li></ul><p><Link href="/cases">Open the case library</Link> · <Link href="/guided-demo">Follow the guided demo</Link> · <Link href="/evaluation">Inspect evaluation limits</Link></p></section>
      <section className="card"><div className="section-heading"><span className="step">02</span><h2>Local API connection</h2></div><p>Check whether the API process can respond. This does not test medical functionality.</p><Connectivity /></section>
    </div>
    <section className="card examples"><p className="eyebrow">PRIVATE ENGINEERING WORKFLOW</p><h2>Inspect a measured region.</h2><p>Open an authorized, technically checked mesh with its mask measurements and source labels. Synthetic fixtures do not establish patient anatomy or clinical validity.</p><Link href="/mesh-preview">Open private mesh preview</Link><p><Link href="/timeline">Inspect an exact observation timeline</Link> · <Link href="/simulation">Configure a hypothetical research branch</Link> · accepted authentic baseline and scientific-policy gates remain open.</p></section>
    <section className="card examples"><p className="eyebrow">COMPONENT REFERENCE · ENGINEERING EXAMPLES</p><h2>Make the origin visible.</h2><p>These labels demonstrate interface behavior. They do not describe a patient or an available model.</p><div className="badges"><ProvenanceBadge origin="REAL_OBSERVED"/><ProvenanceBadge origin="REAL_DERIVED"/><ProvenanceBadge origin="SYNTHETIC_GENERATED"/><ProvenanceBadge origin="INTERPOLATED"/><ProvenanceBadge origin="MODEL_PREDICTED"/></div><p className="simulation-notice">Hypothetical simulation from a real research baseline. This is not an observed outcome or a validated prediction of this person&apos;s treatment response.</p><div className="missing"><TimeLabel time={null}/><ModalityStatus label="Imaging" availability="unavailable"/></div></section>
  </>;
}
