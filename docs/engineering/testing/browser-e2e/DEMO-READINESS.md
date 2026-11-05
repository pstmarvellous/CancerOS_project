# COS-E2E-001 Demo Readiness Verdict

## Verdict: READY_WITH_RESTRICTIONS

The achievable hackathon demonstration workflow is reliable **within the
boundaries below**. This is not a release certification and not a clinical
validation claim.

## What the evidence supports (criteria 1–9, 12–14)

- The application launches from documented commands; API + shell health checks
  respond (T01).
- Landing, case-gated navigation, empty/loading/error states, and negative
  paths behave honestly in a real browser with zero console errors and zero
  HTTP 5xx across all 11 routes (T02–T04, T10, T12–T13).
- Authentic single-examination MRI + verified-mask ingestion and physical
  measurement pipelines pass on backend suites against the real demo-file
  geometry (T05; 29 tests).
- Five-scenario simulation contracts hold (T07; 32 tests), with explicit
  hypothetical labeling preserved in the UI.
- Two real defects (stale build 404s; hydration error) were found by browser
  testing, fixed minimally, and guarded by regression tests.

## Restrictions (must be stated in any demo)

1. **No live 3D/simulation/timeline browser run this session** (T06–T08):
   the fixture-based specs need a disposable API/database that conflicts with
   the live dev stack. Backend coverage is green; browser interaction is not
   claimed.
2. **No live Meta inference** (T09–T11 of acceptance): export-policy gate
   correctly enforced; deterministic fallbacks must be labeled as such.
3. **No genuine longitudinal case** (D02): the demo subset contains one
   examination per subject; DCE phases are not follow-up visits. Show
   synthetic follow-ups only, labeled hypothetical.
4. **No seeded demo case in the dev database:** the presenter must use an
   authorized case-creation path or a disposable fixture; the UI will not
   invent one.
5. **Development laptop only:** no performance, device-matrix, or deployment
   claim. Production deployment, restore, and judge-walkthrough gates stay
   open per COS-AUDIT-002.

## Acceptance-criteria scorecard (§19)

| # | Criterion | Status |
|---|---|---|
| 1 | Application launches | PASS |
| 2 | Demo case can be opened | RESTRICTED (needs authorized case; UI gates honestly) |
| 3 | Authentic MRI ingest/select | PASS (backend; browser button-path not run) |
| 4 | Verified segmentation available | PASS (5 paired subjects; backend) |
| 5 | 3D viewer renders | RESTRICTED (component-tested; browser run deferred) |
| 6 | Measurements match backend | PASS (backend; viewer binding unchanged) |
| 7–8 | Scenario runs; five families accessible/explained | PASS contracts / RESTRICTED browser |
| 9 | Timeline/geometry/clinical sync | RESTRICTED (backend contracts; browser deferred) |
| 10–11 | Authorized Meta inference, grounded | BLOCKED (policy gate; correct) |
| 12 | Real vs synthetic distinguishable | PASS (badges + labels verified in UI) |
| 13 | No unresolved critical errors | PASS (D1/D2 fixed; probes green) |
| 14 | Repeatable without DB hand-edits | PASS (fixtures/guided-demo reset semantics; no DB edits made) |
