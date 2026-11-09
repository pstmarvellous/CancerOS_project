# Stage Handoff — COS-REC-06 through COS-REC-09

**Date:** 2026-11-09. **Author:** single-session agent (self-review only; no independent reviewer).
**Rule basis:** `docs/remediation_prompts/prompt_11.md` (mandatory stage execution rules).

## Per-stage handoff

| Stage | Prompt | Verdict | Evidence | Handoff state |
|-------|--------|---------|----------|---------------|
| COS-REC-06 | prompt_7 (imaging import + 3D) | verified, authentic gate blocked | 5 component + 4 route tests; 45 backend tests; typecheck/lint/build; workflow panel + `GET /imaging-imports` | Complete. Blocked item (authentic MRI) owned by data-rights, not engineering. |
| COS-REC-07 | prompt_8 (AI interpretation) | verified, live path blocked-closed | 9 tests; 25 backend chain tests; Settings/read_policy probe; Timeline→Insights link; capabilities proxy | Complete. Live enablement needs export authorization + policy (owner). |
| COS-REC-08 | prompt_9 (product design) | verified, manual sessions open | Real-Chromium probe (0 errors/overflow/overlaps, 5 screenshots); 221-test suite; copy swap + 3 test updates | Complete. UX-04/05/07/08/09 + UX-18 remain open per UX checklist. |
| COS-REC-09 | prompt_10 (acceptance) | executed; product NOT YET portfolio-ready | Journeys A/B PASS, C PARTIAL (D-01), D/E partial/blocked; 106 backend tests; auth probes 403/404/403; 16 screenshots | Complete. Open defects D-01 (viewer linkage), D-03 (stale spec), D-04 (deferred browser D/E). Fixed D-02 (viewer session auth) with full-suite re-run. |

## Rule-by-rule compliance

1. **One stage at a time** — each stage began on an explicit user request; no auto-advance occurred.
2. **Read before writing** — reference context (`reference-reviews/COS-REC-0X`) created before changes in every stage; originals unmodified.
3. **Preserved unrelated work** — no reverts of other workstreams; pre-existing findings (grounding_runs import sort, COS-074 ledger transition, ux-recovery copy drift) left untouched and recorded.
4. **Smallest changes** — REC-06: 1 endpoint + panel; REC-07: link + proxy; REC-08: copy + probe; REC-09: acceptance + one session-auth fix required by its own gate.
5. **Real integration** — every stage ran disposable-DB backend suites and/or real-Chromium journeys, never mocks alone.
6. **Browser journeys** — REC-06/07 component-level + REC-08/09 full Chromium journeys with screenshots.
7. **Genuine evidence, failures reported** — journey JSONs record per-step PASS/FAIL; D-01 disclosed with API proof instead of being smoothed over.
8. **Accurate verdicts** — "verified" marks stage execution + reporting, not product perfection; blocked/open items are explicit in each ledger entry. No unverified work was converted to PASS (authentic MRI, live Meta, manual UX, browser D/E all recorded as blocked/open).
9. **Blockers identified** — each with owner, missing evidence, and next action (ledger `remaining_risks` + acceptance backlog D-01…D-04).
10. **Stop + handoff** — this file; no next stage begun; no unrelated refactoring.

## Open threads for the owner (not started)

- D-01: owned lesion→mesh-QC lookup (backend contract decision needed).
- Live Meta enablement: export authorization, versioned policy, account access.
- Authentic-data rights/de-identification/review pipeline.
- Manual UX sessions (UX-04/05/07/08/09), UX-18 measurements, full 8-screen before/after set.
- `ux-recovery.spec.ts` copy drift (owning workstream).

## Evidence index

- `docs/engineering/testing/rec08-usability/` (5 screenshots + probe spec)
- `docs/engineering/testing/rec09-acceptance/` (ACCEPTANCE-REPORT.md, journey JSONs, api-probes.json, 16 screenshots, repro scripts)
- `docs/engineering/reference-reviews/COS-REC-0{6,7,8,9}.md`
- Task ledger COS-REC-06…09 (118 tasks total), each with checks_evidence and remaining_risks.
