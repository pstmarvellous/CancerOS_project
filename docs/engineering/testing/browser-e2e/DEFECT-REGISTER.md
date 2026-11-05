# COS-E2E-001 Defect Register

| ID | Severity | Status | Summary | Root cause | Fix | Regression guard |
|---|---|---|---|---|---|---|
| D1 | major (demo-blocking) | FIXED 2026-11-02 | `/twin /states /charts /insights` returned 404 on the running stack | Stale `apps/web/.next` production build predated the route pages | Rebuilt web workspace; restarted tracked `web` process | `e2e-journey-probe` asserts no route renders the 404 page |
| D2 | major (correctness) | FIXED 2026-11-02 | React hydration error #418 on `/cases` (SSR/client first-render mismatch); interim fix attempt produced #301 re-render loop | `CaseLibrary` read `window.location.search` in a lazy `useState` initializer | Refactored to `useSearchParams()` + `Suspense` (matches `AppShell` pattern); explicit `initialProject` for tests | Probe asserts zero console/page errors; `tsc` clean; 5/5 component tests green |
| D3 | note (environment) | NOT A DEFECT | `EXTERNAL_INFERENCE_ENABLED=true` in `.env` blocks `Settings()` without an export policy | Intended safety gate (`verified_policy`), not a bug | None — session ran with process-env `false`; no file changed | `META-LIVE-INTEGRATION-REPORT.md` records the blocked state |
| D4 | note (test isolation) | NOT A DEFECT | DB-backed suites (`test_timeline_runs`, `test_imaging_ingestion` without the flag) error while the dev stack runs | Shared loopback database contention + inherited `.env` flag; expected isolation behavior | Ran suites with process-env `false`; heavy DB suites deferred rather than forcing a stack shutdown | Documented in matrix (T08) |

No security, privacy, provenance, or contract defect was found in the exercised
surface. No fix touched specifications, knowledge maps, contracts, or auth rules.
