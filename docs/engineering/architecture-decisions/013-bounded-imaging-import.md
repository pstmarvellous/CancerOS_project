# ADR-013: private, bounded imaging import and explicit associations

COS-025, 2026-10-28. SPEC-003 4.5/5, SPEC-005 IMG-001–008,
SPEC-008 owned contracts and SPEC-010 privacy govern this extension.

Stage immutable, hash-verified individual files through project/patient/admin
authorization, pinned source rights and the release-scoped encrypted patient mapping.
No archive is unpacked, no URL is fetched, and original bytes remain unchanged.
Real-source ingestion remains disabled pending D01/D03 rights/privacy/linkage review.
An engineering fixture rights assertion cannot open that gate.

An explicit administrator association manifest supplies opaque study/series IDs,
source keys (write-only), sequence, acquisition-time availability and evidence hash.
The attestation is recorded, not described as independent scientific approval.
DICOM PatientID must match the decrypted restricted mapping, with empty issuer in
this first supported scope. Study/series UIDs must match the manifest. NIfTI needs
the same explicit manifest; the parser never guesses patient/examination from a name.
4D is supported only as explicitly declared DCE phases within one study.

Preview shows a research patient label, opaque study/series IDs, controlled sequence,
dimensions and next action. A separate idempotent confirmation records the actor
and leaves geometry, annotation, scientific and sharing review pending. No image
bytes, source UIDs, acquisition dates, header strings or object locations appear in
normal responses/logs. Burned-in identifiers cannot be excluded even when a source
tag says NO. This is not a DICOM de-identifier or a publication mechanism.

Use maintained pydicom 3.0.2 and NiBabel 5.4.2 readers with NumPy 2.4.6, pinned
in uv.lock. Narrow preflight rejects unsupported compressed/multiframe/nested DICOM
and NIfTI extensions before potentially expensive decode. Physical geometry sorts
slices. Parser limits are 8 MiB/file, 32 MiB decoded/series, 2 million voxels,
256 slices and 16 DCE phases; API staging is further bounded to 900,000 base64
characters and configured storage cap (default 1 MiB). These are engineering bounds,
not a full clinical study uploader. Streaming larger studies is not implemented.

Retries use source hashes and a command fingerprint, including retained linkage-key
versions. Original reports are immutable; confirmation is an append-only event.
Patient and study locks serialize association changes. Composite foreign keys bind
mapping, private artifact, import, study and confirmation to the same patient.
Current source rights and ancestor withdrawals are checked again before confirmation
or processing, including replay. History remains readable after withdrawal.

Self-review and a separate AI agent code review found/fixed key-rotation replay,
cross-patient study races, missing composite ownership FKs and upstream warning-log
leakage. This is engineering review, not qualified radiology/privacy approval.

Evidence: imaging-ingestion.json; parser and SQL/S3/HTTP fixture tests. Authentic
case accuracy, large-study performance, de-identification, complete frontend and
external scientific review remain unverified. COS-026 owns canonical geometry QC.
