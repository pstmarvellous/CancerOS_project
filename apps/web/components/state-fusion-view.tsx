'use client';

import type { components } from '../../../packages/contracts/generated/api';
import { ProvenanceBadge, TimeLabel } from './research';
import styles from './simulation-workflow.module.css';

type S = components['schemas'];
type Member = S['FusionMember'];
function value(member: Member) {
  if (member.numeric_result?.form === 'exact') return `${member.exact_value ?? member.numeric_result.quantity.value} ${member.numeric_result.quantity.unit}`;
  if (member.numeric_result?.form === 'censored') return `${member.numeric_result.comparator}${member.numeric_result.threshold.value} ${member.numeric_result.threshold.unit} · censored`;
  if (member.numeric_result?.form === 'missing') return `Missing: ${member.numeric_result.missing_reason}`;
  if (member.ordinal_value != null) return `Ordinal rating: ${member.ordinal_value}`;
  return 'See retained source payload; no numerical value inferred.';
}

export function StateFusionView({report}: {report: S['FusionReport']}) {
  const state = report.canonical_state;
  const snapshot = state.snapshot;
  const members = [...report.tumor_state, ...report.clinical_indicators, ...report.treatment_history];
  return <section aria-label="Retained state fusion context"><h3>Retained state context</h3>
    <p><ProvenanceBadge origin={snapshot.origin}/> · <TimeLabel time={snapshot.time}/> · exact revision {snapshot.input_revision}. {state.stale ? 'Historical revision or association head; current use is restricted.' : 'Captured state revision is current.'}</p>
    <p>This is an engineering research context. Tumor measurements and clinical indicators remain separate; this overview provides no overall health score or clinical classification.</p>
    <p>Available modalities: {report.available_modalities.join(', ') || 'None'}. Current use: {state.current_use_allowed ? 'Allowed within existing engineering gates' : 'Restricted'}.</p>
    {state.restrictions.map(reason => <p key={reason}>Restriction: {reason}</p>)}
    {report.blocks.map(block => <section key={block.title} aria-label={`${block.title} state evidence`}><h4>{block.title}</h4>
      {block.reasons.map((reason, index) => <p key={index}>{reason}</p>)}
      {block.member_ids.map(id => {const member = members.find(item => item.id === id); return member ? <article key={id}>
        <p><strong>{member.concept.replaceAll('_', ' ')}</strong> · {member.modality} · {member.role === 'historical_context' ? 'Historical context; not a current observation' : 'Explicit current member'}</p>
        <p>{value(member)} · {member.time ? <TimeLabel time={member.time.reference}/> : <span>Shift basis unavailable; source time is unresolved</span>} · <ProvenanceBadge origin={member.origin}/></p>
        <p>Availability: {member.availability ?? 'Not recorded'}.</p>{member.original_time && <p>Original source time: <TimeLabel time={member.original_time}/></p>}
        <p>{member.primary_for_display ? 'Primary value under documented source-priority policy.' : 'Retained assertion; not selected as primary.'} Measurement definition: {member.metric_definition ?? 'Not an imaging metric'}.</p>
        {(member.uncertainty ?? []).map((reason, index) => <p key={index}>Source limitation: {reason}</p>)}
        <details><summary>Source evidence for {member.concept.replaceAll('_', ' ')} · {id}</summary><p>Source IDs: {member.source_ids.join(', ') || 'None'}. Hash: {member.source_hash}</p><pre>{JSON.stringify(member, null, 2)}</pre></details>
      </article> : <p key={id}>Retained evidence ID: {id}. Inspect the canonical membership below.</p>;})}
      <p>Next action: {block.next_action}</p>
    </section>)}
    <section aria-label="Independent temporal changes"><h4>Temporal changes</h4>{report.temporal_changes.length === 0 ? <p>No compatible temporal comparison is available for this exact state.</p> : report.temporal_changes.map((change, index) => <div key={index}><p>{change.description}</p><p>{change.status} · {change.reason_codes.join(' · ') || 'No additional reason codes'}</p><details><summary>Comparison input evidence {index + 1}</summary><pre>{JSON.stringify(change, null, 2)}</pre></details></div>)}</section>
    {report.conflicts.length > 0 && <details><summary>Retained conflict assertions and reasons</summary><pre>{JSON.stringify(report.conflicts, null, 2)}</pre></details>}
    {report.note_assertions.length > 0 && <details><summary>Source-grounded note assertions · unverified extraction</summary><p>These assertions remain separate from accepted structured measurements. Retained source references do not establish scientific review.</p><pre>{JSON.stringify(report.note_assertions, null, 2)}</pre></details>}
    {report.limitations.map((reason, index) => <p key={index}>Limitation: {reason}</p>)}
    <details><summary>Exact canonical membership and assembly evidence</summary><p>State ID: {snapshot.id}. Branch: {snapshot.branch_id}. Snapshot hash: {state.snapshot_hash}. Assembly policy: {snapshot.assembly_policy_version}. Fusion version: {report.version}.</p><p>Source-priority policy: {report.source_priority_policy}</p><div className={styles.table}><pre>{JSON.stringify(state, null, 2)}</pre></div></details>
  </section>;
}
