# Complete simulation engineering workflow

Run `uv run python scripts/run_checks.py simulation-complete` with owned private
PostgreSQL, Redis and object storage available. This migrates the disposable test
database and records actual scoped outcomes in `evidence/simulation-complete.json`.
Run `uv run python scripts/run_checks.py frontend` for typed UI checks/build.

Open `/simulation`, load an authorized branch, save an explicit config, inspect
eligibility and the sampled schedule, then review assumptions. Test-mode fixtures
can freeze a run and submit the existing durable worker command
`simulation_complete` with `run_id` and `expected_config_hash`. Normal development
generation remains disabled for missing authentic baseline/scientific policy.
The worker creates ready output or a blocked completion with a failure stage.
It cannot publish. Optional missing labs stay missing; missing required tumor
observations and failed geometry/mesh QC block completion.

Review V1–V8 findings and explicitly publish with a current pointer/revision/head
and engineering evidence hash. The command atomically exposes the complete state
manifest and current-run pointer. Retries are idempotent; a competing publication
requires reload. Historical publications survive failed attempts and corrections,
while changed source revisions/rights block current use. Source clinical revisions
and baseline measurements are never rewritten. The selected state never carries
another visit's clinical values or mesh forward as a current observation.

The lightweight regression uses five families × ten seeds, plus five repeated
pairs with semantic hashes that ignore generated UUIDs. These are target-based
tabular runs. Actual geometry coverage separately uses a shared 216mm³ artificial
cube and three realized masks/meshes per family. A preliminary 512mm³ cube's growth
exceeded the frozen mesh-QC computation budget; that failure remains documented.
No clinical tolerance, source rights or scientific review is inferred from fixtures.

## Required simulation checks and evidence mapping

| Requirement | Implemented evidence scope |
| --- | --- |
| SLRE-T01–T04 | Family pure checks, five-family actual run, realized order and configured regrowth |
| SLRE-T05–T06 | SC-05 stable/shrinking tumor with independent clinical deterioration tests |
| SLRE-T07–T08 | Server eligibility negative receptor/context gates; specific exposure rules disabled |
| SLRE-T09–T11 | Contract/unit/negative/time and jitter collision tests |
| SLRE-T12 | Explicit missing clinical events/notes; no normal/zero fill |
| SLRE-T13 | Fifty tabular trajectories, five replay pairs, exact geometry/mask semantic checks |
| SLRE-T14–T15 | Shared baseline preservation, strict run/state/batch ownership and private HTTP tests |
| SLRE-T16 | Pipeline stage fault injections, worker lease/cancel/retry checks and atomic publication rollback |
| SLRE-T17 | Fixed synthetic discriminators and lineage/state checks; no promotion |
| SLRE-T18 | Deterministic note regeneration and unsafe/conflicting prose rejection |
| SLRE-T19 | Fixed-grid clipping, target tolerance and mesh-QC refusal tests |
| SLRE-T20 | Formal response labels unavailable; numerical region volume only |
| SLRE-T21 | Discrete surgery transition unsupported and disabled; positive surgery simulation deferred |
| SLRE-T22 | Irregular per-modality time and actual elapsed intervals retained |
| SLRE-T23 | Complete deterministic path has no LLM/provider dependency |
| SLRE-T24 | Current rights/withdrawal propagate to batches, geometry, states and completions |
| V1–V8 | Typed structure, sampled timing, units/actual measurement, family/course, exact notes, origin, safety, semantic replay |

This maps software evidence, not specialist plausibility approval. Authentic D01/D03,
genuine repeated exam D02, patient-separated evaluation D05, final hardware/demo D06,
scientific policy C06 and any external-inference access remain separate open gates.
