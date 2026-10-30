# Simulation and branch closure

Discover the five hypothetical families at `GET scenario-definitions`
(SC-01 through SC-05 with versioned definitions and synthetic-only labels),
check eligibility through the existing checks, create a draft branch at
`POST branches` with an idempotency key, and enumerate drafts at
`GET branches`. Submit runs through the existing run endpoints; idempotent
submission returns the same job rather than duplicate simulations.

Complete runs through the existing completion/publication flow: explicit
verification of the exact run/report/hash, all required follow-ups, safety
checks and current rights, with If-Match on the branch pointer. Viewers see
only publication-eligible published content. Failed or in-progress runs
never read as completed branches; prior published runs stay retrievable.

```powershell
uv run python scripts/run_checks.py simulation-closure
```

The checked flow uses synthetic fixtures and mocked auth boundaries.
Engine behavior, genuine curation and COS-071 coverage remain open.
