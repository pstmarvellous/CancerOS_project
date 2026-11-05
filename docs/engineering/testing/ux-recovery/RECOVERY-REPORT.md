# COS-UX-RECOVERY-001 recovery report

Date: 2026-11-05. Scope: local synthetic demonstration and frontend workflow;
no external transmission, deployment, publication or scientific validation.

## Result and entry workflow

The homepage explains CancerOS and offers **Launch Digital Twin Demo** and
**Explore Research Cases**. The launch opens `/demo` and automatically creates a
read-only HttpOnly session. No project/patient/mesh UUID or API token is requested.
Navigation offers Overview, 3D Digital Twin, Hypothetical Scenarios, Clinical Data,
AI Research Insights and Evaluation / Technical Details. URL selection restores
scenario, state and section; camera actions remain transient.

The approved adapter materializes only synthetic data through the existing local
fixture/domain pipeline. It does not relax backend readers or retain the fixture's
administrator JWT. The ignored `.local/synthetic-demo.json` contains embedded
validated meshes and typed backend timeline/trend reports. Source-registry origins
are checked before preparation. Runtime has no backend request or credential.
Explicit `CANCEROS_SYNTHETIC_DEMO=1` opt-in, seven-day bundle expiry, two-hour
fingerprint-bound sessions, same-origin launch, strict cookies, no-store responses
and bounded geometry validation restrict this adapter to the prepared demo.

Operator commands after local data services are available:

```powershell
npm run demo:prepare
npm run build
npm run demo
```

`npm run demo` sets the opt-in only for its loopback web process. The data preparation
process explicitly disables external inference and rejects optimized Python, because
reused fixtures enforce some invariants with assertions. The SQL fixture transaction
rolls back. Generated private object-store blobs are retained; rollback does not
claim deletion of their bytes. No existing development API is replaced.

## Components reused

- Existing Three.js `MeshRenderer` and OrbitControls, including camera buttons,
  physical coordinates, selected annotation, graphics-loss handler and disposal.
- `TimelinePoint`, `TimelinePage`, `TrendReport`, `pointValue` and `TrendView`.
- Existing synthetic source/imaging fixture, `setup_simulation_baseline`, scenario
  `freeze`, `complete_run`, `publish_completion`, `query_timeline`, `query_trends`,
  `read_generated_mesh`, `reconstruct` and `validate_surface`.
- Existing app shell, case library, evaluation report, API diagnostics, design tokens
  and generated contracts. No new dependency or design system.

The renderer frames all four meshes together and displays only the selected one,
preserving physical camera scale during timeline navigation. Charts plot returned
backend values; the browser computes display positions only. Clinical observations
retain their own times rather than being silently carried forward to a selected day.

## Files changed for this task

| Area | Files |
| --- | --- |
| Entry and shared layout | `apps/web/app/page.tsx`, `app/cases/page.tsx`, `app/evaluation/page.tsx`, `app/layout.tsx`, `app/globals.css` |
| Demonstration | `apps/web/app/demo/page.tsx`, `components/demo-workspace.tsx`, `components/demo-workspace.module.css` |
| Reused shell/viewer | `apps/web/components/app-shell.tsx`, `components/mesh-renderer.tsx` |
| Adapter | `apps/web/app/api/demo-session/route.ts`, `app/api/demo/route.ts`, `lib/demo-contracts.ts`, `lib/synthetic-demo.ts`; removed the unfinished `app/api/demo/proxy.ts` |
| Local operation | `scripts/prepare_synthetic_demo.py`, `scripts/serve_synthetic_demo.mjs`, `package.json` |
| Verification | `apps/web/components/app-shell.test.tsx`, `apps/web/lib/synthetic-demo.test.tsx`, `tests/browser/ux-recovery.spec.ts`, `tests/browser/shell.spec.ts`, `tests/browser/mesh-preview.spec.ts` |
| Task evidence | This directory, `docs/engineering/reference-reviews/COS-UX-RECOVERY-001.{md,json}`, task ledger/checkpoint and compact hackathon contribution record |

Paths abbreviated after their first `apps/web/` entry remain under `apps/web/`.
Other pre-existing uncommitted source/evidence changes were preserved. FastAPI,
database, scientific algorithms, source PDFs/maps and generated clients have no
contract change from this task.

## Verification results

The complete browser journey and security checks passed on the final production
build. Seven screenshots were captured and visually inspected, including the
actual 3D mesh, selected follow-up, timeline, clinical observations and mobile view.
There are no remaining blockers to this local synthetic demonstration.

Completed already:

- `uv run python scripts/prepare_synthetic_demo.py`: five complete families,
  each with the shared 216 mm³ baseline and three measured follow-ups.
- `npm run build`: final production build, TypeScript and page generation passed.
- `npm run typecheck`: passed.
- `npm run lint`: passed.
- `npx vitest run --pool=threads --maxWorkers=1 --testTimeout=30000`:
  **77 tests passed across 18 files**, with no unhandled error.
- `npx playwright test tests/browser/ux-recovery.spec.ts tests/browser/shell.spec.ts --reporter=line`:
  **3 tests passed** on the final full workflow and screenshot capture (42.2 seconds).
- `uv run ruff check scripts/prepare_synthetic_demo.py`: passed after import ordering fix.
- `EXTERNAL_INFERENCE_ENABLED=false; uv run python scripts/check_contract_drift.py`:
  passed runtime OpenAPI/schema/generated-client drift checks.

The first Vitest run returned 69 passes and five failures: four five-second
timeouts while fixture generation/build ran concurrently, plus a duplicate Overview
link in the shell. Case navigation was restricted to case screens, and the suite
was rerun serially with a 30-second timeout. The first browser run found NextURL
canonicalizing loopback addresses and rejecting a valid origin. The launch check
was corrected to use the original Host header; cross-origin rejection is retained.
Two browser attempts also found overly exact test locators (timeline button text
and nested select labels). The locators were corrected without bypassing the
interactions. A serial fork-pool rerun passed 65 tests but hit a worker-startup
timeout; an experimental VM-pool run was incompatible with the installed Next/SWC
module packaging. The final standard thread-pool run passed all 77 tests. The host
had approximately 23 MB free memory during the failed worker attempts. None of
these failed or incomplete attempts is reported as a pass.

## Actual browser interactions and screenshots

Fresh Chromium context with cleared cookies and no project selection. Opened the
homepage and launched using its primary action; no identifier/token fields were
required. Verified actual WebGL render, Rotate left, Pan right, Zoom in, Reset view
and pointer drag. Selected two follow-up states, compared backend volume and exact
mesh bounds, refreshed, used browser Back, switched through all five scenario
families and opened their first measured follow-up. Opened Clinical Data, the
volume chart, AI Research Insights and the scenario cards. At 390 CSS pixels,
checked absence of page overflow. Triggered actual WebGL context loss using
`WEBGL_lose_context`, verified retained measurements and successfully retried.
Browser console/page errors: **none**. Runtime backend requests: **none**.

API checks executed in the browser test runner: missing session denied; cross-origin
launch denied; same-origin launch allowed with strict HttpOnly cookie; unexpected
scenario and project override denied; mutation method rejected; response no-store;
no credential, linkage mapping, private object key or remote asset URL in payload.
Unit checks also cover opt-in disabled, expired/forged/hash-mismatched sessions,
expired bundles, real-origin records, missing states and non-finite geometry.

Screenshots are captured from the functioning app, with no hidden forms or mocked
network responses. The final capture set and machine-readable assertions live in
this directory. See `browser-evidence.json` for the actual run timestamp and scope.

| Screenshot | What it shows |
| --- | --- |
| [Homepage](01-home.png) | Purpose, primary launch and secondary case action |
| [3D baseline](02-twin-baseline.png) | Actual 216 mm³ synthetic region, controls, timeline and volume chart |
| [Selected follow-up](02b-twin-followup.png) | Actual 64 mm³ follow-up at the shared physical camera scale |
| [Scenario and timeline](03-scenario-timeline.png) | Another selected family and synchronized state |
| [Clinical observations](04-clinical.png) | Backend-generated observations, actual relative times and missing real facts |
| [Research insights](05-insights.png) | Explicit local-template and unavailable-live-Meta status |
| [Narrow-screen workspace](06-mobile.png) | Actual renderer, usable navigation and scrollable readable chart |

## Synthetic data and unavailable capabilities

Every baseline, descendant mesh, clinical observation and scenario in this demo is
synthetic. The shared baseline is the existing 24³ artificial grid with a 6³ cube
region, not authentic patient anatomy. There is no patient-specific breast context,
authentic MRI rendering, reviewed tumor contour or real longitudinal clinical proof.
Pathology/receptor values and authentic notes remain unrecorded.

AI Research Insights is explicitly a local descriptive template using the selected
backend measurement. It is neither a live nor saved Meta model result. No provider
API is called and no source data leave the local demonstration. Source permissions,
provider access, qualified scientific review, real-data evaluation and publication
approval remain separate open dependencies. No treatment or diagnostic capability
is introduced. This task does not close D01–D06.

## Hackathon Compliance Impact

The directive applies to a functioning, truthful demonstration and clear reuse
attribution. Existing CancerOS engines and the pinned Three.js renderer are reused;
the new work is their scoped demo adapter and guided frontend integration. No Meta
model was invoked, and competition/model eligibility was not reverified. Substantive
live Meta use remains unavailable in this demo. Architecture and backend contracts
are unchanged. The checks above establish local engineering behavior only; they do
not certify competition compliance, medical validity or release readiness. Nothing
was pushed, submitted or published.

Subsequent implementation: [COS-UX-RECOVERY-002 integrity checks and refreshed
browser evidence](INTEGRITY-CONTINUATION.md). The counts above describe the original
recovery run; the continuation records its own current results.
