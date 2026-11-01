import Link from 'next/link';
import { SimulationWorkflow } from '../../components/simulation-workflow';

export default function SimulationPage() {
  return <><p><Link href="/">← Research workspace</Link> · <Link href="/states">History &amp; states</Link> · <Link href="/activity">Editor activity</Link></p><div className="intro"><p className="eyebrow">Private engineering workflow</p><h1>Configure a hypothetical research branch</h1><p className="lead">Inspect an owned baseline, review explicit assumptions and follow a complete run through validation and separate private publication. All five scenario families stay labeled; generation never changes actual history.</p></div><SimulationWorkflow/></>;
}
