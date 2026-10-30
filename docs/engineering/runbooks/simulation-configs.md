# Simulation configuration and pending run snapshots

Run `uv run python scripts/run_checks.py simulation-configs` with owned PostgreSQL
and private storage available. This migrates only the disposable test database,
checks contracts/plugins, concurrent SQL edits, ownership, immutable snapshots,
source corrections and HTTP authentication, then mypy/client drift.

The existing branch is the shared baseline reference; no baseline observation is
copied or relabeled. Save a draft version using
`POST /api/v1/projects/{project}/patients/{patient}/branches/{branch}/simulation-configs`
with an authenticated administrator and Idempotency-Key. Body:
`{"expected_draft_revision":0,"config":<SimulationConfig>}`. Use schema/strict units
from OpenAPI. `tests/test_simulation_contracts.py::configuration` is a runnable
conspicuously artificial example with three imaging slots and an independent lab
profile. Replace its branch/hash/revision with owned values in integration fixtures.
Field errors preserve the submitted draft client-side; stale revision409 requires
reload rather than overwriting another edit. Old versions remain readable by ID.

In isolated test mode only, freeze a run through
`POST .../branches/{branch}/simulation-runs` with
`{"config_id":"<saved-id>","expected_draft_revision":1,"expected_config_hash":"<server-hash>"}`.
GET the returned Location. Each new idempotency key creates a distinct immutable
pending snapshot; retrying the same key returns the original receipt. Snapshot has
exact input manifest hash, full config, code/environment identity and queued time.
No job is dispatched, completed output advertised or current-run pointer advanced
by COS-041. Later orchestration/publication is separate.

Normal development/production run authorization returns409 until permitted authentic
observed-baseline and reviewed-policy integration exists. Editing an unreviewed
draft does not satisfy those gates. Rights withdrawals deny reuse while immutable
metadata history remains retrievable. No external inference or patient data export.
