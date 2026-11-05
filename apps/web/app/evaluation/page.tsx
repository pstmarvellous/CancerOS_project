import Link from 'next/link';
import { EvaluationReport } from '../../components/evaluation-report';
import { UxChecklist } from '../../components/ux-checklist';
import { Connectivity } from '../../components/connectivity';

export default function EvaluationPage() {
  return <>
    <div className="intro"><p className="eyebrow">Evaluation report</p><h1>Inspect evidence and limits</h1><p className="lead">A compact report from authorized artifacts: measured scope, open gates and honest UX evidence. Visual polish alone never establishes readiness.</p></div>
    <EvaluationReport />
    <section className="card"><h2>API diagnostics</h2><Connectivity /></section>
    <UxChecklist />
    <p><Link href="/">← Research workspace</Link> · <Link href="/guided-demo">Guided demo</Link></p>
  </>;
}
