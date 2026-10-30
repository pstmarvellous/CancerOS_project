# ADR-048: snapshot-bound immutable interpretation context

COS-062 implements SPEC-006 sections 4/11–14 and SPEC-008 freshness over the
existing fused-state, twin-snapshot, extraction, corpus and gateway services.
No new state assembly, imputation, forecasting, generation or export path is
introduced. The context is a read-only projection of one explicitly selected
snapshot plus an optional same-branch comparison; current heads are never
re-queried to fill an old snapshot.

Measurements project only fused `primary_for_display` members with exact
numeric results, preserving member time basis, origin and context at item
level. Extracted note assertions enter as unverified items with source
note/hash and span-derived excerpts; they never become observations.
Retrieved passages enter only from the explicitly requested active corpus
with current rights rechecked, labeled unreviewed general research. Disabled
forecasts and hidden simulator truth cannot enter; treatment history is a
labeled projection of fused members, not advice.

Every nested reference resolves under current project/patient authorization
and intended-use rights: stale snapshot expectations, cross-branch
comparisons, unknown extraction/passage IDs and withdrawn corpora fail
closed. Deterministic selection truncates by a bounded budget; critical
negation, provenance, conflicts and safety limits are never silently
dropped — over-budget critical state or recorded omissions surface as 409
or an explicit omission list. Repeat builds hash identically.

Local context and the provider export view are distinct types. The export
view carries only schema version, purpose, snapshot hash, measurements,
missingness and passage IDs under the provider input schema; source maps,
signed URLs, storage credentials, restricted note text and private linkage
keys are excluded by construction. A hash records identity, never disclosure
permission. All free text remains untrusted data for later stages.
