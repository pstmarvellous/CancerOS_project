# Private engineering mesh reconstruction

Requires existing patient editor access, an available COS-033 measurement and
current source/QC rights. All enabled data here are synthetic engineering fixtures.

POST `/api/v1/projects/{project}/patients/{patient}/imaging-jobs`, authenticated,
with a fresh `Idempotency-Key` and body:

```json
{"expected_revision":1,"command":{"operation":"mesh","input":{"measurement_id":"<owned-measurement-uuid>","purpose":"engineering_region_preview"}}}
```

Poll the returned job Location. Dispatch/process using the existing imaging worker
runbook. A successful job's result_report_id identifies GET
`/api/v1/projects/{project}/patients/{patient}/mesh-runs/{id}`. GET the `/asset`
suffix for private typed mesh JSON; same authentication required. No frontend or
GLB export is claimed by this task. Report status remains generated_pending_mesh_qc.

Missing/unavailable measurements, withdrawn evidence or wrong ownership reject
access. Empty/invalid masks, unsupported geometry and size budgets fail the job;
valid original mask and measurement history remain. Restore eligible evidence or
select supported input, then enqueue a new command; do not fabricate geometry.
Repeated command keys replay the same result under current rights. Display must
identify synthetic origin, annotation meaning, RAS/mm and pending review. Do not
label a functional or engineering region as an approved anatomical tumor.

Local verification: `uv run python scripts/run_checks.py mesh-reconstruction`.
This uses artificial private SQL/S3/Redis fixtures; no authentic case or scientific
approval is established. COS-035 must validate topology/display suitability next.
