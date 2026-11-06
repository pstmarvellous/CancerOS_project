'use client';

import type { components } from '../../../packages/contracts/generated/api';

type S = components['schemas'];

export function InterpretationPanel({report, groundingStatus}: {report: S['InterpretationReport'] | null; groundingStatus?: string}) {
  if (!report) return <section aria-label="Research interpretation"><h3>Research interpretation</h3><p>No interpretation has been generated for this snapshot. Generate a rule-based summary first; external candidates stay private until grounding and safety review pass.</p></section>;
  const mode = report.execution_mode === 'rule_based_summary' ? 'Rule-based summary · deterministic template' : 'Saved result';
  return <section aria-label="Research interpretation"><h3>Research interpretation · {mode}</h3>
    <p>{report.summary}</p>
    <p><strong>Snapshot {report.snapshot_hash.slice(0, 8)}… · context {report.context_hash.slice(0, 8)}… · {report.findings.length} finding{report.findings.length === 1 ? '' : 's'}</strong>{groundingStatus ? <> · <span className="badge simulated">Grounding: {groundingStatus}</span></> : null}</p>
    {report.findings.map((finding, index) => <details key={index}><summary>{finding.kind.replaceAll('_', ' ')} · {finding.text.slice(0, 80)}</summary>
      <p>{finding.text}</p>
      {finding.metric_value != null && <p>Verified value: {finding.metric_value} {finding.metric_unit ?? ''} ({finding.metric_code ?? 'untyped metric'})</p>}
      {finding.measurement_refs.length > 0 && <p>Case evidence: {finding.measurement_refs.map(ref => ref.slice(0, 8).concat('…')).join(', ')}</p>}
      {finding.passage_refs.length > 0 && <p>Background passages: {finding.passage_refs.map(ref => ref.slice(0, 8).concat('…')).join(', ')} · unreviewed background only, not patient-specific support</p>}
    </details>)}
    {report.uncertainties.map((reason, index) => <p key={index}>Uncertainty: {reason}</p>)}
    {report.limitations.map((reason, index) => <p key={index}>Limitation: {reason}</p>)}
    <p>Next action: {report.next_action}</p>
  </section>;
}
