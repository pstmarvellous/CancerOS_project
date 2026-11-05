# COS-E2E-001 Meta Live Integration Report

Status: **BLOCKED — no live provider call was made.** This is the enforced
safe outcome, not a test failure to bypass.

## Gate evidence

- `src/canceros/settings.py` refuses to boot with
  `EXTERNAL_INFERENCE_ENABLED=true` unless `verified_policy()` in
  `src/canceros/export.py` confirms a versioned permission policy whose
  provider/model match the configuration and whose permission-evidence file
  hashes verify.
- The workspace `.env` sets `EXTERNAL_INFERENCE_ENABLED=true` and carries a
  live `MODEL_API_KEY`, but **no export-policy file exists** in the repo
  (no `EXPORT_POLICY` key in `.env`, no policy document under `docs/`).
- Consequence: `Settings()` raises `External inference requires verified
  versioned permission policy and private credentials`. The development stack
  for this session was started with `EXTERNAL_INFERENCE_ENABLED=false` in the
  process environment only; `.env` was not modified.

## What was (and was not) done

- Inspected provider wiring read-only (`provider_gateway.py`,
  `provider_contracts.py`, `export.py`, settings gate).
- Never printed, logged, screenshotted, or committed the credential.
- Never invoked the Meta endpoint, from the app or otherwise.
- Backend provider unit suites (`test_provider_api`, `test_provider_gateway`)
  exist for fixture-scoped behavior; they were not promoted to live claims.

## Unblocking conditions (owner decision required)

1. Recorded source-rights and data-use authorization for the exact inputs.
2. A versioned export policy file with matching provider/model identity and
   verifiable permission evidence.
3. Explicit owner approval for the specific live call (test inputs must be
   synthetic, non-identifying, and pre-approved per §11 safety gate).

## Demo implication

Criterion 10–11 of the acceptance list (genuine authorized Meta inference with
grounded, identified output) cannot be demonstrated until the above close.
The UI correctly offers deterministic local fallbacks labeled as such; those
must never be presented as live Meta responses.
