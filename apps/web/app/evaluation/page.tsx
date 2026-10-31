import Link from 'next/link';

export default function EvaluationPage() {
  return <>
    <div className="intro"><p className="eyebrow">Evaluation report</p><h1>Inspect evidence and limits</h1><p className="lead">The evaluation screen with actual results, denominators and review status completes in COS-080. Visual polish alone never establishes readiness.</p></div>
    <section className="card"><h2>Availability</h2><p>No evaluation report is published in this build. Passing interface checks do not prove clinical suitability.</p><p><Link href="/">← Research workspace</Link></p></section>
  </>;
}
