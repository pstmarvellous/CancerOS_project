# COS-E2E-001 E2E Test Matrix

Verdicts: PASS / FAIL / BLOCKED / NOT_RUN / NOT_APPLICABLE.
Evidence: this directory (`route-summary.json`, `route-*.png`) plus cited suites.

| ID | COS-E2E-001 section | Expectation | Result | Evidence |
|---|---|---|---|---|
| T01 | §4 environment | Stack starts on documented commands; health endpoints respond | PASS | `TEST-ENVIRONMENT.md`; `dev.py start foundation/shell` output |
| T02 | §5 browser automation | Real Chromium drives real UI; no mocked browser claims | PASS | 3 Playwright specs green on live stack |
| T03 | §6 scenario A | Landing, auth messaging, project/case selection, empty/loading states | PASS (probe) | `e2e-journey-probe`: 11/11 routes render, gated routes show honest empty states, 0 console errors, 0 HTTP 5xx |
| T04 | §13 negatives | Invalid UUID/token fails safely without leaks | PASS (probe) | `e2e-negative-probe`: access-denied + restricted-project messaging; no page errors; no secret/traceback echo |
| T05 | §7 scenario B | Authentic MRI ingestion → verified mask → measurements | PASS (backend) | `test_imaging_ingestion` + `test_mask_alignment` + `test_physical_measurements`: 29 passed; demo NIfTI geometry verified (§DATASET-INVENTORY) |
| T06 | §8 scenario C | 3D viewer renders, rotates, shows authoritative volumes | NOT_RUN (browser) | Pre-existing `mesh-preview.spec.ts` requires disposable fixture API (`scripts/mesh_browser_fixture.py` refuses while dev API occupies :8000); component/unit coverage exists. Browser run deferred to avoid stopping the dev stack mid-session |
| T07 | §9 scenario D | Five hypothetical families run, synchronize, stay labeled | PASS (contracts) / NOT_RUN (browser) | `test_simulation_contracts`: 32 passed; five-family engine covered in repo suites; browser run needs disposable fixture (`phase3_browser_fixture.py`, same port conflict) |
| T08 | §10 scenario E | Clinical timeline sync, missingness honest | BLOCKED (browser) | Timeline DB suites need isolated test database; dev stack occupies it. `test_simulation_contracts` trend math green; no browser timeline run this session |
| T09 | §11 scenario F | Live Meta inference, grounded, identified, costed | BLOCKED | Export policy gate enforced (`verified_policy` denies without versioned permission evidence). No provider call attempted; credential untouched. See `META-LIVE-INTEGRATION-REPORT.md` |
| T10 | §14 UX/responsive | Narrow viewport, keyboard, focus, overflow | PASS (partial) | `shell.spec.ts` (390px overflow + keyboard) and journey screenshots pass; full matrix (screen reader, touch) NOT_RUN |
| T11 | §6–10 complete journey | Case → MRI → mask → mesh → simulation → charts → insights | BLOCKED | No seeded demo case exists in dev DB (by design: fixtures are honesty gates, `test_demo_cases_synthetic` stays blocked); full journey needs curated baseline + authn, which does not exist |
| T12 | D1 stale build | All routes serve current code | PASS (fixed) | Rebuilt `apps/web`; `/twin /states /charts /insights` now 200 |
| T13 | D2 hydration #418 | No React hydration errors on any route | PASS (fixed) | `case-library.tsx` refactored to `useSearchParams`+`Suspense`; probe asserts zero console errors; `tsc` + 5 component tests green |
