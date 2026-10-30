import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { components } from '../../../packages/contracts/generated/api';
import { TrendView, type ChartPoint, type TrendReport } from './trend-view';

type S = components['schemas'];
const origin = '00000000-0000-4000-8000-000000000001';
function point(id: string, day: string, value: string | null, extra: Partial<ChartPoint> = {}): ChartPoint {
  return {point_id: id, x_elapsed_days: day, y: value, exact_value: value, label: `hemoglobin: ${value ?? 'unavailable'} g/dL`, qualifier: null, censored_threshold: null, reason_codes: value === null ? ['MISSING_NUMERIC_VALUE'] : [], time: {reference: {basis: 'relative_day', value: day, time_domain: 'simulation', timeline_origin_id: origin, anchor_state_id: null}, precision: 'relative_day', date_shift_basis: 'not_applicable'}, source_ids: [id], origin: 'SYNTHETIC_GENERATED', context: 'SYNTHETIC', ...extra};
}
function comparison(extra: Partial<S['PointComparison']> = {}): S['PointComparison'] {
  return {status: 'comparable', left_point_id: 'a', right_point_id: 'b', from_state_ids: [], to_state_ids: [], from_measurement_ids: ['a'], to_measurement_ids: ['b'], comparison_context: 'within_simulation', change: 'increased', absolute_change: '2', percentage_change: '20', elapsed_days: '10', slope_per_day: '0.2', exact_absolute_change: '2', exact_slope_per_day: '0.2', reason_codes: [], description: 'Returned descriptive comparison only.', method: 'later_minus_earlier/actual_elapsed_days', usable_count: 2, ...extra};
}
export function trendReport(points = [point('a', '0', '10'), point('b', '1', '11'), point('c', '10', '12')], extra: Partial<S['TrendSeries']> = {}): TrendReport {
  return {version: 'temporal-trends/1', tolerance: '0', window: {scope: {mode: 'source_fixture', data_revision: 1}, knowledge_as_of: '2026-10-29T12:00:00Z', event_cutoff: null}, interpretation: 'descriptive_only_no_clinical_significance_or_response_class', comparison: null, series: [{key: 'hemoglobin', concept: 'hemoglobin', metric_definition: null, unit: 'g/dL', lesion_id: null, method_version: 'clinical-dictionary/1', origin: 'SYNTHETIC_GENERATED', context: 'SYNTHETIC', instrument: null, instrument_version: null, points, segments: points.slice(1).map(() => comparison()), endpoint: comparison(), usable_count: points.filter(item => item.y !== null).length, description: 'Descriptive observed changes only.', ...extra}]};
}

describe('deterministic trend presentation', () => {
  it('places irregular intervals on true elapsed coordinates and preserves exact values and selection', () => {
    const selected = vi.fn();
    const exact = '11.000000000000000001';
    const {container} = render(<TrendView report={trendReport([point('a', '0', '10'), point('b', '1', '11', {exact_value: exact, label: `hemoglobin: ${exact} g/dL`}), point('c', '10', '12')])} onSelect={selected}/>);
    const markers = container.querySelectorAll('circle');
    expect([...markers].map(item => Number(item.getAttribute('cx')))).toEqual([60, 113, 590]);
    expect(screen.getByRole('img', {name: /elapsed-time axis/})).toBeVisible();
    expect(within(screen.getByRole('table')).getByText(`Exact value: ${exact}`)).toBeVisible();
    expect(screen.getByText('Usable point count: 3. Method: later minus earlier divided by actual elapsed days.')).toBeVisible();
    fireEvent.click(screen.getByRole('button', {name: 'Open point b'})); expect(selected).toHaveBeenCalledWith('b');
  });
  it('breaks guides at missing points and retains their known times in the axis', () => {
    const {container} = render(<TrendView report={trendReport([point('a', '0', '10'), point('b', '3', null), point('c', '10', '12'), point('d', '20', null)])} onSelect={vi.fn()}/>);
    expect(screen.queryAllByTestId('trend-guide')).toHaveLength(0);
    expect([...container.querySelectorAll('circle')].map(item => Number(item.getAttribute('cx')))).toEqual([60, 325]);
    expect(within(screen.getByRole('table')).getAllByText('MISSING_NUMERIC_VALUE')).toHaveLength(2);
    expect(screen.getByText(/not interpolated observations/)).toBeVisible();
  });
  it('shows a directional censoring threshold without substituting an exact point or connecting it', () => {
    const censored = point('b', '3', null, {label: 'hemoglobin: <7 g/dL; censored, not an exact value', qualifier: '<', censored_threshold: '7', reason_codes: ['CENSORED_VALUE_NOT_EXACT', 'MISSING_NUMERIC_VALUE']});
    const {container} = render(<TrendView report={trendReport([point('a', '0', '10'), censored, point('c', '10', '12')])} onSelect={vi.fn()}/>);
    expect(screen.getAllByTestId('censored-marker')).toHaveLength(1);
    expect(screen.queryAllByTestId('trend-guide')).toHaveLength(0);
    expect(container.querySelectorAll('circle[fill="#5b21b6"]')).toHaveLength(2);
    expect(screen.getByTestId('censored-marker').querySelector('path')).toHaveAttribute('d', expect.stringContaining('v 16'));
    expect(within(screen.getByRole('table')).getByText(censored.label)).toBeVisible();
  });
  it('retains ordinal semantics without a percentage or slope display', () => {
    render(<TrendView report={trendReport([point('a', '0', '1'), point('b', '10', '6')], {concept: 'fatigue', unit: null, instrument: 'engineering_ordinal', instrument_version: '1', endpoint: comparison({status: 'not_comparable', change: 'ordinal_direction', ordinal_direction: 'increased', percentage_change: null, slope_per_day: null, reason_codes: ['ORDINAL_INSTRUMENT_NO_RATIO_ARITHMETIC']})})} onSelect={vi.fn()}/>);
    expect(screen.getByText(/Ordinal instrument: engineering_ordinal\/1/)).toBeVisible();
    expect(screen.queryByText('Percentage change')).toBeNull();
    expect(screen.queryByText('Endpoint slope')).toBeNull();
    expect(screen.getByText(/ORDINAL_INSTRUMENT_NO_RATIO_ARITHMETIC/)).toBeVisible();
  });
  it('explains absent endpoint evidence, unknown times and an empty report', () => {
    const {rerender} = render(<TrendView report={trendReport([point('a', '0', null, {x_elapsed_days: null, reason_codes: ['TIME_UNRESOLVED']})], {endpoint: null})} onSelect={vi.fn()}/>);
    expect(screen.getByText(/Endpoint comparison unavailable/)).toBeVisible();
    expect(screen.queryByRole('img')).toBeNull();
    expect(within(screen.getByRole('table')).getByText('Unresolved')).toBeVisible();
    rerender(<TrendView report={{...trendReport(), series: []}} onSelect={vi.fn()}/>);
    expect(screen.getByText(/No supported series exists/)).toBeVisible();
  });
  it('shows returned incompatibility reasons without manufacturing percentage values', () => {
    render(<TrendView report={trendReport(undefined, {endpoint: comparison({status: 'not_comparable', absolute_change: null, percentage_change: null, slope_per_day: null, exact_absolute_change: null, exact_slope_per_day: null, reason_codes: ['MASK_METRIC_MISMATCH'], description: 'Comparison unavailable: MASK_METRIC_MISMATCH'})})} onSelect={vi.fn()}/>);
    expect(screen.getByText('Comparison unavailable: MASK_METRIC_MISMATCH')).toBeVisible();
    expect(screen.queryByText('20%')).toBeNull();
  });
});

