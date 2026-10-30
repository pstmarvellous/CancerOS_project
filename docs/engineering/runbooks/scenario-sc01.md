# SC-01 explicit sustained reduction

Run `uv run python scripts/run_checks.py scenario-sc01` against owned local data
services. The fixture includes the real SQL/private S3/shared-worker path and a
deliberately coarse mask whose targets decline but realized volumes plateau.

Save a SimulationConfig using family SC-01, definition_version sc01-explicit/1,
positive strictly decreasing target knots below its actual baseline, at least three
ordered imaging slots and an independent clinical profile. Keep category
no_specific_assumption. For geometry set policy isotropic-fixed-grid/1. The config
and queued-run routes are in simulation-configs.md; production authorization remains
blocked. Isolated tests freeze code/environment and association head with the run.

Enqueue existing synthetic_geometry jobs for the common run ID and each target_index
as documented in synthetic-geometry.md. No legacy authorization row is fabricated.
After obtaining all result IDs, POST
`.../simulation-runs/{run_id}/geometry-validation` with
`{"result_ids":["<slot1-result>","<slot2-result>","<slot3-result>"]}`.
It returns latent targets and realized mask measurements separately, an ordering
check, reasons and next action. Missing, plateaued or reversed realized values block
the check; successful ordering alone never publishes the run. Source withdrawal
denies current use, and old metadata/history remain intact.

This backend workflow is not a complete simulated timeline UI or clinical response
assessment. Full run integration/review/publication remains COS-050 and its gates.
