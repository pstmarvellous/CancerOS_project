# Patient and observation closure

Pick a patient at `GET patients` (grant-scoped; admins see project patients,
others see granted patients only), inspect `GET patients/{patient_id}` for
revision, observation and visit counts, then review `GET visits` and filtered
`POST observation-queries` (kind/concept/visit_id, limit 1–100) with the
returned `snapshot_cursor`. Open the exact record at
`GET observations/{record_id}` (adopted C01 semantics) and confirm
source-backed diagnoses at `POST diagnoses/{record_id}/confirmations`
(422 for non-diagnosis kinds; no parallel store exists).

Stage corrections through the existing `observation-batches` flow: all
entries validate or none commit, 100-entry and 1 MiB bounds apply, and kind
changes use new-record plus retraction. Retractions stay source-backed with
idempotency keys. Use the cursor to detect mid-review changes; re-query
rather than assuming stability.

```powershell
uv run python scripts/run_checks.py patient-closure
```

The checked flow uses synthetic fixtures and mocked auth boundaries.
Genuine curation, clinical validation and COS-071 coverage remain open.
