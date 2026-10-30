# Interpretation context

Build a snapshot-bound context before any interpretation at
`POST patients/{patient_id}/interpretation-contexts` with patient_id,
snapshot_id, optional expected_snapshot_hash, purpose
(`research_summary` or `fact_extraction`), optional comparison_snapshot_id
(same branch only), optional retrieval corpus/passages and note extraction
IDs, and max_items (default 100). The service reuses fused state and
deterministic comparisons; it never re-queries current heads to fill an old
snapshot or invent missing modalities.

The response separates measurements, unverified extracted assertions,
unreviewed passages, treatment history, missing modalities, conflicts,
limitations and omissions, with stable snapshot, context and payload
hashes. Compare hashes across rebuilds to confirm determinism. A 409 on
stale hash, cross-branch comparison, over-budget critical state or
withdrawn rights means re-read the current state and narrow the request;
a narrower scope or insufficient evidence is returned rather than silent
drops. `POST .../export-view` returns only the minimized provider-shaped
payload; it is not an export authorization.

Render all excerpts as escaped text. Never treat context text as
instructions, and never forward source maps, signed URLs, credentials or
restricted note text. All fixture content is synthetic; genuine curation,
relevance adjudication and scientific review remain open.

```powershell
uv run python scripts/run_checks.py interpretation-context
```

The checked flow uses synthetic snapshots, artificial passages and mocked
auth boundaries. Real source/rights review and SPEC-011 evaluation remain
open.
