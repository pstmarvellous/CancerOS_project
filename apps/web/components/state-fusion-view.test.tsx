import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { components } from '../../../packages/contracts/generated/api';
import { StateFusionView } from './state-fusion-view';

type S = components['schemas'];
const id = '00000000-0000-4000-8000-000000000001';
const hash = 'a'.repeat(64);
const time: S['RelativeTime'] = {basis: 'relative_day', value: '20', time_domain: 'simulation', timeline_origin_id: id, anchor_state_id: null};
function member(extra: Partial<S['FusionMember']> = {}): S['FusionMember'] {
  return {id, source_ids: [id], source_hash: hash, modality: 'laboratory', concept: 'hemoglobin', time: {reference: time, precision: 'relative_day', date_shift_basis: null}, role: 'current', origin: 'SYNTHETIC_GENERATED', context: 'SYNTHETIC', availability: 'available', numeric_result: {form: 'exact', quantity: {value: '9.123456789', unit: 'g/dL'}}, exact_value: '9.123456789123456789', metric_definition: null, ordinal_value: null, uncertainty: ['scientific_review:pending'], primary_for_display: true, ...extra};
}
function report(): S['FusionReport'] {
  return {version: 'state-fusion/1', canonical_state: {snapshot: {id, patient_id: id, branch_id: id, context: 'SYNTHETIC', origin: 'SYNTHETIC_GENERATED', time, input_revision: 2, patient_event_head: 1, assembly_policy_version: 'exact-membership/1', request_manifest_hash: hash, revision_manifest_hash: hash, baseline_hash: hash, clinical_members: [], imaging_members: [], generated_geometry_members: [], generated_clinical_members: [], missing: ['current_imaging_unavailable'], conflicts: [], status: 'ready_partial', technical_readiness: 'ready', scientific_review: 'pending', publication: 'draft', next_action: 'Inspect retained membership'}, snapshot_hash: hash, stale: false, current_use_allowed: true, restrictions: [], review: null, publication: null, available_actions: ['inspect_history'], next_action: 'Inspect retained membership'}, available_modalities: ['laboratory'], tumor_state: [], clinical_indicators: [member()], treatment_history: [], temporal_changes: [], note_assertions: [], conflicts: [], blocks: [{title: 'Available', member_ids: [id], reasons: [], next_action: 'Inspect exact source'}, {title: 'Historical', member_ids: [], reasons: ['No current MRI is supplied'], next_action: 'Inspect historical source time'}, {title: 'Missing', member_ids: [], reasons: ['Note extraction unavailable'], next_action: 'Retain missing evidence'}, {title: 'Conflicting', member_ids: [], reasons: ['No retained contradiction'], next_action: 'Review original sources if new evidence arrives'}], limitations: ['No qualified scientific review'], source_priority_policy: 'usable_structured_member_over_unverified_assertion_display_only/1'};
}

describe('compact exact-membership fusion view', () => {
  it('preserves exact quantities, all four evidence blocks and source drilldown without an overall score', () => {
    render(<StateFusionView report={report()}/>);
    for (const title of ['Available', 'Historical', 'Missing', 'Conflicting']) expect(screen.getByRole('region', {name: `${title} state evidence`})).toBeVisible();
    expect(screen.getByText(/9.123456789123456789 g\/dL/)).toBeVisible();
    expect(screen.getByText('Next action: Retain missing evidence')).toBeVisible();
    expect(screen.getByText('Note extraction unavailable')).toBeVisible();
    expect(screen.getByText(/no overall health score/)).toBeVisible();
    expect(screen.getByText(/Source IDs:/)).toHaveTextContent(id);
    expect(screen.getByText(/Snapshot hash:/)).toHaveTextContent(hash);
  });
  it('keeps historical imaging and source restrictions visible while retaining independent clinical direction', () => {
    const input = report();
    input.canonical_state.stale = true; input.canonical_state.current_use_allowed = false; input.canonical_state.restrictions = ['captured_revision_or_association_head_changed'];
    input.tumor_state = [member({id: 'historical-image', modality: 'imaging', concept: 'numerical_region_volume', role: 'historical_context', metric_definition: 'numerical_region_volume', numeric_result: {form: 'exact', quantity: {value: '64', unit: 'mm3'}}, exact_value: '64'})];
    input.blocks[1].member_ids = ['historical-image'];
    input.temporal_changes = [{status: 'not_comparable', left_point_id: id, right_point_id: id, from_state_ids: [], to_state_ids: [id], from_measurement_ids: [], to_measurement_ids: [], comparison_context: 'within_simulation', change: 'ordinal_direction', ordinal_direction: 'increased', reason_codes: ['ORDINAL_INSTRUMENT_NO_RATIO_ARITHMETIC'], description: 'Internal ordinal fatigue rating increased; tumor numerical region decreased independently.', method: 'later_minus_earlier/actual_elapsed_days', usable_count: 2}];
    render(<StateFusionView report={input}/>);
    expect(within(screen.getByRole('region', {name: 'Historical state evidence'})).getByText(/not a current observation/)).toBeVisible();
    expect(screen.getByText(/Historical revision or association head/)).toBeVisible();
    expect(screen.getByText('Restriction: captured_revision_or_association_head_changed')).toBeVisible();
    expect(screen.getByText('Internal ordinal fatigue rating increased; tumor numerical region decreased independently.')).toBeVisible();
  });
  it('shows retained conflict reasons and ordinal or censored values without ratio arithmetic', () => {
    const input = report();
    input.clinical_indicators = [member({numeric_result: {form: 'censored', comparator: '<', threshold: {value: '7', unit: 'g/dL'}}, exact_value: null}), member({id: 'ordinal', concept: 'fatigue', numeric_result: null, exact_value: null, ordinal_value: '6', primary_for_display: false})];
    input.blocks[3] = {title: 'Conflicting', member_ids: ['ordinal'], reasons: ['INCONSISTENT_VALUES: source assertion retained'], next_action: 'Review both assertions'};
    input.conflicts = [{category: 'INCONSISTENT_VALUES', member_ids: [id, 'ordinal'], reason: 'Retain conflicting source assertion', primary_member_id: id, next_action: 'Review both assertions'}];
    render(<StateFusionView report={input}/>);
    expect(screen.getByText(/<7 g\/dL · censored/)).toBeVisible();
    expect(screen.getByText(/Ordinal rating: 6/)).toBeVisible();
    expect(screen.getByText('INCONSISTENT_VALUES: source assertion retained')).toBeVisible();
    expect(screen.getByText(/Retained assertion; not selected as primary/)).toBeVisible();
    expect(screen.getByText(/No compatible temporal comparison/)).toBeVisible();
    expect(screen.queryByText(/Percentage change/)).toBeNull();
  });
  it('preserves a shifted source date without inventing its missing comparison basis', () => {
    const input = report();
    input.clinical_indicators = [member({time: null, original_time: {basis: 'date', value: '2025-01-02', time_domain: 'source_shifted'}, primary_for_display: false, uncertainty: ['source_shift_basis_unavailable']})];
    render(<StateFusionView report={input}/>);
    expect(screen.getByText('Shift basis unavailable; source time is unresolved')).toBeVisible();
    expect(screen.getByText('2025-01-02 · shifted source date')).toBeVisible();
    expect(screen.getByText(/Source limitation: source_shift_basis_unavailable/)).toBeVisible();
  });
});
