# ADR-012: frozen original-patient groups and explicit role assignments

COS-024, 2026-10-27. Engineering fixture verification; D05 real evaluation stays open.

Confirmed current same-person assertions join opaque patient IDs across releases.
All exams, clinical records, processed inputs and synthetic descendants inherit the
original patient group. Similar dates/demographics never merge people. Exact imaging
byte hashes flag duplicate review, not patient identity. Uncertain equivalence and
duplicate evidence exclude clean held-out claims. Source mappings remain encrypted.

An administrator explicitly assigns train, validation, test, demo or unassigned roles.
Confirmed group members cannot have contradictory roles. A group closure includes
reviewed source aliases even when only one member is selected. Demo exposure is
recorded separately and excludes independent claims. No universal percentage split
is imposed. Seed determines reproducible group ordering; it does not invent ratios.

Frozen manifests contain group membership, identity evidence, source versions,
patient revisions and root resource IDs. New derived resources inherit the patient
assignment, but a learned fit may only use train resources descended from roots in
that frozen manifest. New source roots cannot silently enter an old fit. Grouping
changes block fit access until a new reviewed version exists. Validation/test/demo
roles cannot enter learned preprocessing fits. No actual trained model is implemented.

Current identity/duplicate evidence is audited against frozen grouping. Later cross-role
confirmation reports the actual merged-group overlap and invalidates eligibility;
it never rewrites old assignments. Audit evidence appends. Synthetic results cannot
be independent observed test outcomes. Real evaluation clearance is explicitly false
until D05 source/reference review exists; engineering group checks cannot override it.

Actual project-scoped handlers create/read splits and read/record leakage audits;
full manifests are administrator only. Patient assignment reads require patient
authorization. POST split creation uses atomic Idempotency-Key replay. The clinical
HTTP fixture now exercises quality, lineage withdrawal and frozen split endpoints.

Evidence: evaluation-splits.json, clinical-fixture.json. Five partition tests cover
reproducibility, aliases, synthetic descendants, ambiguous identities, demo exposure,
new source roots, later cross-role contamination, ownership and duplicate-byte review.
Actual cohort overlap, independent annotation/model evaluation and qualified review
remain unverified. No performance metric or statistical power claim is made.
