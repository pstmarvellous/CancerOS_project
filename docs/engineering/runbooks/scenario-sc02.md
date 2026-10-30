# SC-02 declared demonstration modes

Run `uv run python scripts/run_checks.py scenario-sc02` with owned local data
services. It covers SC-02 bounds and mode preservation, SC-01 regression, shared
geometry and stable historical config snapshots.

Use family SC-02/version sc02-explicit/1 and provide exactly one sc02_parameters
object in the common SimulationConfig. Examples of explicit engineering assumptions:

```json
{"mode":"near_stable","max_absolute_change_mm3":"2","max_relative_change":"0.02"}
```

```json
{"mode":"modest_reduction","min_relative_decline":"0.1","max_relative_decline":"0.2"}
```

These are example inputs, not defaults or clinical thresholds. Both absolute and
relative limits apply in near-stable mode. Modest targets strictly decline within
the configured maximum and endpoint minimum. Mode-specific schemas reject irrelevant
keys. The explicit requested mode is preserved when numeric bands overlap.

Keep clinical profile independent, including deterioration with stable lesion size.
Freeze a test-only common run and use existing geometry jobs and geometry-validation
read as in scenario-sc01.md. Inspect family, mode, target and realized quantities,
ordering result and unknown measurement uncertainty. Failed realized mode constraints
remain failures; no target substitution or clipping is performed. Zero allowed by
explicit wide bands is simulated configured absence, not cure or surgery.

Full-run publication, authentic baseline and scientific policy remain gated. A passing
mode check does not establish patient stability or a formal clinical response.
