# COS-UX-RECOVERY-002 reference context

Scope: assigned implementation task; specialist self-review through architecture,
data-integrity/security and verification perspectives; no independent clinical review.

Queries executed: provenance, timeline against capability, academic and repository/scientific maps.
Exact commands, output, IDs and incoming/outgoing dependency/guard/verification edges:
[COS-UX-RECOVERY-002.json](COS-UX-RECOVERY-002.json). Unmatched queries are gaps, not successful source reviews.

Original specification sections inspected: COS-SPEC-009 v1.0 sections 1-4.3 and 11-12; COS-SPEC-008 v1.0 sections 17 and 19; COS-SPEC-010 v1.0 sections 2 and 7 (inspected during UX recovery); current source and lineage validators inspected for this continuation.
Agent guidance: COS-000 sections 3–8/11; repository instructions sections 2–8;
COS-REF-001 sections 2–3/15–23; COS-HACK-001 sections 2–3/9/11/17.

## Source Learning Record and Three-Source Decision Note

Map source IDs are retrieved pointers only. Academic text, upstream interfaces and
empirical papers are NOT claimed read or reproduced by this refresh. Append actual
source learning, pinned interface inspection and empirical scope below before
enabling consequential scientific or security behavior. Medical reading exemptions
must be justified for the actual task; this refresh grants no exemption.
Missing academic/repository/empirical categories remain unverified for future domain
enablement. No weights, datasets or upstream code are adopted by a lookup.

Decision: preserve scoped specifications and keep unsupported capabilities disabled.
Verification: task-specific evidence and ledger, not map
existence. Failure fallback: disable affected domain/provider capability. Map drift
is recorded separately; original maps are unchanged.

## Hackathon Compliance Impact

Applies to preservation, source privacy and truthful contribution records. No external
model request is authorized by this task record. Models/rules/access remain unverified.
Architecture is preserved; refer to the task ledger for changed files and actual checks.

## Resumed implementation scope and decision

The user requested implementation to resume after the verified UX recovery. The
phase records already contain COS-057–104 code, while authentic-source, scientific
review, provider and release evidence remains separate. This bounded continuation
closes a concrete integration defect in the existing synthetic presentation adapter:
the v1 validator could accept mixed patient records, changed chart coordinates and
surfaces exchanged between otherwise valid state keys.

Map refresh returned 15 capability nodes, five academic behaviors (DAT.02,
TWIN.02, AI.04, AI.06, UX.01), and 99 adjacent edges. GOV.PROV constrains
TWIN.STATE, TWIN.BRANCH and UX.TIMELINE. Source requirements were inspected
during COS-UX-RECOVERY-001 and remain unchanged: SPEC-009 sections 1–4.3/11–12,
SPEC-008 sections 17/19, SPEC-010 sections 2/7.

Source Learning Record: inspected local TimelinePoint/TimelineWindow,
TrendReport/TrendSeries/PointComparison, Surface and their actual construction in
timeline_runs.py, temporal_trends.py and prepare_synthetic_demo.py. Exact strings
carry backend decimals; plotting wire values and exact values are distinct.
Comparisons retain explicit state/source references. No clinical computation or
geometry reconstruction algorithm is changed. Medical textbook/cohort reading is
not applicable to this representation-integrity fix; mapped books and papers are
pointers, not claimed source reading or validation. No upstream dependency, model,
weight or dataset is adopted. Local candidate at inspection: Git 9221233 plus
preserved uncommitted work. No independent clinical review.

Three-source decision: existing specification provenance/context requirements →
reuse the implemented typed backend reports and source preparation → purely
synthetic corruption cases and real pipeline/browser checks. Empirical clinical
support remains absent. Chosen solution: internal bundle `synthetic-demo/2`,
preparation-time mesh bindings, strict context/reference/quantity coherence and
fail-closed loading. No new auth system, backend route, scientific arithmetic or
data-rights decision. A separate agent reviewed accepted-corruption cases and
implemented only the assigned test file; this is engineering review, not clinical
approval.

Each mesh binding records point/patient/branch/run/state/geometry-result identity
and a SHA-256 surface digest. The producer and Node reader use a fixed binary
encoding of IEEE binary64 coordinates, unsigned triangle indices, bounds and
transforms with fixed metadata/count prefixes. This avoids cross-language JSON
float spelling differences. The digest binds bytes to a trusted producer record;
it is not a signature or an independent attestation of scientific truth. Source
rights and quality checks remain in the existing pipeline.

Compatibility: v1 bundles are refused and must be regenerated with
`npm run demo:prepare`. FastAPI/OpenAPI/database contracts and generated clients
are unchanged; the internal TypeScript bundle contract and producer change
together. Existing sessions remain expiring and bound to a bundle fingerprint.
Repeated scenario query parameters are now rejected rather than choosing one.
External inference remains disabled for preparation; runtime does not call a
backend/provider. Authentic data and publication gates are unchanged.

Verification completed: 113 frontend tests across 18 files (including 39 focused
adapter tests), production build, typecheck, focused ESLint, preparation-script
Ruff and 3 real Chromium checks passed. Actual version 2 pipeline preparation and
Python-to-TypeScript surface digest interoperability succeeded. The first
preparation attempt timed out because local data services were stopped; existing
loopback services were restarted without a reset and the retry passed. Typecheck
initially found a fixture tuple type and nullable-origin narrowing issue; both were
corrected before the passing check. Updated browser screenshots show the working
phantom and clinical views. Full results and file inventory:
[integrity continuation](../testing/ux-recovery/INTEGRITY-CONTINUATION.md).
