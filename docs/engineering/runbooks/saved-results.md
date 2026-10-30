# Saved results

Persist a gate-published template at
`POST patients/{patient_id}/states/{state_id}/interpretations/{interpretation_id}/saved-results`
with interpretation_snapshot_id, idempotency_key body field and a matching
Idempotency-Key header. Replays return the original receipt under current
permission checks. Read at `saved-interpretations/{saved_id}`; reuse the
exact context at `POST states/{state_id}/saved-result-queries` with
context_snapshot_id and optional expected_context_hash. Every reuse
revalidates a fresh template through the grounding gate; version or state
drift returns 409 rather than a stale answer.

Display labels honestly: “Validated model summary” for fresh gate passes,
“Saved result for this snapshot” for revalidated reuse, “Rule-based
fallback” when generation is unavailable, or a precise unavailable status
with freshness and drill-down. A source correction supersedes by new rows;
old records remain as historical evidence. Withdrawal blocks new reuse
without rewriting retained hashes.

```powershell
uv run python scripts/run_checks.py saved-results
```

The checked flow uses synthetic snapshots, fixture reports and mocked auth
boundaries. Genuine curation, live model access, qualified review and
retention signoff remain open.
