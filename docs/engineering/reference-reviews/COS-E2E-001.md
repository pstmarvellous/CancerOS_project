# COS-E2E-001 reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: browser-e2e, longitudinal-simulation against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-E2E-001.json](COS-E2E-001.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: COS-E2E-001 reference context.
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

## Implementation status (2026-11-02)

Changed files: `apps/web/components/case-library.tsx` (hydration fix),
`tests/browser/e2e-journey-probe.spec.ts` + `e2e-negative-probe.spec.ts` (new),
`docs/engineering/testing/browser-e2e/` (7 evidence artifacts).
No specification, map, contract, or auth-rule change. No secrets committed
(`.env`/`.local` ignored; credential never printed).

Checks actually performed: `dev.py start foundation/shell` (services + health
200s); 3 Playwright specs green on the live stack; `test_imaging_ingestion` +
`test_mask_alignment` + `test_physical_measurements` 29 passed;
`test_simulation_contracts` 32 passed; `test_contracts` 15 passed;
`check_boundaries` + `check_contract_drift` pass; `tsc --noEmit` clean;
`case-library` + `app-shell` component tests 5/5 green.

Blocked/not-run (explicit, not passes): live Meta inference (export-policy
gate); mesh/simulation/timeline browser specs (disposable-fixture port
conflict); DB-backed timeline suites (dev-stack contention); full seeded-case
journey (no curated baseline exists). Verdict: READY_WITH_RESTRICTIONS —
see `docs/engineering/testing/browser-e2e/DEMO-READINESS.md`.
