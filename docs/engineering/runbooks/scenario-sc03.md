# SC-03 increasing hypothetical size

Run `uv run python scripts/run_checks.py scenario-sc03` with owned data services.
Use family SC-03/version sc03-explicit/1 with explicit positive increasing mm3
targets above its mask-derived baseline, supplied ordered follow-up days and an
independent clinical profile. There is no default growth/treatment-response rate.

Use the common draft/run routes, then read
`GET .../simulation-runs/{run_id}/targets` for validated latent quantities. This
authenticated calculation also works when geometry_policy is none; no geometry job
or fake scan is generated. For geometry-enabled runs, use the existing worker jobs
and explicit result-ID geometry-validation route. Inspect target, realized volume,
clipping/tolerance reasons, source coordinate frame and containment-not-established.

Field-of-view failure retains a blocked result with missing realized volume and no
ready state, rather than substituting the desired target. Stable symptoms or lab
context can coexist with growth. Nothing asserts treatment resistance, metastases,
causal progression or a prognosis. Full-run review/publication remains separate.
