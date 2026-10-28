# Mesh quality and immutable display selection

After COS-034 succeeds, enqueue an imaging job with existing authenticated headers:

```json
{"expected_revision":1,"command":{"operation":"mesh_qc","input":{"mesh_run_id":"<owned-run-uuid>","triangle_budget":20000,"simplify":true}}}
```

Use a fresh Idempotency-Key and the existing worker dispatch/run procedure. Poll its
Location. The result_report_id addresses
`GET /api/v1/projects/{project}/patients/{patient}/mesh-qc-reports/{id}` and `/asset`.
The latter returns only certified selected geometry under current rights. A blocked
job/report keeps mask measurements and original mesh history. It cannot serve a
display asset. A budget miss may still select certified original/higher-detail
geometry; budget_met is false and next_action explains the limit.

Certification supports bounded single convex shells only. Concave/multicomponent
surfaces need a future general intersection validator. Do not delete components,
force a convex approximation or present a failed QC as successful. Separate source
anatomical review and source rights are required for authentic anatomy. Current
fixtures remain synthetic, even when mesh QC passes.

`uv run python scripts/run_checks.py mesh-quality` runs actual disposable SQL/S3/
Redis and HTTP tests, type/schema checks and a standalone CPU fixture measurement.
The 3×4×2 cuboid benchmark records original/LOD counts and bytes, process RSS after
calculation and CPU/JSON decode time. Peak RSS, browser/device performance and real
studies remain explicitly unmeasured. Those measurements cannot pass D06 release.
