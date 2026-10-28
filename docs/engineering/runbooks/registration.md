# Fixture rigid registration

No genuine two-exam pair is approved; D02 is blocked. Do not present engineering
relative days, landmarks, numerical residuals or a frame UID as anatomical review.

An administrator may enqueue the existing imaging worker operation `registration`
with expected_revision and RegistrationInput. Use owned distinct study image UUIDs,
same known sequence, strictly later engineering moving day, evidence SHA256,
four noncoplanar paired fit landmarks inside the declared images and separate
held-out pairs. Both coordinate sets use physical RAS/mm. If a moving annotation is
selected, supply its exact current moving_qc_report_id; either both IDs or neither.
No new source upload, network inference or real-source permission is introduced.

POST `/api/v1/projects/{project}/patients/{patient}/imaging-jobs`, authenticated with
Idempotency-Key. Command envelope is `{"operation":"registration","input":...}`.
Poll job Location; GET `/registrations/{result_report_id}` in the same patient
scope returns transform/inverse, numerical fit/holdout metrics, bounds guard and
pending-review status. Canonical OpenAPI defines exact fields and limits.

Success is fixture_aligned_pending_review, genuine_exam_pair_verified=false,
overlay_allowed=false. Failed fitting/bounds/mask clipping produces blocked report
or terminal input failure and keeps original scalar history. A new QC attempt after
enqueue makes an old pin stale; inspect/review current evidence and enqueue a new
command. Do not silently swap inputs on retry. Wrong ownership denies reads.

`uv run python scripts/run_checks.py registration` executes pure and actual private
SQL/S3/Redis/HTTP fixtures. Real acceptance needs data-steward evidence of source
rights, reviewed same-person identity, genuine distinct exams/times and appropriate
anatomical overlay review. Use original side-by-side views until that evidence exists;
scalar comparison additionally requires reviewed lesion identity and metric meaning.
