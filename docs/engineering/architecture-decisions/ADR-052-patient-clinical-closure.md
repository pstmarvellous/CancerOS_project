# ADR-052: patient/clinical API closure over existing services

COS-066 implements SPEC-008 sections 6/11–13 and audit C01–C05 decisions over
the existing clinical ingestion, linkage, outbox and generated-client stack.
No parallel diagnosis store, no uncontrolled CRUD, no new persistence and no
second endpoint catalog are introduced. The five new reads compose owned
services: grant-scoped patient enumeration, patient detail with observation
and visit counts, visit grouping, filtered observation summaries with signed
snapshot cursors, and source-backed diagnosis confirmation.

Patient listing reuses the grant boundary: admins enumerate project patients,
others see only granted patients; display codes and revision counters are
the only exposed identity. Detail, visit and observation reads re-authorize
the patient and return original/canonical units, qualifiers, provenance,
missingness and revision without protected linkage fields. Observation
summaries carry source hashes and superseded flags; the cursor binds patient,
filter and result IDs so later pages cannot silently shift. Diagnosis
confirmation re-reads the exact record and accepts only kind=diagnosis —
changing observation kind remains new-record plus retraction.

Batches, corrections, retractions and revisions keep their validated
transactional semantics: all bundle entries validate or none commit, 100
entries and 1 MiB bounds hold, client fields cannot select ownership or
status, and dependent updates flow through the same outbox. Regenerated
OpenAPI, schemas and TypeScript clients expose only implemented runtime
routes. Fixture denominators cover grant isolation, cursor stability,
diagnosis kind gating and HTTP boundaries; they are not clinical validation
or a coverage claim for COS-071.
