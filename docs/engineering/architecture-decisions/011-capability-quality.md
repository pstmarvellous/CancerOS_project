# ADR-011: capability quality and append-only revalidation

COS-023, 2026-10-27; capability-quality/1. Engineering self-review only.

Report separate clinical display, physical measurement, anatomical mesh, genuine
temporal comparison and synthetic baseline requirements. Denominators count named
requirements, never patient health or a global trust score. Technical QC evidence,
current access, scientific review and publication stay distinct. Pending domain
validators/reviews cannot yield a ready medical capability from a running job.

Accepted clinical engineering records remain displayable with their own source
permissions even when an unrelated mask fails. Missing numeric results are counted
explicitly; exact zero is not missing. Quarantined source artifacts remain isolated,
with original row findings and private byte identity preserved. No override endpoint
can assert technical success or waive source/ownership/geometry integrity checks.

Owned validators can append versioned technical evidence. Quality snapshots bind
patient revision, current resource/validation IDs and current inherited restrictions.
Subsequent corrections, withdrawal/rights changes or new QC mark the old report stale;
the old report is not edited. Revalidation calls the actual source validator, appends
a new report and audit event, and never auto-accepts or publishes data. Fixing raw
content means a new staged artifact; original rejection evidence remains visible.

Actual patient-scoped handlers: POST/GET quality-reports and POST
quality-revalidations. The latter accepts the same pinned BatchCommand as validation.
Writes use Idempotency-Key; replay resolves the stored report ID and recomputes its
stale indicator under current authorization. Editor needs a patient grant; full
medical readiness remains blocked D01/D03 and later domain/review work.

Fixtures verify zero/missingness, bad-mask isolation, denied access, repeated
revalidation and stale evidence after a corrected source. API schema errors also
sanitize unexpected field names: attacker-supplied dictionary/extra keys can contain
protected identifiers, so only static schema field names/row indexes are echoed.
Evidence: quality.json and source-registry regression tests.
