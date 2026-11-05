# COS-E2E-002 Provider Integration Report (Meta `muse-spark-1.3`)

Status: **BLOCKED — no live request was made or authorized.** Correct per the
deny-by-default architecture; this is a structural finding, not a missing
configuration detail.

## Three independent gates, all closed

1. **No export policy exists.** `Settings` requires `export_policy_path` with
   a versioned policy whose provider/model/endpoint/account/region match and
   whose permission + source-rights evidence file hashes verify
   (`read_policy` in `provider_gateway.py`). `.env` sets
   `EXTERNAL_INFERENCE_ENABLED=true` with a live `MODEL_API_KEY` but defines
   no policy path. No policy document exists anywhere in the repo.
2. **No verified provider adapter.** `export.invoke_provider` unconditionally
   raises `NO_VERIFIED_PROVIDER_ADAPTER`. `MetaHTTPTransport.send` only
   operates with an `httpx.MockTransport` in `mode="test"`, and
   `ClosedOutputValidator.validate` unconditionally raises
   `GROUNDING_VALIDATOR_UNAVAILABLE`. No route calls the execution harness.
3. **No owner approval.** COS-HACK-001 §11 and the task require explicit
   project-owner approval with synthetic, non-identifying, pre-approved inputs
   before any live call. No such approval is recorded.

Fabricating a policy file, forging permission-evidence hashes, weakening the
gate, or treating the VS Code agent session's own Meta connection as the
application's integration would each violate explicit instructions. None was
done. The credential was never printed, logged, or committed.

## What was verified instead

- Deterministic local fallbacks remain labeled as such in the insights UI
  (`rule_based_summary` execution mode asserted in component tests).
- The continuous journey binds insights to an exact snapshot hash without
  invoking any provider.

## Demo implication

Acceptance criteria 10–11 (genuine authorized Meta inference with grounded,
identified output) cannot be demonstrated. The demo must present the
rule-based path explicitly as local and non-agentic.
