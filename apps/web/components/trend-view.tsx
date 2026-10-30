'use client';

import { useState } from 'react';
import { ProvenanceBadge, TimeLabel } from './research';
import type { components } from '../../../packages/contracts/generated/api';
import styles from './simulation-workflow.module.css';

type S = components['schemas'];
export type ChartPoint = S['TrendChartPoint'];
export type TrendReport = S['TrendReport'];

function coordinate(value: string | null): number | null {if (value === null || value.trim() === '') return null; const number = Number(value); return Number.isFinite(number) ? number : null;}
export function TrendView({report, onSelect}: {report: TrendReport; onSelect: (id: string) => void}) {
  const [selectedKey, setSelectedKey] = useState('');
  const series = report.series.find(item => item.key === selectedKey) ?? report.series[0];
  if (!series) return <section><h2>Descriptive trends</h2><p>No supported series exists in this exact observation window.</p></section>;
  const values = series.points.map(point => ({point, x: coordinate(point.x_elapsed_days), y: coordinate(point.y), threshold: coordinate(point.censored_threshold ?? null)}));
  const plotted = values.filter((item): item is typeof item & {x: number; y: number} => item.x !== null && item.y !== null && item.point.reason_codes.length === 0);
  const censored = values.filter((item): item is typeof item & {x: number; threshold: number} => item.x !== null && item.threshold !== null && ['<', '<=', '>', '>='].includes(item.point.qualifier ?? '') && item.point.reason_codes.every(reason => ['CENSORED_VALUE_NOT_EXACT', 'MISSING_NUMERIC_VALUE'].includes(reason)));
  const knownTimes = values.filter(item => item.x !== null);
  const minX = Math.min(...knownTimes.map(item => item.x!)), maxX = Math.max(...knownTimes.map(item => item.x!));
  const heights = [...plotted.map(item => item.y), ...censored.map(item => item.threshold)];
  const minY = Math.min(...heights), maxY = Math.max(...heights);
  const px = (x: number) => minX === maxX ? 325 : 60 + (x - minX) / (maxX - minX) * 530;
  const py = (y: number) => minY === maxY ? 130 : 210 - (y - minY) / (maxY - minY) * 160;
  const canPlot = heights.length > 0 && [minX, maxX, minY, maxY, maxX - minX, maxY - minY].every(Number.isFinite);
  const isOrdinal = !!series.instrument;
  const endpoint = series.endpoint;
  return <section aria-label="Descriptive observation trends"><h2>Descriptive trends</h2><p>Version {report.version} · numeric tolerance {report.tolerance}. These are deterministic descriptions of returned observations; they do not assign clinical response or treatment benefit.</p>
    <label>Trend metric and source context<select value={series.key} onChange={event => setSelectedKey(event.target.value)}>{report.series.map(item => <option key={item.key} value={item.key}>{item.concept} · {item.metric_definition ?? 'source measure'} · {item.unit ?? item.instrument ?? 'no numeric unit'} · {item.origin} · {item.context} · lesion {item.lesion_id ?? 'unlinked'}</option>)}</select></label>
    <p><ProvenanceBadge origin={series.origin}/> · {series.context} · {series.concept} · {series.unit ?? 'No ratio unit'} · {series.metric_definition ?? 'No imaging metric definition'}. Method: {series.method_version}.</p>
    <p>{series.description}</p><p>Usable point count: {series.usable_count}. Method: later minus earlier divided by actual elapsed days.</p>
    {endpoint ? <><p>{endpoint.description}</p><p>Endpoint comparison: {endpoint.status}. {endpoint.reason_codes.join(' · ')}</p></> : <p>Endpoint comparison unavailable: fewer than two usable observations.</p>}
    {isOrdinal ? <p>Ordinal instrument: {series.instrument}/{series.instrument_version}. Direction and ordered ratings are descriptive; percentage change and numerical slopes are unavailable.</p> : <dl><dt>Absolute change</dt><dd>{endpoint?.exact_absolute_change ?? endpoint?.absolute_change ?? 'Unavailable'} {series.unit}</dd><dt>Percentage change</dt><dd>{endpoint?.percentage_change == null ? 'Unavailable' : `${endpoint.percentage_change}%`}</dd><dt>Elapsed interval</dt><dd>{endpoint?.elapsed_days ?? 'Unavailable'} days</dd><dt>Endpoint slope</dt><dd>{endpoint?.exact_slope_per_day ?? endpoint?.slope_per_day ?? 'Unavailable'} {series.unit}/day</dd></dl>}
    {canPlot ? <figure><svg viewBox="0 0 650 270" role="img" aria-label={`${series.concept} observations on elapsed-time axis; exact values and missing gaps in table below`} style={{width: '100%', maxWidth: 850}}>
      <line x1="60" y1="210" x2="600" y2="210" stroke="currentColor"/><line x1="60" y1="40" x2="60" y2="210" stroke="currentColor"/>
      <text x="320" y="258" textAnchor="middle">Elapsed days from server-defined anchor</text><text x="60" y="25">{series.unit ?? `${series.instrument}/${series.instrument_version}`}</text>
      {values.map((item, index) => {const next = values[index + 1]; const comparison = series.segments[index]; const good = (value: typeof item) => value.x !== null && value.y !== null && (!value.point.reason_codes || value.point.reason_codes.length === 0); return next && good(item) && good(next) && comparison?.status === 'comparable' ? <line key={`line-${item.point.point_id}`} data-testid="trend-guide" x1={px(item.x!)} y1={py(item.y!)} x2={px(next.x!)} y2={py(next.y!)} stroke="#6d28d9" strokeDasharray="4 4"/> : null;})}
      {plotted.map(item => <circle key={item.point.point_id} cx={px(item.x)} cy={py(item.y)} r="5" fill="#5b21b6"><title>{item.point.label} · elapsed {item.point.x_elapsed_days} days</title></circle>)}
      {censored.map(item => {const x = px(item.x), y = py(item.threshold), direction = item.point.qualifier!.startsWith('<') ? 1 : -1; return <g key={item.point.point_id} data-testid="censored-marker"><title>{item.point.label} · elapsed {item.point.x_elapsed_days} days</title><circle cx={x} cy={y} r="5" fill="none" stroke="#5b21b6"/><path d={`M ${x} ${y} v ${direction * 16} m -4 ${-direction * 5} l 4 ${direction * 5} l 4 ${-direction * 5}`} fill="none" stroke="#5b21b6"/></g>;})}
      <text x="60" y="232">{knownTimes.find(item => item.x === minX)?.point.x_elapsed_days}</text><text x="590" y="232" textAnchor="end">{knownTimes.find(item => item.x === maxX)?.point.x_elapsed_days}</text>
      <text x="55" y="45" textAnchor="end">{maxY}</text><text x="55" y="207" textAnchor="end">{minY}</text>
    </svg><figcaption>Filled points are exact returned observations; open circles with arrows show censoring thresholds and the bound direction, never exact values. Dashed segments are visual guides between eligible adjacent points, not interpolated observations. Missing, censored, conflicting and unresolved points break the guides. Coordinates are display approximations; use the exact-value table below.</figcaption></figure> : <p>No finite compatible coordinates are available for plotting. Use the observation table and comparison reasons.</p>}
    <div className={styles.table}><table><caption>Exact observations and gaps · {series.concept}</caption><thead><tr><th>Underlying point</th><th>Observation time</th><th>Elapsed days</th><th>Exact label / qualifier</th><th>Origin / limitations</th></tr></thead><tbody>{series.points.map(point => <tr key={point.point_id}><td><button onClick={() => onSelect(point.point_id)}>Open point {point.point_id.slice(0, 8)}</button></td><td><TimeLabel time={point.time.reference}/></td><td>{point.x_elapsed_days ?? 'Unresolved'}</td><td>{point.label}<p>{point.qualifier}</p>{point.exact_value !== null && <p>Exact value: {point.exact_value}</p>}</td><td><ProvenanceBadge origin={point.origin}/><p>{point.reason_codes?.join(' · ') || 'No additional reason codes'}</p></td></tr>)}</tbody></table></div>
    <details><summary>Adjacent comparison evidence</summary>{series.segments.map((comparison, index) => <p key={index}>{comparison.description} · {comparison.status} · {comparison.reason_codes.join(' · ')}</p>)}</details>
  </section>;
}
