# Durable CPU imaging commands

An authorized patient editor enqueues an existing immutable operation input:

```text
POST /api/v1/projects/{project_id}/patients/{patient_id}/imaging-jobs
Idempotency-Key: imaging-command-1
{"expected_revision":1,"command":{"operation":"segmentation_qc","input":{"segmentation_id":"<owned-annotation-uuid>"}}}
```

Operations also include geometry, preprocessing and alignment, using their existing
typed input contracts. The response is 202 with a Location for GET job status.
POST `/imaging-jobs/{id}/cancellations` requests cancellation idempotently. Running
cancellation is acknowledged by the worker before a result commit. A changed body
under an existing key is rejected. Current-head corrections do not replace frozen
inputs; code/hash/rights incompatibility blocks instead of silently changing a run.

Run one bounded worker cycle explicitly (workers do not auto-start):

```powershell
uv run python workers/imaging.py --once
uv run python scripts/run_checks.py imaging-worker
```

The CLI supervises one child with wall/RSS limits. Its output describes the process
cycle; SQL/API job status determines operation success. Do not interpret process exit
or successful jobs as scientific approval/publication. Lost leases recover on a later
cycle; transient retries have bounded backoff. Validation failures need a new corrected
command. No GPU, external service or model weights are required.

POST `/artifacts/{artifact_id}/read-grants` with `{"purpose":"restricted_review"}`
returns a private, version-specific URL expiring within 120 seconds. Original source
images require admin; other approved imaging reviews require patient edit permission.
Never paste URLs into logs, AI prompts or documentation. Signed access can persist
until expiry after withdrawal. This is not public sharing or publication.

Admin-only cleanup is two-step: POST `/imaging-cleanup-plans`, commit that response,
then POST `/imaging-cleanup-plans/{plan_id}/applications`. Plans show counts, not keys.
Only tagged, unreferenced, aged fixture versions are eligible; active jobs block it.
No deletion of patient source records, references, untagged objects or whole buckets.
Reservations are retained for safe retry after a partial object/SQL failure. Do not
use the internal test clock against user objects. No existing-user cleanup was run.

Evidence covers real private PostgreSQL/Redis/S3 fixtures, actual child-process limits,
HTTP authority, lease/retry/cancel/failure cases and bounded cleanup. Publication,
authentic-source review, large-study load and archived environment replay remain open.
