# Explicit simulation sampling

Run `uv run python scripts/run_checks.py simulation-sampling` against owned private
test services. This records actual results in `evidence/simulation-sampling.json`.

Add optional `sampling` settings to a new config draft: per-slot `jitter_rules`
with bounded day offsets, per-channel uniform `noise_rules`, and Bernoulli
`missingness_rules` with an explicit reason/probability. All are hypothetical
engineering distributions. Omit settings for exact configured samples. Fixed
`noise`/`missingness` profiles remain available; duplicate policies are rejected.

Read `simulation-configs/{config_id}/schedule-preview` before freezing, or
`simulation-runs/{run_id}/sampling` afterwards, under the existing patient API base.
These private administrator previews preserve stable slot IDs, sampled modality
times and missing reasons. Unknown source dates remain unknown. The generated
clinical batch stores the sampling/PRNG version and actual sampled values.

Within-modality jitter collisions, unsupported precision, negative quantities,
component conflicts and family-erasing sampled tumor changes block generation.
Required missing imaging blocks anatomical completion; an optional absent lab
stays missing in its note rather than removing a state or becoming normal/zero.
Latent configuration and profiles must not supply observations to later temporal
features or forecasts. Real-data calibration and scientific review remain pending.
