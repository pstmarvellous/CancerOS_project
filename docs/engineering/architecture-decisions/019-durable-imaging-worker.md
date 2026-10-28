# ADR-019: fenced, private CPU imaging commands and owned fixture cleanup

COS-032, 2026-10-28. SPEC-007 worker boundaries, SPEC-008 13.4/15 and
SPEC-010/011 privacy/recovery govern this bounded extension of the existing worker.

Use existing PostgreSQL jobs/attempts/outbox and Redis transport. Imaging has a
separate kind/transport list; the digest dispatcher cannot consume it. One immutable
manifest freezes actor, patient revision, command, input IDs/hashes and code hash.
The worker checks current SQL membership, patient grant, source rights, input integrity
and code compatibility. It never reconstructs a prior job from current heads.
Original code/environment archives remain unavailable: incompatible code fails closed.

Supported actual operations are geometry, preprocessing, alignment and segmentation
QC. Global advisory locking limits imaging concurrency to one. A 150-second lease,
five-second heartbeat, token/expiry/cancellation fence and bounded three-attempt
transient retries with exponential backoff/jitter protect finalization. Validation
failures are terminal. Progress names completed stages; no percentage is invented.
Final result references, stage rows and job status commit in one SQL transaction.
The result report inherits actual output resources, so their withdrawal propagates.
Late attempts append diagnostics without changing another lease's status. Lost-worker
measurements are null. Durable SQL recovery repairs expired/lost transport delivery.

workers/imaging.py runs one supervised child per invocation, discarding arbitrary
child stdout/stderr. A 120-second wall deadline and sampled 512-MiB RSS threshold
terminate only the owned child. This is sampled enforcement, not an OS memory
reservation or guaranteed instantaneous peak bound. Parsers also bound input sizes.
Actual small fixture metrics are in imaging-worker-measurement.json; they are not
large-study performance or clinical validation. Killed stages roll back SQL; private
objects may remain until conservative cleanup.

Object writes and SQL are not atomic. Only explicitly tagged engineering fixture
versions older than seven days may enter bounded cleanup: at most 128 scanned and
32 candidates. Referenced, untagged, foreign-project and fresh versions are retained.
Queued/running jobs block cleanup. A committed immutable reservation precedes deletion
and an artifact-insert trigger prevents references to reserved versions, including
after S3 deletion followed by SQL rollback. Apply rechecks ownership, version/hash,
age and references under NOWAIT table locks, deletes exact versions and retains
retry outcomes. No cleanup of existing user data was run; tests delete their own
new artificial objects with an explicitly advanced internal test clock.

Restricted-review grants recheck patient edit authority, source restrictions, immutable
bytes and availability. Original source images additionally require project admin.
Derived imaging is allowlisted; clinical/source-note assets are excluded. URLs expire
within 120 seconds, appear only in the response, and are never persisted/logged.
They can remain usable until expiry after withdrawal; immediate revocation is not
claimed. No viewer original-DICOM permission or external inference permission follows.

A successful worker stores a private technical result with publication draft,
scientific review pending and publication_allowed false. Explicit publication remains
blocked by missing qualified review/state publication policy; no placeholder working
publish action or public project publication was introduced. This mandatory positive
publication check is not reported as passed. Continue independent COS-033 work.

Contracts: ImagingJobInput/Record, AssetGrant and CleanupReport; project/patient HTTP
routes and generated clients. Migrations 0021–0024 add command/result/evidence/grant/
cleanup records and composite job ownership. Evidence: imaging-worker.json. Review
was engineering self-review and actual AI code review, not qualified scientific review.
