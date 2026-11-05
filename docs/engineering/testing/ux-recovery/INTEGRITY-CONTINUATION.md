# COS-UX-RECOVERY-002 — Prepared demonstration integrity

Verified 2026-11-05 for the local synthetic demonstration. The resumed work closes
an integration gap: the original adapter could accept mixed patient references,
changed volume-chart coordinates and surfaces exchanged between valid state keys.
The prepared bundle now refuses those inconsistencies before a session can use it.

## Changes and reuse

- `apps/web/lib/demo-contracts.ts`: internal bundle version `synthetic-demo/2`
  and explicit point/patient/branch/run/state/result bindings for every mesh.
- `apps/web/lib/demo-integrity.ts`: strict synthetic context, reference, time,
  quantity, chart and surface checks; shared fixed binary SHA-256 digest protocol.
- `apps/web/lib/synthetic-demo.ts`: requires coherent scenario scopes and the same
  observed synthetic baseline across all five families; refuses version 1.
- `scripts/prepare_synthetic_demo.py`: emits version 2 and bindings directly from
  the existing SQL/private-storage measurement, mesh, simulation and timeline engines.
- `apps/web/app/api/demo/route.ts`: rejects duplicate scenario parameters.
- `apps/web/lib/synthetic-demo.test.tsx` and `tests/browser/ux-recovery.spec.ts`:
  corruption regression cases and actual prepared mesh-binding browser assertions.

No backend API, database schema, generated client, scientific measurement algorithm
or authorization policy changed. The homepage, one-click local session, existing
Three.js renderer, scenario controls, timeline and clinical views remain the entry
workflow described in [the original report](RECOVERY-REPORT.md). No manual UUIDs or
API credentials are required. Version 1 bundles require `npm run demo:prepare`.

## Checks actually performed

| Check | Result |
| --- | --- |
| Focused synthetic adapter tests | 39 passed; included in the full suite below |
| `npx vitest run --pool=threads --maxWorkers=1 --testTimeout=30000` | 113 passed across 18 files |
| `npm run typecheck` | Passed after fixture tuple and nullable-origin type corrections |
| Focused ESLint and preparation-script Ruff | Passed |
| `uv run python scripts/prepare_synthetic_demo.py` | Passed after restarting stopped local data services without resetting them |
| `npm run build` | Passed production compilation and route generation |
| `npx playwright test tests/browser/ux-recovery.spec.ts tests/browser/shell.spec.ts --reporter=line` | 3 passed against the final production build |

The first preparation attempt failed with data services stopped; it was not a pass.
The successful preparation used external inference disabled and generated five
scenario families with four bound geometry positions each: one shared artificial
baseline and three generated follow-ups per family. Fixture SQL was rolled back;
generated private object-store blobs remain. The local ignored bundle contains no
API token and expires after seven days.

Chromium executed the fresh-session homepage launch, actual WebGL rendering,
camera buttons, drag, all five scenarios, selected volume and mesh identity/bounds,
reload/back navigation, clinical table/chart, insight-status labeling, narrow-screen
layout, actual graphics-context loss/retry and session/request boundaries. Duplicate
scenario parameters returned 400. There were no browser errors or runtime requests
to the backend on port 8000. See [machine-readable evidence](browser-evidence.json).

All seven screenshots were refreshed by this browser run. The
[selected 64 mm³ follow-up](02b-twin-followup.png) and
[clinical observations](04-clinical.png) were visually inspected in this continuation:
the rendered phantom, selected timeline state, volume chart, observation times and
synthetic labels were visible and coherent. The original report links every view.

## Limits and retained gates

The digest records coherence with a trusted local producer; it is not a signature,
an independent scientific attestation or complete scientific quality control. Exact
backend values are compared without recomputing medical measurements. Unrelated
workspace edits were preserved. Task-local map/source consultation is recorded in
[the reference review](../../reference-reviews/COS-UX-RECOVERY-002.md).

Every geometry and clinical observation is synthetic. The baseline is a geometric
cube phantom, not authentic anatomy. Insights remain a labeled local template;
live Meta is unavailable. Authentic-source rights, qualified scientific review,
longitudinal evaluation, provider access and publication gates remain open. No
patient-source transmission, provider inference, commit, push or deployment occurred.
The demo remains available locally at http://127.0.0.1:3000 via `npm run demo`.

## Hackathon compliance impact

This continues the existing application and engine reuse with traceable engineering
checks. No model, dataset, upstream code or dependency was newly adopted. No event
eligibility, live Meta use, clinical validity or release-readiness claim is made.
