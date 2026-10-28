# Curated engineering lesion tracking

Use an authorized administrator in the owned project/patient. All enabled records
remain synthetic engineering fixtures and scientific review pending.

1. POST `/api/v1/projects/{project}/patients/{patient}/lesions` with baseline segmentation
   UUID, evidence_sha256, expected_revision and an Idempotency-Key. GET its Location
   reads the stable identity. It is separate from source annotation label/UUID.
2. POST `/lesion-associations` in the same scope with lesion_id, segmentation_id,
   optional single-annotation measurement_id, status/relation, explicit simulation
   time, evidence_sha256 and expected_revision. Relative days require an owned
   simulation timeline_origin_id; unknown time uses an explicit missing reason.
   Split/merge relations require related_lesion_ids. A correction supplies the exact
   latest supersedes_event_id; it appends history. GET Location reads that event.
3. POST `/measurement-series` with lesion_id and expected_revision; GET Location
   returns the immutable report plus current stale/restrictions view. Lists are
   available at `/lesions` and `/lesion-associations`.

Unknown identity/time/measurements and split/merge uncertainty remain gaps. Incompatible
classes/methods, same-exam phases or different time groups cannot form eligible changes.
Review the source or append a corrected mapping; never fill missing values/dates.
After a correction, create a new series key rather than expecting old numbers to
change. Withdrawing source/QC blocks downstream use while metadata history remains.
No anatomical overlay, public demo or clinical response is authorized by a match.

`uv run python scripts/run_checks.py lesion-tracking` executes Decimal cases and
actual disposable PostgreSQL/private S3/HTTP ownership/history tests. Start owned
data services first after a pause. D02 needs genuine examinations/times and qualified
identity review; these fixture checks cannot close that dependency.
