# Private engineering state assembly

Create an owned simulation timeline origin and an engineering branch with POST
`/api/v1/projects/{project}/patients/{patient}/branches`, using an available baseline
measurement, optional mesh-QC report, origin and explicit run UUID. This branch is
labelled engineering_fixture; it does not authorize a real simulation engine or
establish a genuine observed baseline. GET Location reads its immutable baseline hash.

Enqueue the shared imaging job `state_assembly` with expected_revision=current and
input StateBuildInput: target_revision, captured association_head, branch_id, exact
simulation-relative time, explicit clinical_members and imaging_members. Current
clinical IDs must be in that revision and exactly match anchor time. Current imaging
needs an eligible explicit association at the captured head/time; historical imaging
needs role=historical_context and a reason. Its original time remains visible.
No member is silently carried forward. OpenAPI defines exact nested typed contracts.

Poll job Location, then GET `/states/{result_report_id}`. It returns snapshot/hash,
missing/conflicts, current eligibility and available actions. Rebuilding old target N
after N+1 uses original members and produces a stale historical snapshot; it cannot
publish as current. A lab-only state may contain historical geometry without any
mesh processing. Empty/unknown current time and OBSERVED enablement are not faked.

An administrator explicitly POSTs `/states/{id}/reviews` with snapshot_hash,
accepted_engineering/rejected and evidence_sha256. A separate `/publications` POST
uses snapshot_hash, expected_patient_revision, expected_association_head and the
exact expected_review_id. Both require Idempotency-Key. Publication is a private
engineering record; scientific review stays pending. Changed preconditions return
409; inspect/rebuild/review rather than silently replacing inputs.

GET `/states?branch_id=...&published_only=true&limit=25` returns items, next_cursor,
snapshot_revision. Keep filter/limit/actor context unchanged when using next_cursor;
expired/tampered/wrong-scope cursors fail409. The list is frozen across later states
or corrections; individual current restrictions remain visible. No public link exists.

Verification: `uv run python scripts/run_checks.py twin-states`. Actual disposable
SQL/private storage and shared Redis worker tests establish scoped infrastructure,
not authentic observed twin/scientific release. Genuine baseline and review evidence
are the next dependencies for those capabilities.
