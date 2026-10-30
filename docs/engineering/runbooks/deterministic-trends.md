# Deterministic descriptive trends

COS-052 uses `POST /api/v1/projects/{project_id}/patients/{patient_id}/trend-queries`
with a `TrendQuery` containing the same pinned `TimelineQuery` used by `/timeline`.
Use `cursor: null`: calculations read the complete authorized window, even when the
timeline display uses pagination. Optional pair IDs must both belong to that window.
No client-supplied replacement values are accepted. Current lineage rights apply.

Open `/timeline`, supply an authorized private context, load observations, then load
trends. Select a series to inspect its exact values, units, elapsed days and input
references. A missing point interrupts visual guides. Censored bounds have separate
directional markers and never become exact observations. Context changes cancel
pending requests. Geometry is loaded only for an actual selected timeline point.

Run `uv run python scripts/run_checks.py deterministic-trends` and
`uv run python scripts/run_checks.py frontend`. Evidence records contain the actual
results; failed attempts are not successful verification. No LLM is involved.

Method: later minus earlier, supported unit conversions, percentage relative to the
earlier nonzero value, endpoint change divided by actual compatible elapsed days.
Physical-volume arithmetic retains exact precision separately from display values.
Zero baselines, conflicting measurements, unresolved/tied times, incompatible mask
meanings and censored values return explicit reasons. Ordinal symptoms yield only
direction. Tolerance is a numeric display decision, not clinical significance.

These are descriptive research computations. Authentic longitudinal evaluation,
qualified scientific review and final browser/WebGL verification remain separate
gates. No response classification, forecast or clinical recommendation is supplied.
