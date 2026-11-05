# COS-E2E-002 reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: demo-case-provisioning against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-E2E-002.json](COS-E2E-002.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: COS-E2E-002 reference context.
Agent guidance: COS-000 sections 3–8/11; repository instructions sections 2–8;
COS-REF-001 sections 2–3/15–23; COS-HACK-001 sections 2–3/9/11/17.

## Source Learning Record and Three-Source Decision Note

Map source IDs are retrieved pointers only. Academic text, upstream interfaces and
empirical papers are NOT claimed read or reproduced by this refresh. Append actual
source learning, pinned interface inspection and empirical scope below before
enabling consequential scientific or security behavior. Medical reading exemptions
must be justified for the actual task; this refresh grants no exemption.
Missing academic/repository/empirical categories remain unverified for future domain
enablement. No weights, datasets or upstream code are adopted by a lookup.

Decision: preserve scoped specifications and keep unsupported capabilities disabled.
Verification: task-specific evidence and ledger, not map
existence. Failure fallback: disable affected domain/provider capability. Map drift
is recorded separately; original maps are unchanged.

## Hackathon Compliance Impact

Applies to preservation, source privacy and truthful contribution records. No external
model request is authorized by this task record. Models/rules/access remain unverified.
Architecture is preserved; refer to the task ledger for changed files and actual checks.

## Implementation status (2026-11-03)

Changed product code: 5 components to `useSearchParams()`+`Suspense`
(`lesion-viewer`, `state-timeline-explorer`, `clinical-charts-explorer`,
`insights-explorer`, `case-workspace`) + `case-library` unused-helper removal;
home-page copy directing first-time presenters to the guided demo. No
specification, map, contract, auth-rule, or ingestion-limit change. No secrets
committed (fixture bundles stay in git-ignored `.local/`; credential never
printed).

New/updated tests: `e2e-continuous-journey.spec.ts` (PASS),
`phase3-timeline.spec.ts` timeout/keyboard robustness (PASS),
`mesh-preview.spec.ts` re-PASS, E2E-001 probes re-PASS, 5 component test files
updated to the `useSearchParams` mock pattern (17/17 green with app-shell).

Evidence: `E2E-002-READINESS.md` (verdict READY_WITH_RESTRICTIONS),
`E2E-002-DEMO-CASE.md` + `E2E-002-case-ISPY1_1001.json`, `E2E-002-PROVIDER-REPORT.md`
(BLOCKED, three gates), `E2E-002-DEFECTS.md` (D5/D6 fixed, D7 documented),
journey/route screenshots + summaries, refreshed mesh/phase3 evidence.

Blocked (explicit, not passes): live Meta inference (no policy, no verified
adapter, no owner approval); authentic-baseline display (rights + technical
ineligibility, synthetic channel labeled); genuine longitudinal D02;
production/judge-walkthrough gates per COS-AUDIT-002.
