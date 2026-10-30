# Exact-member research context

COS-053: `POST /api/v1/projects/{project_id}/patients/{patient_id}/fusion-queries`
accepts `{state_id, timeline}`. `timeline` may be null. With a simulation timeline,
use its exact branch/run/revision and published completion, `cursor: null`, and an
aware knowledge cutoff. The server bounds event time at the state, including when
the displayed timeline extends farther. Earlier comparisons retain their input IDs;
future visits cannot supply the selected state's values.

On `/timeline`, select an observation and an exact state when multiple states are
listed, then request its overview. Available, Historical, Missing and Conflicting
blocks expose evidence and next actions. Source fixture points without state
membership cannot fabricate an assembled state. Authentic observed-state assembly
remains gated. Missing note extraction and retrieval are visible unavailable blocks.

Run `uv run python scripts/run_checks.py state-fusion`, followed by
`uv run python scripts/run_checks.py frontend`. Actual outcomes live in evidence
records. Pure tests cover display/conflict policies; private fixtures check rights,
exact replay, publication-aware temporal inputs and absence of future facts.

This computed view preserves the canonical state's original ID/hash, revision,
assembly policy and full typed members. It never edits state history or publication.
An old scan remains historical; laboratory changes cannot make it a current scan.
Tumor and clinical indicators remain independent. There is no global confidence,
health score, missing-value filling, clinical interpretation or external model call.
