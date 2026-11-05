# COS-E2E-002 Readiness Report

## Verdict: READY_WITH_RESTRICTIONS

The browser-tested demonstration workflow is working and reproducible within
the restrictions below. This is not a release certification, clinical
validation, or organizer-acceptance claim.

## Browser evidence actually executed (real Chromium, loopback services)

| Flow | Spec | Result |
|---|---|---|
| Shell honesty + keyboard + narrow layout | `shell.spec.ts` | PASS |
| 11 routes render, zero console errors, zero 5xx, honest empty states | `e2e-journey-probe.spec.ts` | PASS |
| Invalid credentials fail safely, no leaks | `e2e-negative-probe.spec.ts` | PASS |
| Real WebGL mesh: rotate/pan/zoom/reset, authoritative 576 mm³, context-loss recovery, auth-denial clears geometry | `mesh-preview.spec.ts` | PASS (`mesh-preview.png`, `mesh-browser-measurement.json`) |
| Saved SC-01 config → eligibility → 3 published follow-ups (64/8/1 mm³, days 37/56/90) → exact state fusion → full-window trends (−99.537037037%) → unauthorized recovery | `phase3-timeline.spec.ts` | PASS (`phase3-timeline.png`, `phase3-browser.json`) |
| Continuous journey: simulation branch → exact timeline (5 items) → charts/insight honest gating, one case context, zero unexpected errors | `e2e-continuous-journey.spec.ts` | PASS (`journey-*.png`, `journey-summary.json`) |

Backend: imaging/measurement 29 + simulation contracts 32 + contracts 15 pass;
`check_boundaries`, `check_contract_drift`, `tsc`, 17/17 component tests, and
lint are green on the final build.

## Restrictions (must be stated in any demo)

1. **Synthetic display channel only.** All rendered 3D/timeline geometry is
   explicitly labeled synthetic engineering fixture; no authentic patient
   anatomy is shown (real-file blockers in `E2E-002-DEMO-CASE.md`).
2. **No live Meta inference.** Three independent gates closed (no policy, no
   verified adapter, no owner approval). Rule-based local summaries only,
   labeled as such — never presented as model output.
3. **No genuine longitudinal case.** D02 stays open; follow-ups are
   hypothetical scenario outputs with distinct provenance labels.
4. **Fixture browser flows need a fresh disposable fixture** (45-min token,
   isolated DB/ports) and are separate from the dev-stack route probes.
5. **Development laptop only.** No performance, device-matrix, deployment, or
   restore claims; judge-walkthrough and production gates stay open per
   COS-AUDIT-002.

## Scorecard (E2E-001 §19 criteria)

1 launch PASS · 2 case open RESTRICTED (authorized session; UI gates honestly)
· 3 MRI ingest PASS backend / synthetic display browser · 4 mask PASS (5 paired
subjects verified offline; synthetic masks rendered) · 5 3D viewer PASS
(synthetic) · 6 measurements PASS (server-authoritative, camera-checked) ·
7–8 scenarios PASS (SC-01 end-to-end in browser; five families in contracts) ·
9 sync PASS (timeline/fusion/trends in browser) · 10–11 Meta BLOCKED (correct)
· 12 provenance PASS (badges + labels verified) · 13 errors PASS (D1/D2/D5/D6
fixed, probes green) · 14 repeatable PASS (idempotent fixtures, no DB edits).

## Changes in E2E-002 (surgical, no redesign)

- 5 components refactored to the E2E-001 D2 pattern (`useSearchParams` +
  `Suspense`); 5 test files updated to mock `useSearchParams`.
- Home-page copy: private previews require authorized session identifiers;
  first-time presenters directed to the guided demo.
- New specs: `e2e-continuous-journey`; extended timeouts/keyboard submit in
  `phase3-timeline`; longer timeouts in E2E-001 probes (load-related only).
- New scripts: `scripts/demo_case_verify.py` (read-only verifier).
- No specification, map, contract, auth-rule, or ingestion-limit change. No
  secrets committed (bundles in git-ignored `.local/`).
