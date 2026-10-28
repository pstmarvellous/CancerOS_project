# Bounded imaging import

Private synthetic engineering fixtures only. Start dependencies and apply migrations:

```powershell
uv run python scripts/dev.py start data
uv run python scripts/migrate_test.py
uv run python scripts/run_checks.py imaging-ingestion
```

The last command exercises actual disposable PostgreSQL and private versioned S3,
plus authenticated in-process HTTP. It is not an authentic case or deployed browser
test. All source identifiers/pixels in these tests are artificial.

API sequence (base `/api/v1/projects/{project_id}/patients/{patient_id}`):

1. Administrator registers an exact source-byte checksum under the authorized
   fixture release/component, with current internal-processing and derivative rights.
   Resolve a restricted patient mapping using the installed private linkage keyring.
2. `POST /imaging-files`: `source_version_id`, `mapping_id`, `format` (`dicom` or
   `nifti`), `sha256`, write-only `content_base64`. One file per call, no paths or
   archive extraction. Repeated identical deliveries return the same artifact ID.
3. `POST /imaging-import-previews`: `file_ids` and `association` containing
   `mapping_id`, opaque `study_id`/`series_id`, write-only `source_study_key` and
   `source_series_key`, controlled `sequence`, optional `fourth_axis:"dce_phase"`,
   `acquisition_time_status`, `association_basis:"administrator_manifest_attestation"`
   and the approved manifest's `evidence_sha256`. Supply actual authorized manifest
   evidence; do not treat an arbitrary hash as a privacy review.
4. Review returned patient label, study/series, sequence, dimensions and issue codes.
   Read the same report at `GET /imaging-imports/{id}` (also returned as Location).
5. `POST /imaging-imports/{id}/confirmations` confirms the reviewed association.
   The result is `staged_pending_geometry`, draft and scientific-review pending.

See `tests/test_imaging_ingestion.py` for executable artificial requests, including
RS256/SQL authentication. Do not paste protected bytes, source keys or tokens into
shell history, logs or committed examples. Parser/privacy details and supported
formats are in ADR-013 and COS-025-parser.md.

Unsupported compressed/enhanced multiframe DICOM, mixed series, missing/duplicate
physical positions, conflicting NIfTI q/s transforms, unknown units, corrupt/truncated
bytes and unspecified 4D axes quarantine. Source bytes remain privately staged for
repair/retry. Archives are rejected without extraction; no traversal is possible.
Use a supported individually staged source or a separately reviewed conversion;
do not strip headers or resize data to force acceptance. A corrected association
uses a new immutable preview. Existing accepted series cannot be silently rebound.

No ready/publish/share action exists. Real-source onboarding, large study streaming,
qualified review and eventual lawful cleanup of private orphaned writes remain open.
