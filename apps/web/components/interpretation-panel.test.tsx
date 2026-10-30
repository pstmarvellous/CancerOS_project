import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { components } from '../../../packages/contracts/generated/api';
import { InterpretationPanel } from './interpretation-panel';

type S = components['schemas'];
const id = '00000000-0000-4000-8000-000000000001';
const hash = 'a'.repeat(64);
function report(): S['InterpretationReport'] {
  return {schema_version: 'interpretation/1', context_snapshot_id: id, context_hash: hash, snapshot_hash: hash, execution_mode: 'rule_based_summary', summary: 'Rule-based summary of 1 retained measurements, 0 unverified assertions and 1 unreviewed passages.', findings: [{kind: 'observed_measurement', text: 'Retained hemoglobin value 9 g/dL (member time basis relative_day).', measurement_refs: [id], passage_refs: [], metric_code: 'hemoglobin', metric_value: '9', metric_unit: 'g_dL'}], uncertainties: ['No recorded conflicts.'], limitations: ['Rule-based summary only; no clinical interpretation, diagnosis or advice.'], visibility: 'visible_template', next_action: 'proceed_to_bounded_generation_review'};
}

describe('bounded interpretation panel', () => {
  it('labels rule-based execution and links findings to source references', () => {
    render(<InterpretationPanel report={report()}/>);
    expect(screen.getByRole('heading', {name: /Rule-based summary/})).toBeVisible();
    expect(screen.getByText(/1 retained measurements/)).toBeVisible();
    fireEvent.click(screen.getByText(/observed measurement/));
    expect(screen.getByText(/Verified value: 9 g_dL/)).toBeVisible();
    expect(screen.getByText(/Next action:/)).toBeVisible();
  });
  it('explains the empty state without placeholders', () => {
    render(<InterpretationPanel report={null}/>);
    expect(screen.getByText(/No interpretation has been generated/)).toBeVisible();
    expect(screen.getByText(/external candidates stay private/)).toBeVisible();
  });
});
