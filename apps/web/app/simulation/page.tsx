import Link from 'next/link';
import { SimulationWorkflow } from '../../components/simulation-workflow';

export default function SimulationPage() {
  return <main id="main-content" tabIndex={-1}><p><Link href="/">← Research workspace</Link></p><div className="intro"><p className="eyebrow">Private engineering workflow</p><h1>Configure a hypothetical research branch</h1><p className="lead">Inspect an owned baseline, review explicit assumptions and follow a complete run through validation and separate private publication.</p></div><SimulationWorkflow/></main>;
}
