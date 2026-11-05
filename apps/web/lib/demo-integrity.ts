import { createHash } from 'node:crypto';
import { isDeepStrictEqual as equal } from 'node:util';
import type { components } from '../../../packages/contracts/generated/api';
import type { DemoScenario } from './demo-contracts';

type S = components['schemas'];
type Point = S['TimelinePoint'];
type Comparison = S['PointComparison'];
type Surface = DemoScenario['meshes'][string];
const UUID = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
const HASH = /^[0-9a-f]{64}$/;
const identity = (matrix: number[][]) => matrix.length === 4 && matrix.every((row, i) => row.length === 4 && row.every((v, j) => v === (i === j ? 1 : 0)));
const ids = (values: string[], minimum = 0) => Array.isArray(values) && values.length >= minimum && values.length <= 64 && new Set(values).size === values.length && values.every(v => UUID.test(v));
const text = (value: string) => typeof value === 'string' && value.length > 0 && value.length <= 2000;
export const onlyKeys = (value: object, allowed: string) => !!value && !Array.isArray(value) && Object.keys(value).every(key => allowed.split(' ').includes(key));

// Lexical equality preserves exact backend decimals without binary64 arithmetic.
// Number conversion is used only to reject out-of-range plotting inputs.
function decimal(value: unknown): string | null {
  if (typeof value !== 'string' || value.length > 180 || !/^-?(0|[1-9]\d*)(\.\d+)?$/.test(value) ||
    !Number.isFinite(Number(value)) || Math.abs(Number(value)) >= 1e15) return null;
  const trimmed = value.includes('.') ? value.replace(/0+$/, '').replace(/\.$/, '') : value;
  return trimmed === '-0' ? '0' : trimmed;
}
const sameDecimal = (a: unknown, b: unknown) => decimal(a) !== null && decimal(a) === decimal(b);
const optionalDecimal = (v: unknown) => v === null || decimal(v) !== null;
const day = (p: Point) => p.time.reference.basis === 'relative_day' ? p.time.reference.value : null;

function validWindow(window: S['TimelineWindow']) {
  return onlyKeys(window, 'scope event_cutoff knowledge_as_of event_cutoff_shift_basis') &&
    onlyKeys(window.scope, 'mode data_revision branch_id run_id') && Number.isFinite(Date.parse(window.knowledge_as_of)) &&
    window.event_cutoff === null && window.event_cutoff_shift_basis === null;
}

function validNumeric(result: Point['numeric_result']) {
  if (result === null) return true;
  const quantity = (value: S['Quantity']) => onlyKeys(value, 'value unit') && decimal(value.value) !== null && typeof value.unit === 'string' && value.unit.length > 0 && value.unit.length <= 32;
  if (result?.form === 'exact') return onlyKeys(result, 'form quantity') && quantity(result.quantity);
  if (result?.form === 'censored') return onlyKeys(result, 'form comparator threshold') && ['<', '<=', '>', '>='].includes(result.comparator) && quantity(result.threshold);
  return result?.form === 'missing' && onlyKeys(result, 'form missing_reason') && text(result.missing_reason);
}

/** Binary protocol shared with prepare_synthetic_demo.py; no JSON float ambiguity. */
export function surfaceDigest(surface: Surface): string {
  const bytes = Buffer.allocUnsafe(12 + surface.vertices.length * 24 + surface.triangles.length * 12 + surface.normals.length * 24 + 38 * 8);
  let offset = 0;
  for (const count of [surface.vertices.length, surface.triangles.length, surface.normals.length]) { bytes.writeUInt32LE(count, offset); offset += 4; }
  const write = (rows: number[][], integer = false) => {
    for (const row of rows) for (const value of row) {
      if (integer) { bytes.writeUInt32LE(value, offset); offset += 4; }
      else { bytes.writeDoubleLE(value, offset); offset += 8; }
    }
  };
  write(surface.vertices); write(surface.triangles, true); write(surface.normals);
  write([surface.bounds_min_mm, surface.bounds_max_mm]); write(surface.display_to_patient); write(surface.patient_to_display);
  return createHash('sha256').update('canceros-demo-surface/1\n')
    .update(JSON.stringify([surface.frame, surface.unit, surface.algorithm, surface.surface_convention, surface.measurement_authority]) + '\n')
    .update(bytes).digest('hex');
}

function validSurface(surface: Surface) {
  if (!onlyKeys(surface, 'vertices triangles normals bounds_min_mm bounds_max_mm frame unit algorithm surface_convention display_to_patient patient_to_display measurement_authority') ||
    surface.frame !== 'RAS' || surface.unit !== 'mm' || surface.algorithm !== 'skimage-0.26.0-lewiner/1' ||
    surface.surface_convention !== 'binary_0.5_isosurface_one_zero_pad_integer_voxel_centers' ||
    surface.measurement_authority !== 'source_mask_not_surface' || !identity(surface.display_to_patient) || !identity(surface.patient_to_display) ||
    surface.vertices.length < 4 || surface.vertices.length > 50000 || surface.triangles.length < 4 || surface.triangles.length > 100000 || surface.normals.length !== surface.vertices.length ||
    ![...surface.vertices, ...surface.normals, surface.bounds_min_mm, surface.bounds_max_mm].every(row => row.length === 3 && row.every(Number.isFinite)) ||
    !surface.triangles.every(row => row.length === 3 && row.every(n => Number.isInteger(n) && n >= 0 && n < surface.vertices.length))) return false;
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  for (const row of surface.vertices) for (let axis = 0; axis < 3; axis++) { min[axis] = Math.min(min[axis], row[axis]); max[axis] = Math.max(max[axis], row[axis]); }
  return equal(min, surface.bounds_min_mm) && equal(max, surface.bounds_max_mm);
}

function validComparison(value: Comparison | null, points: Map<string, Point>) {
  if (value === null) return true;
  if (!onlyKeys(value, 'status left_point_id right_point_id from_state_ids to_state_ids from_measurement_ids to_measurement_ids concept metric_code metric_definition unit lesion_id origin context comparison_context absolute_change percentage_change elapsed_days slope_per_day exact_absolute_change exact_slope_per_day change ordinal_direction reason_codes description method usable_count')) return false;
  const left = points.get(value.left_point_id ?? ''), right = points.get(value.right_point_id ?? '');
  return !!left && !!right && left.id !== right.id && value.origin === 'SYNTHETIC_GENERATED' && value.context === 'SYNTHETIC' && value.comparison_context === 'within_simulation' &&
    value.concept === left.concept && value.metric_code === left.concept && value.metric_definition === left.metric_definition && value.lesion_id === left.lesion_id &&
    (value.metric_definition !== 'numerical_region_volume' || value.unit === 'mm3') &&
    (value.status !== 'comparable' || right.concept === left.concept && right.metric_definition === left.metric_definition && right.lesion_id === left.lesion_id) &&
    equal(value.from_state_ids, left.state_ids) && equal(value.to_state_ids, right.state_ids) && equal(value.from_measurement_ids, left.source_ids) && equal(value.to_measurement_ids, right.source_ids) &&
    ['comparable', 'not_comparable', 'insufficient_data'].includes(value.status) && Array.isArray(value.reason_codes) &&
    [value.absolute_change, value.percentage_change, value.elapsed_days, value.slope_per_day, value.exact_absolute_change, value.exact_slope_per_day].every(optionalDecimal);
}

export function validScenario(scenario: DemoScenario, family: string): boolean {
  if (!onlyKeys(scenario, 'id label description timeline trends meshes meshBindings') || scenario.id !== family || !text(scenario.label) || !text(scenario.description)) return false;
  const { timeline, trends, meshes, meshBindings } = scenario;
  const scope = timeline.window.scope;
  if (!onlyKeys(timeline, 'version window completion_id items features total_points next_cursor current_patient_revision historical_revision restrictions next_action') ||
    timeline.version !== 'timeline-page/1' || timeline.next_cursor !== null || !UUID.test(timeline.completion_id ?? '') ||
    !validWindow(timeline.window) || scope.mode !== 'simulation' || !UUID.test(scope.branch_id ?? '') || !UUID.test(scope.run_id ?? '') || !Number.isSafeInteger(scope.data_revision) || scope.data_revision < 1 ||
    timeline.items.length > 100 || timeline.total_points !== timeline.items.length || !equal(trends.window, timeline.window) ||
    !onlyKeys(trends, 'version window tolerance series comparison interpretation') || trends.version !== 'temporal-trends/1' || decimal(trends.tolerance) === null ||
    trends.interpretation !== 'descriptive_only_no_clinical_significance_or_response_class' || !Array.isArray(trends.series) || trends.series.length > 100) return false;
  const points = new Map(timeline.items.map(p => [p.id, p]));
  const geometry = timeline.items.filter(p => ['baseline_reference', 'mask_realized'].includes(p.measurement_basis));
  const baseline = geometry[0];
  if (points.size !== timeline.items.length || geometry.length !== 4 || baseline?.measurement_basis !== 'baseline_reference' ||
    !baseline.historical_context || decimal(day(baseline)) !== '0' || baseline.geometry_result_id !== null ||
    !UUID.test(baseline.patient_id) || !UUID.test(baseline.lesion_id ?? '') ||
    !equal(Object.keys(meshes).sort(), geometry.map(p => p.id).sort()) || !equal(Object.keys(meshBindings).sort(), Object.keys(meshes).sort())) return false;
  const features = timeline.features;
  if (!onlyKeys(features, 'version scope series selected_point_ids unresolved_point_ids treatment_point_ids') || features.version !== 'temporal-features/1' || !equal(features.scope, scope) ||
    !equal(features.selected_point_ids, timeline.items.map(p => p.id)) || !Array.isArray(features.series) || features.series.length > 100 ||
    ![features.unresolved_point_ids, features.treatment_point_ids].every(values => ids(values) && values.every(id => points.has(id)))) return false;
  for (const series of features.series) {
    if (!onlyKeys(series, 'concept unit method_version metric_definition lesion_id instrument instrument_version time_partition ordered_point_ids interval_days usable_count missing_count censored_count conflict_point_ids latest_available_id age_days interval_semantics') ||
      ![series.ordered_point_ids, series.conflict_point_ids].every(values => ids(values) && values.every(id => points.has(id))) ||
      series.latest_available_id !== null && !points.has(series.latest_available_id) || !series.interval_days.every(value => decimal(value) !== null) || !optionalDecimal(series.age_days)) return false;
  }
  for (const point of timeline.items) {
    if (!onlyKeys(point, 'id patient_id time recorded_at revision origin context modality concept numeric_result canonical_unit exact_value metric_definition ordinal_value instrument instrument_version symptom_presence availability missing_reason conflicts source_ids source_hash state_ids geometry_result_id lesion_id measurement_basis method_version summary historical_context branch_id run_id supersedes_id') ||
      !UUID.test(point.id) || point.patient_id !== baseline.patient_id || point.revision !== scope.data_revision || point.origin !== 'SYNTHETIC_GENERATED' || point.context !== 'SYNTHETIC' ||
      point.branch_id !== scope.branch_id || point.run_id !== scope.run_id || !ids(point.source_ids, 1) || !ids(point.state_ids) || !HASH.test(point.source_hash) ||
      !Number.isFinite(Date.parse(point.recorded_at)) || !text(point.method_version) || point.time.reference.basis !== 'relative_day' || point.time.reference.time_domain !== 'simulation' ||
      point.time.reference.timeline_origin_id !== (baseline.time.reference.basis === 'relative_day' ? baseline.time.reference.timeline_origin_id : null) || decimal(day(point)) === null ||
      !UUID.test(point.time.reference.timeline_origin_id ?? '') ||
      !onlyKeys(point.time, 'reference precision date_shift_basis uncertainty_days') || !onlyKeys(point.time.reference, 'basis value time_domain timeline_origin_id anchor_state_id') ||
      point.time.precision !== 'relative_day' || point.time.date_shift_basis !== null || !optionalDecimal(point.time.uncertainty_days) ||
      !validNumeric(point.numeric_result) || !optionalDecimal(point.exact_value) || !optionalDecimal(point.ordinal_value)) return false;
  }
  for (const [index, point] of geometry.entries()) {
    if (point.modality !== 'imaging' || point.concept !== 'numerical_region_volume' || point.metric_definition !== 'numerical_region_volume' || point.lesion_id !== baseline.lesion_id ||
      point.availability !== 'available' || point.missing_reason !== null || point.conflicts.length || !ids(point.state_ids, 1) || decimal(point.exact_value) === null ||
      point.numeric_result?.form !== 'exact' || point.numeric_result.quantity.unit !== 'mm3' ||
      index > 0 && (point.measurement_basis !== 'mask_realized' || !UUID.test(point.geometry_result_id ?? '') || Number(day(point)) <= Number(day(geometry[index - 1])))) return false;
    const binding = meshBindings[point.id], surface = meshes[point.id];
    if (!onlyKeys(binding, 'point_id patient_id branch_id run_id state_ids geometry_result_id surface_sha256') ||
      binding.point_id !== point.id || binding.patient_id !== point.patient_id || binding.branch_id !== point.branch_id || binding.run_id !== point.run_id ||
      !equal(binding.state_ids, point.state_ids) || binding.geometry_result_id !== point.geometry_result_id || !validSurface(surface) || surfaceDigest(surface) !== binding.surface_sha256) return false;
  }
  const volumeSeries = trends.series.filter(s => s.metric_definition === 'numerical_region_volume');
  if (volumeSeries.length !== 1 || !equal(volumeSeries[0].points.map(p => p.point_id), geometry.map(p => p.id))) return false;
  for (const series of trends.series) {
    if (!onlyKeys(series, 'key concept metric_definition unit lesion_id method_version origin context instrument instrument_version points segments endpoint usable_count description') ||
      series.origin !== 'SYNTHETIC_GENERATED' || series.context !== 'SYNTHETIC' || !Array.isArray(series.points) || series.points.length > 100 || new Set(series.points.map(p => p.point_id)).size !== series.points.length ||
      !Array.isArray(series.segments) || series.segments.length !== Math.max(0, series.points.length - 1) || !validComparison(series.endpoint, points)) return false;
    for (const item of series.points) {
      const point = points.get(item.point_id);
      if (!point || !onlyKeys(item, 'point_id x_elapsed_days y exact_value label qualifier censored_threshold reason_codes time source_ids origin context') ||
        item.origin !== point.origin || item.context !== point.context || !equal(item.time, point.time) || !equal(item.source_ids, point.source_ids) ||
        series.concept !== point.concept || series.metric_definition !== point.metric_definition || series.method_version !== point.method_version || series.lesion_id !== point.lesion_id ||
        ![item.x_elapsed_days, item.y, item.exact_value, item.censored_threshold].every(optionalDecimal)) return false;
      if (series.metric_definition === 'numerical_region_volume' && (series.unit !== 'mm3' || !sameDecimal(item.x_elapsed_days, day(point)) ||
        !sameDecimal(item.exact_value, point.exact_value) || point.numeric_result?.form !== 'exact' || !sameDecimal(item.y, point.numeric_result.quantity.value) || item.reason_codes.length)) return false;
    }
    for (const [index, comparison] of series.segments.entries()) {
      if (!validComparison(comparison, points) || comparison.left_point_id !== series.points[index].point_id || comparison.right_point_id !== series.points[index + 1].point_id) return false;
    }
  }
  return validComparison(trends.comparison, points);
}
