# Clinical generation fixture checks

Run `uv run python scripts/run_checks.py clinical-generation` with the owned private
PostgreSQL/Redis/S3 test services available. The target migrates only the disposable
test database and records actual results in `evidence/clinical-generation.json`.

Save a supported explicit simulation config and freeze a test-mode run. Submit an
existing imaging-job request with `operation: clinical_generation` and input
`run_id`/`expected_config_hash`. Read its private `result_report_id` through
`GET /api/v1/projects/{project_id}/patients/{patient_id}/generated-clinical-batches/{batch_id}`.
Project administrator authorization and current source rights are required.

Generated batches contain configured quantities, canonical units, declared symptom
instruments, hypothetical events and deterministic notes. Source clinical values,
missing baseline values and immutable revisions remain unchanged. Retry returns
the same batch; a changed frozen config needs a new run. Scientific acceptance,
authentic longitudinal evaluation and complete-run publication are not established
by these software fixtures. Normal development generation remains disabled.
