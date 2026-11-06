import Link from 'next/link';
import { EvaluationReport } from '../../components/evaluation-report';
import { UxChecklist } from '../../components/ux-checklist';
import { Connectivity } from '../../components/connectivity';

export default function EvaluationPage() {
  return <>
    <div className="intro"><p className="eyebrow">Evaluation report</p><h1>Inspect evidence and limits</h1><p className="lead">A compact report from authorized artifacts: what a researcher can do today, measured scope, open gates and honest UX evidence. Visual polish alone never establishes readiness. Missing evidence reads Not evaluated.</p></div>
    <section className="card" aria-label="Researcher summary" style={{ borderLeft: '4px solid #0f766e' }}>
      <h2>What this build supports for researchers</h2>
      <ul className="step-list">
        <li><strong>Workspace:</strong> open a case from the library with no UUID typing; Overview, Clinical Records, Charts, Imaging & 3D, and Timeline tabs persist across refresh.</li>
        <li><strong>Twin & timeline:</strong> authorized lesion viewer with a prominent server measurement overlay; branch/state pickers with baseline pinning and A/B compare; charts can filter to the selected state&apos;s source window.</li>
        <li><strong>Scenarios & insights:</strong> guided SC-01 through SC-05 builder with locked treatment exposure; snapshot-bound insights with grouped case versus background evidence and explicit grounding status.</li>
        <li><strong>Provenance:</strong> REAL_OBSERVED vs SYNTHETIC_GENERATED stay labeled; missing stays missing; revisions retained.</li>
      </ul>
      <p className="field-hint">Optional dependencies: automated segmentation checkpoints and live Meta inference remain optional and unverified here. Their absence does not block reference masks, deterministic measurements, the synthetic demo, or rule-based summaries — but it does block claims beyond fixture evidence.</p>
      <p><Link className="button-secondary" href="/cases">Open the case library</Link> <Link className="button-ghost" href="/demo">Open the synthetic demo</Link></p>
    </section>
    <EvaluationReport />
    <section className="card"><h2>API diagnostics (engineering details)</h2><Connectivity /></section>
    <UxChecklist />
    <p><Link href="/">← Research workspace</Link> · <Link href="/guided-demo">Guided demo</Link></p>
  </>;
}
