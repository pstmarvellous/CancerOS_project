# ADR-054: simulation closure with discovery reads and existing lifecycle

COS-068 implements SPEC-008 scenario/branch/run/publication routes and
SPEC-004 over the existing five-family engine, eligibility, job/outbox and
publication services. No simulation logic is duplicated and no destructive
branch endpoints are introduced. Two discovery reads compose owned stores:
static five-family scenario discovery with versioned definitions and
synthetic-only labels, and branch listing from immutable twin reports with
baseline hash, mode and verification state. Both re-authorize the patient.

Creation, submission, completion and publication keep their existing
transactional semantics: draft branches may exist while insufficient,
generation stays blocked until source-supported evidence exists, runs freeze
inputs and enqueue through jobs/outbox, idempotent submission returns the
same job, viewers see only publication-eligible content, If-Match guards the
branch pointer, and job success alone cannot publish. Cancellation, retry
and validation failures use canonical job/resource commands. Cross-branch
report IDs, stale baselines and concurrent publications fail closed through
existing guards; generated descendants retain synthetic provenance.
Fixture denominators cover family discovery, branch ownership isolation and
HTTP boundaries — engine correctness stays with the Phase 3 suites and
genuine review remains open.
