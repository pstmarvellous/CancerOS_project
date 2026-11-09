# ADR-060 — Repair the existing recovery workflow contracts

Date: 2026-11-09. Status: adopted for the assigned COS-REC-06–09 audit/fixes.

The earlier recovery handoff claimed completion despite a failed mesh journey,
unexecuted simulation/selected-case interpretation, and incomplete usability checks.
The owner requested critical review and completion of the missing implementation.

Reuse the established source registry, private staging, exact-grid alignment,
annotation/QC, deterministic measurements, existing job worker and state assembly.
Do not add a second imaging engine or AI gateway. Imported functional regions remain
regions; a synthetic measurement never establishes authentic MRI validation.

- Discover segmentation image/study ownership explicitly. Resolve a lesion's mesh
  through its owned QC/mesh/measurement lineage rather than guessing report UUIDs.
  Newly reconstructed models can be opened through an exact owned mesh-QC report.
- Add an administrator-only current simulation draft read under its owned branch.
  A withdrawn newest draft fails closed; it never silently selects an older draft.
  The builder resolves the current case revision and submits the registered scenario
  template version, explicit per-day targets and optional artificial observations.
  Editing assumptions invalidates the pending builder result; frozen runs stay immutable.
- Preserve exact measurement times and explicitly pinned prior comparison values
  in interpretation context. Optional `context_input` binds interpretation to the
  same assembly request. The server checks patient/state identity, hash, branch,
  revision, time domain, current rights and exact note membership again.
- Keep additive wire fields compatible with schema version 1. Record changed
  assembly/template algorithms separately; old saved metadata remains readable,
  while incompatible cached generation is denied rather than reinterpreted silently.
- Submit the browser fusion query as POST so the real browser Origin reaches the
  existing cookie-session CSRF guard. Do not weaken the guard to accommodate a GET
  proxy that internally changes method to POST.

Affected tests and generated clients are recorded in
[the audit report](../testing/rec06-09-audit/REVIEW.md). Evidence is scoped to explicitly
synthetic disposable records, actual SQL/private storage and real browser/worker
execution. External inference, authentic-data rights, qualified review and publication
remain separate gates. No original specification or knowledge map is modified.
