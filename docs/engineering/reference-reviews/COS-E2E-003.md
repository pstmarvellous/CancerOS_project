# COS-E2E-003 reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: meta-provider-integration against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-E2E-003.json](COS-E2E-003.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: COS-E2E-003 reference context.
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

## Implementation status (2026-11-04, E2E-003)

Changed product code: completed fail-closed `GroundingValidator.validate`
(`src/canceros/grounding_runs.py`); nothing else in `src/` touched. New tests:
`tests/test_grounding_validator.py` (6/6). New scripts: `plan_synthetic_live_test.py`,
`run_authorized_live_test.py` (fail-closed runner, exit-6 refusal verified),
`build_synthetic_smoke_input.py`. Private drafts (git-ignored `.local/`):
`E2E-003-owner-authorization-DRAFT.md`, `E2E-003-source-rights-DRAFT.md`,
`e2e-003-synthetic-input.json`. Evidence:
`docs/engineering/testing/browser-e2e/E2E-003-{COMPLETION,ITEM-10,READINESS}.md`.
Official Meta docs verified request/response schemas (models, Responses,
structured-output pages fetched 2026-11-04).

Checks actually performed: provider/export/grounding/interpretation suites
(72+74+88+18 across runs), validator units 6/6, frontend 4/4, hygiene +
boundaries PASS, anonymous TLS reachability only (HTTP 401, no credentials).
No live authenticated request executed; no browser live-result test added
(nothing live to display). Verdict: READY_WITH_RESTRICTIONS, live integration
BLOCKED correctly — see `E2E-003-READINESS.md` and `E2E-003-ITEM-10.md`.
