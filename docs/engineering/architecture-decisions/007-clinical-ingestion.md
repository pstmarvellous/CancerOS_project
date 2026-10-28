# ADR-007: staged source-backed clinical ingestion

COS-019/020, 2026-10-27. Engineering self-review; no qualified clinical review.

The current executable source format is `clinical-source/1`: private JSON with an
explicit SYNTHETIC_ENGINEERING_FIXTURE label and at most 100 records. An administrator
stages bytes after project/patient/mapping/release/rights and SHA-256 checks. Both
registry artifact-source hash and supplied hash must match. Private S3 immutable
versions retain the exact bytes; server-owned JSON row locators retain record hashes.
All examples and accepted outputs remain synthetic; **real-source upload is disabled**
pending D01/D03 privacy/linkage onboarding. No real cohort adapter is implied.

Canonical patient-scoped routes provide timeline-origin creation, source staging,
validate-first batches, acceptance, exact observation reads and explicit retraction.
Source locators and provenance are server-derived, not arbitrary editor claims.
Source status, technical validation, scientific review and publication are separate.
Known private source-note references have a contract but no validated text adapter:
such rows are quarantined. This is an explicit partial-domain limitation.

Batch policy: all-or-none for errors; preserve every raw input and row-specific repair
report. Warnings remain visible and do not imply contraindication. Source JSON cannot
override a server locator; unknown time/term/unit stays unavailable or quarantined.
Relative day zero references an owned persisted origin. State-anchor imports remain
disabled until authoritative state resolution exists in COS-039.

Acceptance locks the patient revision. Idempotency key + request fingerprint replay
the exact existing result after rechecking patient access and current source rights.
Changed input with a reused key returns 409. Corrections require the current head,
one source-backed row and expected revision. Observations, typed subtype rows, immutable
input manifest, revision increment, audit and durable domain outbox commit together.
Retractions append and remove current membership; old revisions still bind exact IDs.
No auto-publication, imputation or fabricated treatment delivery occurs.

Relational subtype tables and deferred kind checks supplement the canonical serialized
payload and content hash. The bounded `visit` subtype is an implementation extension
for source occasions; DCE phases are not represented as visits. A later broader source
adapter must reconcile unsupported outcomes/notes under SPEC-008 before enablement.
Private objects written before a failed DB transaction can be orphaned; they remain
private and require a retention-reviewed cleanup job, not unsafe deletion on retry.

Evidence: clinical-ingestion.json, clinical-fixture.json, focused rollback/concurrency
tests. The runnable HTTP harness uses real disposable PostgreSQL/private S3 and
ephemeral test identities in-process. It is not a deployed browser or real-data test.
