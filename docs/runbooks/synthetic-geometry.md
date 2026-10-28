# Hypothetical geometry verification

Use `uv run python scripts/run_checks.py synthetic-geometry` with owned local data
services running. It migrates only the disposable test database and exercises pure
geometry plus SQL/private S3, shared worker and immutable state integration.

API sequence for an isolated test fixture with an authenticated project administrator:
read `GET /api/v1/projects/{project}/patients/{patient}/branches/{branch}` and use its
exact baseline hash. Send `POST .../simulation-fixture-runs` with an idempotency key
and this typed body (replace the placeholders with owned fixture values):

```json
{
  "branch_id": "<owned-branch-uuid>",
  "baseline_hash": "<exact-server-baseline-hash>",
  "targets": [{"relative_day": "10", "target_mm3": "24"}],
  "shape_config": {"version": "isotropic-fixed-grid/1", "seed": 42}
}
```

Enqueue `POST .../imaging-jobs` with the current `expected_revision` and command
`{"operation":"synthetic_geometry","input":{"run_id":"<frozen-run-uuid>","baseline_hash":"<exact-server-baseline-hash>","target_index":0}}`.
Use the shared imaging dispatcher/worker. Read the completed job's result through
`GET .../synthetic-geometry-results/{result_id}`; its `/mesh` read is available only
for a usable nonzero surface. `tests/test_synthetic_geometry.py` provides a runnable
fixture example without source records or credentials.

The isolated test API can freeze explicit target runs. Normal development and
production configurations deny this operation. Targets are supplied mock inputs,
not predictions or executable treatment rules. Geometry artifacts have private
lineage and current-rights checks; metadata history survives withdrawal while
geometry use and mesh reads are denied. Never expose test credentials or signed
storage links. No source acquisition or external inference is performed.

Inspect target and realized mask volume, tolerance, transform, original grid,
seed/version, blocked reasons, synthetic labels and pending scientific review.
Configured zero is simulated absence with no mesh. Blocked results have no state.
Ready results have draft states and require separate review/publication commands.

Real acceptance still requires permitted authentic masks, independent scientific
review, simulation engine integration and the target device/demo checks.
