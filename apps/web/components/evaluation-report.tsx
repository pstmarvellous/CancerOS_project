'use client';

import Link from 'next/link';

type Row = { label: string; status: string; detail: string };

const ROWS: Row[] = [
  { label: 'Case library and selection', status: 'Fixture-tested', detail: 'Accurate pagination, search and counts with longitudinal availability; approved real-data operation not run.' },
  { label: 'Overview, sources and completeness', status: 'Fixture-tested', detail: 'Source-backed observation, correction and retraction workflows; no synthetic production fallback.' },
  { label: 'Interactive 3D tumor viewer', status: 'Fixture-tested', detail: 'Authorized geometry with server measurements authoritative; graphics fallback labeled, not release evidence.' },
  { label: 'State timeline and comparison', status: 'Fixture-tested', detail: 'Persisted discrete snapshots with sequential Pin A/B comparison; no browser arithmetic.' },
  { label: 'Clinical charts and tables', status: 'Fixture-tested', detail: 'Bounded history with exact tables; no smoothing, gap fill or mixed-unit axes.' },
  { label: 'Scenario setup and publication', status: 'Fixture-tested', detail: 'Four-step generate, validate and separate private publication; actual history unchanged.' },
  { label: 'Grounded insights and provenance', status: 'Fixture-tested', detail: 'Snapshot-bound context with rule-based labels; private candidates never stream or auto-publish.' },
  { label: 'Measured task and protocol', status: 'Not evaluated', detail: 'No authorized versioned evaluation report is published in this build.' },
  { label: 'Cohort and independent patients', status: 'Not evaluated', detail: 'Real versus synthetic outcomes and independent patient counts are not established here.' },
  { label: 'Pipeline, model and split versions', status: 'Not evaluated', detail: 'Pipeline and model versions, split method and failure accounting are not published in this build.' },
  { label: 'Real-data operation', status: 'Blocked', detail: 'Requires approved data, live provider access and qualified scientific review; owner and evidence pending.' },
  { label: 'Participant review', status: 'Blocked', detail: 'No three-participant interactive sessions run; self-review cannot invent participants or expert signoff.' },
];

export function EvaluationReport() {
  return (
    <div>
      <section aria-label="Evaluation scope">
        <h2>Compact evaluation report</h2>
        <p>
          Passing interface checks do not prove clinical suitability. Missing evidence reads Not evaluated; open
          real-follow-up and review gates remain visible. Synthetic branches are never counted as independent real
          patients.
        </p>
        <div style={{ overflowX: 'auto' }}>
          <table>
            <caption>Implemented, fixture-tested, real-data-verified, participant-reviewed and blocked scope</caption>
            <thead>
              <tr>
                <th scope="col">Capability</th>
                <th scope="col">Evidence status</th>
                <th scope="col">Detail and next action</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map(row => (
                <tr key={row.label}>
                  <th scope="row">{row.label}</th>
                  <td>{row.status}</td>
                  <td>{row.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>No decorative accuracy percentages are shown. Performance targets (warm metadata p95, manifest p95, first mesh, frame rate, mesh budget) remain targets until measured on declared hardware. No percentage sign appears in this report.</p>
      </section>
      <section aria-label="Journey">
        <h2>One coherent journey</h2>
        <p>
          Open case → inspect measured geometry and exact sources → select and compare states → read charts and
          tables → explore a labeled branch → inspect grounded findings → see measured evaluation limits.
        </p>
        <p><Link href="/guided-demo">Follow the guided demo</Link> · <Link href="/cases">Open the case library</Link></p>
      </section>
    </div>
  );
}
