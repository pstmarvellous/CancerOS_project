# E2E-003 — completion evidence (final report: see `E2E-003-READINESS.md`)

## 1. Files changed

- `src/canceros/grounding_runs.py` — completed the real fail-closed
  `GroundingValidator.validate(result, context)`: snapshot-hash match,
  reference/numeric fidelity via `validate_private_candidate`, prohibited-claim
  and unresolved-reference rejection, unsupported-metric abstention. Returns the
  `GroundingReport` on success; raises `FAILED_GROUNDING` otherwise. No
  network, no secrets, no candidate-prose logging.
- `tests/test_grounding_validator.py` — NEW: 6 synthetic-context unit checks
  (version pin, pass-through, snapshot mismatch, unresolved reference,
  prohibited claim, empty candidate).
- `scripts/plan_synthetic_live_test.py` — NEW: bounded test-plan generator.
  Reads `.env` key NAMES only, builds the approved synthetic input, prints the
  plan with real byte/hash counts, exits 3 with `live_call_authorized: false`.
- `scripts/run_authorized_live_test.py` — NEW: fail-closed live runner. Refuses
  (exit 6, zero transmission) unless nine owner-confirmed policy inputs arrive
  via process environment; builds the export/2 policy with REAL evidence-file
  hashes only. Not yet executed end-to-end (policy inputs incomplete).
- `scripts/build_synthetic_smoke_input.py` — NEW: builds the unsigned-draft
  synthetic fixture `.local/e2e-003-synthetic-input.json` (435 input bytes).
- `.local/E2E-003-owner-authorization-DRAFT.md`,
  `.local/E2E-003-source-rights-DRAFT.md` — NEW: unsigned drafts for owner
  review (private, git-ignored; full contents shown below).
- `docs/engineering/testing/browser-e2e/E2E-003-READINESS.md` — this report's
  final section (to be completed).

No specification, knowledge map, contract, route, UI text, or deployment file
was changed. No duplicate provider service was created.
