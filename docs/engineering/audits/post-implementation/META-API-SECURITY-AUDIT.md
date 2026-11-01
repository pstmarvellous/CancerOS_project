# COS-AUDIT-002 Meta API and Security Audit

**Run:** `cos-audit-002-arch-001` · **Candidate:** `bd7b2c2`
No secrets are printed, stored, or committed by this report. Live keys were never displayed.

## Provider configuration (inspected, not executed live)

| Item | Finding |
|---|---|
| Endpoint | Pinned literal `https://api.meta.ai/v1/responses` in `provider_gateway.py:43` and `settings.py:32`; `read_policy` additionally enforces `Literal` match — no configurable-URL drift |
| Model | Default `muse-spark-1.3` in `settings.py:31` and `.env.example:19`; configured (not assumed) model is what the gateway sends via `MetaAdapter.request` |
| Contributor mode | No Contributor-mode path found in the gateway; `execute_private` only supports the closed test harness (`LIVE_PROVIDER_GATE_NOT_CLOSED` outside `mode == "test"`) |
| Auth storage | `model_api_key: SecretStr \| None`, `hide_input_in_errors`, never serialized; `.env` is git-ignored and `check_hygiene.py` passes |
| Tool calling | No tool-calling surface: fixed `INSTRUCTIONS` forbid executing instructions in data or calling tools |
| Structured output | `strict_json` rejects duplicates, non-finite numbers, truncation, oversize (>64 KiB); `MetaAdapter.parse` enforces snapshot-hash, reference, usage and identity checks |
| Timeouts/retries | Bounded (`max_attempts` 1–3, `timeout_seconds` ≤ 30); `PROVIDER_TIMEOUT` is the only retryable failure; budget reserved per attempt |
| Token/cost controls | Per-attempt usage validated (ints 0–1,000,000); candidate prose withheld (`publication_status: withheld_pending_cos064`); provider download/training paths absent |
| Fallback | `local_summary` template never passes input prose; empty inputs → `insufficient_evidence` |
| Data export policy | Denied by default: `external_inference_enabled=false` default; `verified_policy` requires enabled flag + key + policy path with hash-verified permission evidence and exact wire hashes; `check_export` legacy guard retained |
| Mock/live separation | `execute_private` docstring: internal harness only; no route calls it; `authorize_now` must verify owned snapshot plus current rights per input |

## Outstanding live tests (not run in this audit)

Per audit restriction §9, no paid or externally transmitting call was made. The `MODEL_API_KEY` slot exists in `.env` (git-ignored). A minimal live smoke test remains a **proposed explicit gate**: authorized session + verified export policy + bounded prompt, recording model identity, token usage, grounding verdict and cost — never inferred from authentic-session access.

## Security posture

- No hard-coded credentials, secret commits, public artifacts, path traversal, SQL injection (parameterized `text()` clauses sampled), unsafe deserialization, or client-side provider credential found in the sampled paths.
- `.env` git-ignored; `.env.example` contains placeholders only.
- Cross-project/patient/branch denial covered by conformance and lineage tests (frozen evidence reused; full live rerun exceeded the audit time budget and is recorded, not assumed).
- One environmental failure observed: `test_identity_db.py::test_actual_sql_membership_and_role_denial` fails with connection timeout because no local PostgreSQL instance is running — infrastructure absence, not a code defect. Non-DB identity/export tests: 17/17 pass.
- Dependency CVE scan with reliable advisory data not run; recorded in the remediation backlog rather than claimed.
- Prompt-injection resistance: fixed instructions, untrusted-evidence framing, per-attempt policy recheck, and adversarial suite (20 adversarial cases withheld as `failed_grounding`).
- Excessive disclosure: `Health`/`Problem` schemas bounded; error payloads scanned for bearer/key/grant graph in the observability gate (pass).

## Critical findings

None. No exposed secret, no privacy/provenance violation, and no prohibited-claim publication path found in the sampled paths. Open gates (restore, deployment, review) are access/evidence absences, not active exposures.
