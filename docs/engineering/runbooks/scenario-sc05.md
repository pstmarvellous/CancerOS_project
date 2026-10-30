# SC-05 independent condition course

Run `uv run python scripts/run_checks.py scenario-sc05` with owned local data services.
Use family SC-05/version sc05-explicit/1 and explicit sc05_parameters version
clinical-condition/1. Select an existing tumor family SC-01/02/03; provide its required
parameters plus affected concepts, onset/recovery, internal severity and explicit
numeric or symptom course points. Numeric direction is declared, not inferred from
a disease label. Symptom scale simulation_0_10 is not CTCAE.

Save/freeze the common isolated test configuration, then read its targets. Output
contains independent clinical_condition metadata and ungraded hypothetical events
linked to actual configured slots. Missing/unsupported concepts or insufficient
course points return explicit errors; no clinical baseline is filled. A recovery
setting requires a demonstrated configured reversal.

Use shared geometry jobs and validation for tumor quantities. A stable tumor can
pass its size check while symptoms worsen; a quantized shrinking pattern can fail
its geometry check while the condition descriptor stays available. Both remain
synthetic research assumptions. These descriptors are not materialized source
records, certified toxicity, treatment causality or patient advice. Full-run
validation/publication and authentic evidence remain gated.
