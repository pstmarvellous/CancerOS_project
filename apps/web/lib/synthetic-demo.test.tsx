import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { components } from '../../../packages/contracts/generated/api';
import type { DemoBundle, DemoScenario } from './demo-contracts';
import { validateDemoBundle, demoBundle, newDemoSession, hasDemoSession, surfaceDigest } from './synthetic-demo';

type Point = components['schemas']['TimelinePoint'];
type Comparison = components['schemas']['PointComparison'];
type Surface = DemoScenario['meshes'][string];
const uuid = (n: number) => `00000000-0000-4000-8000-${n.toString(16).padStart(12, '0')}`;
const identity = (): Surface['display_to_patient'] => [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]];
function surface(size: number): Surface {
  return { frame: 'RAS', unit: 'mm', algorithm: 'skimage-0.26.0-lewiner/1',
    surface_convention: 'binary_0.5_isosurface_one_zero_pad_integer_voxel_centers',
    measurement_authority: 'source_mask_not_surface',
    vertices: [[0, 0, 0], [size, 0, 0], [0, size, 0], [0, 0, size]],
    normals: [[-1, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
    triangles: [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]],
    bounds_min_mm: [0, 0, 0], bounds_max_mm: [size, size, size],
    display_to_patient: identity(), patient_to_display: identity() };
}
// Fixed comparison outputs are test data, not a second scientific calculator.
function comparison(left: Point, right: Point, delta: string, elapsed: string, endpoint = false): Comparison {
  return { status: 'comparable', left_point_id: left.id, right_point_id: right.id,
    from_state_ids: [...left.state_ids], to_state_ids: [...right.state_ids],
    from_measurement_ids: [...left.source_ids], to_measurement_ids: [...right.source_ids],
    concept: left.concept, metric_code: left.concept, metric_definition: left.metric_definition ?? null,
    unit: 'mm3', lesion_id: left.lesion_id ?? null, origin: 'SYNTHETIC_GENERATED', context: 'SYNTHETIC',
    comparison_context: 'within_simulation', absolute_change: delta, percentage_change: null,
    elapsed_days: elapsed, slope_per_day: null, exact_absolute_change: delta, exact_slope_per_day: null,
    change: 'decreased', ordinal_direction: null, reason_codes: [], description: 'Descriptive synthetic test comparison.',
    method: 'later_minus_earlier/actual_elapsed_days', usable_count: endpoint ? 4 : 2 };
}
// Complete schema-shaped data, independent of SQL/S3 and the ignored local bundle.
// These tests verify bindings and metadata; they do not establish scientific performance.
function bundle(): DemoBundle {
  const recorded = new Date().toISOString();
  const scenarios = Object.fromEntries(['SC-01', 'SC-02', 'SC-03', 'SC-04', 'SC-05'].map((id, family) => {
    const base = 100 + family * 100, branch = uuid(base), run = uuid(base + 1);
    const scope = { mode: 'simulation' as const, data_revision: 1, branch_id: branch, run_id: run };
    const window = { scope, knowledge_as_of: recorded, event_cutoff: null, event_cutoff_shift_basis: null };
    const points: Point[] = ['216', '64', '8', '1'].map((value, n) => ({
      id: uuid(base + 10 + n), patient_id: uuid(1),
      time: { reference: { basis: 'relative_day', value: ['0', '30', '60', '90'][n], time_domain: 'simulation',
        timeline_origin_id: uuid(3), anchor_state_id: null }, precision: 'relative_day', date_shift_basis: null, uncertainty_days: null },
      recorded_at: recorded, revision: 1, origin: 'SYNTHETIC_GENERATED', context: 'SYNTHETIC',
      modality: 'imaging', concept: 'numerical_region_volume',
      numeric_result: { form: 'exact', quantity: { value, unit: 'mm3' } }, canonical_unit: null,
      exact_value: value, metric_definition: 'numerical_region_volume', ordinal_value: null,
      instrument: null, instrument_version: null, symptom_presence: null,
      availability: 'available', missing_reason: null, conflicts: [],
      source_ids: n === 0 ? [uuid(4), run, uuid(5)] : [uuid(base + 10 + n), uuid(base + 30 + n), uuid(5)],
      source_hash: n === 0 ? 'a'.repeat(64) : 'b'.repeat(64), state_ids: [uuid(base + 20 + n)],
      geometry_result_id: n === 0 ? null : uuid(base + 30 + n), lesion_id: uuid(2),
      measurement_basis: n === 0 ? 'baseline_reference' : 'mask_realized', method_version: 'physical-measurements/1',
      summary: null, historical_context: n === 0, branch_id: branch, run_id: run, supersedes_id: null,
    }));
    const meshes = Object.fromEntries(points.map((p, n) => [p.id, surface([6, 4, 2, 1][n])]));
    const segments = [comparison(points[0], points[1], '-152', '30'), comparison(points[1], points[2], '-56', '30'), comparison(points[2], points[3], '-7', '30')];
    const endpoint = comparison(points[0], points[3], '-215', '90', true);
    const scenario: DemoScenario = { id, label: id, description: 'Synthetic test scenario.',
      timeline: { version: 'timeline-page/1', window: structuredClone(window), completion_id: uuid(base + 2),
        items: points, total_points: 4, next_cursor: null, current_patient_revision: 1, historical_revision: false,
        restrictions: [], next_action: 'Choose a synthetic state.',
        features: { version: 'temporal-features/1', scope: structuredClone(scope), selected_point_ids: points.map(p => p.id),
          unresolved_point_ids: [], treatment_point_ids: [], series: [{ concept: 'numerical_region_volume', unit: 'mm3',
            method_version: 'physical-measurements/1', metric_definition: 'numerical_region_volume', lesion_id: uuid(2),
            instrument: null, instrument_version: null, time_partition: JSON.stringify(['simulation', 'relative_day', [uuid(3), 'None'], null]),
            ordered_point_ids: points.map(p => p.id), interval_days: ['30', '30', '30'], usable_count: 4,
            missing_count: 0, censored_count: 0, conflict_point_ids: [], latest_available_id: points[3].id,
            age_days: null, interval_semantics: 'nominal_source_time_no_imputation' }] } },
      trends: { version: 'temporal-trends/1', window: structuredClone(window), tolerance: '0', comparison: structuredClone(endpoint),
        interpretation: 'descriptive_only_no_clinical_significance_or_response_class',
        series: [{ key: 'c'.repeat(64), concept: 'numerical_region_volume', unit: 'mm3', metric_definition: 'numerical_region_volume',
          lesion_id: uuid(2), method_version: 'physical-measurements/1', origin: 'SYNTHETIC_GENERATED', context: 'SYNTHETIC',
          instrument: null, instrument_version: null, points: points.map(p => ({ point_id: p.id,
            x_elapsed_days: p.time.reference.basis === 'relative_day' ? p.time.reference.value : null,
            y: p.numeric_result?.form === 'exact' ? p.numeric_result.quantity.value : null, exact_value: p.exact_value ?? null,
            label: `${p.exact_value} mm3`, qualifier: null, censored_threshold: null, reason_codes: [], time: structuredClone(p.time),
            source_ids: [...p.source_ids], origin: 'SYNTHETIC_GENERATED', context: 'SYNTHETIC' })),
          segments, endpoint, usable_count: 4, description: 'Descriptive synthetic changes only.' }] },
      meshes, meshBindings: Object.fromEntries(points.map(p => [p.id, { point_id: p.id, patient_id: p.patient_id,
        branch_id: branch, run_id: run, state_ids: [...p.state_ids], geometry_result_id: p.geometry_result_id ?? null,
        surface_sha256: surfaceDigest(meshes[p.id]) }])) };
    return [id, scenario];
  }));
  return { version: 'synthetic-demo/2', syntheticOnly: true, sourceOrigin: 'synthetic_engineering_fixture',
    caseLabel: 'Research Demo 01', preparedAt: recorded, expiresAt: new Date(Date.now() + 86400000).toISOString(), scenarios };
}
const scenario = (v: DemoBundle) => v.scenarios['SC-01'];
const point = (v: DemoBundle) => scenario(v).timeline.items[1];
const chart = (v: DemoBundle) => scenario(v).trends.series[0].points[1];
const mesh = (v: DemoBundle) => scenario(v).meshes[point(v).id];
function changeSurface(value: DemoBundle, change: (s: Surface) => void) {
  change(mesh(value));
  // A fresh binding digest must not make invalid geometry metadata acceptable.
  scenario(value).meshBindings[point(value).id].surface_sha256 = surfaceDigest(mesh(value));
}
beforeEach(() => { vi.unstubAllEnvs(); vi.useRealTimers(); });

describe('synthetic-only demo integrity boundary', () => {
  it('accepts a complete synthetic manifest and denies absent opt-in', () => {
    expect(validateDemoBundle(bundle())).toBe(true);
    vi.stubEnv('CANCEROS_SYNTHETIC_DEMO', '');
    expect(demoBundle()).toBeNull();
  });
  const corruptions: [string, (v: DemoBundle) => void][] = [
    ['foreign patient', v => { point(v).patient_id = uuid(9999); }],
    ['foreign branch', v => { point(v).branch_id = uuid(9999); }],
    ['foreign run', v => { point(v).run_id = uuid(9999); }],
    ['foreign state binding', v => { point(v).state_ids = [uuid(9999)]; }],
    ['real origin', v => { point(v).origin = 'REAL_OBSERVED'; }],
    ['foreign trend window', v => { scenario(v).trends.window = structuredClone(v.scenarios['SC-02'].timeline.window); }],
    ['unknown window field', v => {
      Object.assign(scenario(v).timeline.window, { unexpected: 'untrusted' });
      Object.assign(scenario(v).trends.window, { unexpected: 'untrusted' });
    }],
    ['chart value mismatch', v => { chart(v).y = '999'; }],
    ['chart exact value mismatch', v => { chart(v).exact_value = '999'; }],
    ['chart day mismatch', v => { chart(v).x_elapsed_days = '31'; }],
    ['chart time mismatch', v => { Object.assign(chart(v).time.reference, { value: '31' }); }],
    ['chart source mismatch', v => { chart(v).source_ids = [uuid(9999)]; }],
    ['series unit mismatch', v => { scenario(v).trends.series[0].unit = 'cm3'; }],
    ['series metric mismatch', v => { scenario(v).trends.series[0].metric_definition = 'different_metric'; }],
    ['foreign comparison point', v => { scenario(v).trends.series[0].segments[0].right_point_id = uuid(9999); }],
    ['foreign comparison state', v => { scenario(v).trends.series[0].segments[0].to_state_ids = [uuid(9999)]; }],
    ['comparison unit mismatch', v => { scenario(v).trends.series[0].segments[0].unit = 'cm3'; }],
    ['foreign endpoint source', v => { scenario(v).trends.series[0].endpoint!.from_measurement_ids = [uuid(9999)]; }],
    ['foreign report comparison', v => { scenario(v).trends.comparison!.left_point_id = uuid(9999); }],
    ['extra baseline', v => { point(v).measurement_basis = 'baseline_reference'; }],
    ['baseline without historical context', v => { scenario(v).timeline.items[0].historical_context = false; }],
    ['follow-up without geometry result', v => { point(v).geometry_result_id = null; }],
    ['missing geometry state', v => { scenario(v).timeline.items.pop(); }],
    ['nonfinite geometry', v => changeSurface(v, s => { s.vertices[0][0] = Infinity; })],
    ['nonidentity display transform', v => changeSurface(v, s => { s.display_to_patient[0][3] = 10; })],
    ['nonidentity patient transform', v => changeSurface(v, s => { s.patient_to_display[0][0] = 2; })],
    ['incorrect declared bounds', v => changeSurface(v, s => { s.bounds_max_mm[0] = 999; })],
    ['incorrect mesh authority', v => changeSurface(v, s => { Object.assign(s, { measurement_authority: 'surface_mesh' }); })],
    ['incorrect mesh algorithm', v => changeSurface(v, s => { Object.assign(s, { algorithm: 'unknown' }); })],
    ['swapped geometry surfaces', v => { const [a, b] = scenario(v).timeline.items; const meshes = scenario(v).meshes;
      [meshes[a.id], meshes[b.id]] = [meshes[b.id], meshes[a.id]]; }],
    ['foreign mesh binding', v => { scenario(v).meshBindings[point(v).id].patient_id = uuid(9999); }],
    ['unknown root field', v => { Object.assign(v, { unexpected: 'untrusted' }); }],
    ['unknown scenario field', v => { Object.assign(scenario(v), { unexpected: 'untrusted' }); }],
    ['expired bundle', v => { v.expiresAt = new Date(Date.now() - 1000).toISOString(); }],
    ['leaked credential', v => { Object.assign(v, { token: 'private' }); }],
    ['remote resource', v => { scenario(v).description = 'https://private.example/asset'; }],
  ];
  it.each(corruptions)('rejects %s', (_name, corrupt) => {
    const value = bundle();
    expect(validateDemoBundle(value)).toBe(true);
    corrupt(value);
    expect(validateDemoBundle(value)).toBe(false);
  });
  it('rejects absent data', () => { expect(validateDemoBundle(null)).toBe(false); });
  it('binds sessions to the bundle fingerprint, expires them and denies forgeries', () => {
    vi.useFakeTimers();
    const session = newDemoSession('one', new Date(Date.now() + 1000).toISOString());
    expect(hasDemoSession(session.id, 'one')).toBe(true);
    expect(hasDemoSession(session.id, 'two')).toBe(false);
    expect(hasDemoSession('forged', 'one')).toBe(false);
    expect(hasDemoSession(undefined, 'one')).toBe(false);
    vi.advanceTimersByTime(1001);
    expect(hasDemoSession(session.id, 'one')).toBe(false);
    vi.useRealTimers();
  });
});
