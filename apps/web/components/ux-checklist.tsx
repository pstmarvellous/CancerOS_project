'use client';

import { useState } from 'react';

type UxCheck = { id: string; label: string; result: string; evidence: string };

const CHECKS: UxCheck[] = [
  { id: 'UX-01', label: 'Case, context, time and origin visible', result: 'Pass (fixture)', evidence: 'Header/selection labels and provenance badges across Phase 5 routes; component tests.' },
  { id: 'UX-02', label: 'One clear primary action per region', result: 'Pass (fixture)', evidence: 'Task regions expose a single labeled action; blocked states name the next action.' },
  { id: 'UX-03', label: 'Non-color-only provenance', result: 'Pass (fixture)', evidence: 'ProvenanceBadge pairs symbol and text label for every origin.' },
  { id: 'UX-04', label: 'Keyboard and screen-reader flow', result: 'Manual check required', evidence: 'Semantic landmarks, labeled controls, table alternatives; no recorded assistive-technology session.' },
  { id: 'UX-05', label: 'Focus visibility and return', result: 'Manual check required', evidence: 'Skip link and dialog Escape patterns present; focus-return session not recorded.' },
  { id: 'UX-06', label: 'Polite announcements', result: 'Pass (fixture)', evidence: 'role=status live regions for loading, ready and failure messages.' },
  { id: 'UX-07', label: 'Reduced motion', result: 'Manual check required', evidence: 'No auto-rotation or autoplay; prefers-reduced-motion audit not recorded.' },
  { id: 'UX-08', label: 'Touch targets and 200%/320px reflow', result: 'Manual check required', evidence: 'Rail/main/inspector and stacked layouts styled; device and zoom session not recorded.' },
  { id: 'UX-09', label: 'Contrast 4.5:1 / 3:1 essentials', result: 'Manual check required', evidence: 'Dark neutral palette; measured contrast audit not recorded.' },
  { id: 'UX-10', label: 'Failure states name recovery', result: 'Pass (fixture)', evidence: '401/403/404/409/expired/stale/withdrawn messages name what remains usable.' },
  { id: 'UX-11', label: 'No patient data in storage', result: 'Pass (fixture)', evidence: 'Selection lives in URL; tokens and records stay in memory; storage assertion in shell tests.' },
  { id: 'UX-12', label: 'Loading artwork never mimics tumor', result: 'Pass (fixture)', evidence: 'Text loaders only; no geometry-shaped placeholders.' },
  { id: 'UX-13', label: 'Sensitive actions confirm', result: 'Pass (fixture)', evidence: 'Retraction uses explicit window.confirm with retained history.' },
  { id: 'UX-14', label: 'Disclosure of hypothetical content', result: 'Pass (fixture)', evidence: 'Simulated labels in branches, viewport, quantities and timeline.' },
  { id: 'UX-15', label: 'Table alternatives to plots', result: 'Pass (fixture)', evidence: 'Every chart ships an exact-value table with parity assertions.' },
  { id: 'UX-16', label: 'No invented confidence', result: 'Pass (fixture)', evidence: 'Unknown uncertainty is text, never a gauge; censored values keep markers.' },
  { id: 'UX-17', label: 'Durable outcomes in panels', result: 'Pass (fixture)', evidence: 'Jobs, publications and saves render in panels and activity, not toasts alone.' },
  { id: 'UX-18', label: 'Measured performance and trials', result: 'Not measured', evidence: 'p95/mesh/frame targets and 30-warm/5-cold trials not run; hardware limits unrecorded.' },
];

export function UxChecklist() {
  const [filter, setFilter] = useState('all');
  const rows = CHECKS.filter(check => filter === 'all' || (filter === 'manual' ? check.result.startsWith('Manual') || check.result === 'Not measured' : check.result.startsWith('Pass')));
  return (
    <section aria-label="UX acceptance evidence">
      <h2>UX-01–UX-18 acceptance evidence</h2>
      <p>Targeting WCAG 2.2 AA without claiming conformance from an automated scan. Screenshots alone cannot pass interaction, performance or usability tests.</p>
      <p>
        <label htmlFor="ux-filter">Show </label>
        <select id="ux-filter" value={filter} onChange={event => setFilter(event.target.value)}>
          <option value="all">All checks</option>
          <option value="passing">Passing fixture checks</option>
          <option value="manual">Manual or unmeasured checks</option>
        </select>
      </p>
      <div style={{ overflowX: 'auto' }}>
        <table>
          <caption>Executable and manual UX evidence per check</caption>
          <thead>
            <tr>
              <th scope="col">Check</th>
              <th scope="col">Result</th>
              <th scope="col">Evidence origin</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(check => (
              <tr key={check.id}>
                <th scope="row">{check.id} · {check.label}</th>
                <td>{check.result}</td>
                <td>{check.evidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
