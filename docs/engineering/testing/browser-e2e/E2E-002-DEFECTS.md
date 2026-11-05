# COS-E2E-002 Defect Register (delta from E2E-001)

E2E-001 D1 (stale build 404s) and D2 (case-library hydration #418) remain fixed;
their regression probes (`e2e-journey-probe`, `e2e-negative-probe`) pass on the
final build.

## New

| ID | Severity | Status | Summary | Root cause | Fix | Guard |
|---|---|---|---|---|---|---|
| D5 | major (pattern) | FIXED 2026-11-03 | Same SSR/client query-read hydration bug (#418) in 5 more components: `lesion-viewer`, `state-timeline-explorer`, `clinical-charts-explorer`, `insights-explorer`, `case-workspace` | `useState(() => read window.location.search)` evaluated during SSR as null-state but as query-state on first client render | Same D2 pattern: `useSearchParams()` + `Suspense`, explicit initial props; tests switched from `window.location` mocking to `useSearchParams` mock (established `app-shell.test` pattern) | `e2e-continuous-journey` asserts zero unexpected console errors; 17/17 component tests green; `tsc` clean |
| D6 | minor (test-only) | FIXED 2026-11-03 | `phase3-timeline.spec` and journey probes flaky/timing-out on loaded laptop (5s expects, 30s test timeout, 45-min fixture JWT expiry) | Engineering timeouts, not app behavior (proven by in-page fetch spy: both API calls 200, "Branch loaded.") | `test.slow()`, 90s expects on load steps, keyboard submit for the load button, fresh fixture per run | Specs pass: phase3 25s, journey 20s on healthy stack |
| D7 | note (environment) | DOCUMENTED | Dev postgres + object store died mid-session (laptop sleep/overload); fixture DB timeouts followed | Ephemeral local processes, no data-loss path (fixture DBs disposable, dev DB transactional) | Restarted full `foundation`; documented in matrix | Health checks in TEST-ENVIRONMENT flow |

## Investigated, not defects

- Real BreastDCEDL bytes cannot be staged as an authentic baseline: staging
  contract payload caps + `bounded-imaging/1` millimeter-units requirement
  (files report `unknown`) + no de-identification/public-demo evidence. The
  provisioning attempt refused to resample or forge; recorded in
  `E2E-002-DEMO-CASE.md`. No contract was widened.
- Fixture JWT expiry (45 min) during long runs: operational, handled by
  refreshing the disposable fixture, never by extending trust.
- Charts/insights 401 without a session token: correct authz behavior;
  journey asserts the honest gated state instead of bypassing it.
