# Source registry runbook

Research engineering only. All included examples are synthetic and do not convey
rights to any clinical dataset. No approved real release has been established.

From the repository root:

```powershell
uv run python scripts/dev.py start foundation
uv run python scripts/migrate_test.py
uv run python scripts/run_checks.py source-registry
npm.cmd run contracts:generate
```

The check exercises real disposable PostgreSQL and authenticated HTTP requests
using generated ephemeral test keys. Expected: migrations repeat without reset;
10 registry tests pass. No patient files or remote cohort downloads are required.
For the local development DB, `uv run python -m alembic upgrade head` applies
forward migrations with the private `.env` configuration.

Authenticated API use requires a registered issuer/subject and database-backed
project membership. The API does not enroll accounts or mint production tokens.
POST `/api/v1/projects/{project_id}/sources` requires administrator role,
`Authorization: Bearer …`, JSON and a unique `Idempotency-Key`. Supply the
SourceVersionInput fields in generated OpenAPI. See `example()` in the registry
test for a complete conspicuously synthetic JSON object; create collection, release,
component then artifact source, using each returned immutable parent UUID.
GET the returned Location to retrieve that exact version. The token stays private.

POST `/{component_id}/rights-reviews` with action, decision, basis,
evidence_reference, SHA-256 and timezone-aware valid_until. Reviewer and review time
are server-derived. A fixture uses `engineering_fixture_example`; it cannot grant
real-data rights. Read `/{artifact_source_id}/capabilities/internal_processing` or
another SourceAction to obtain permitted, verification_scope, reason, attribution
and next_action. Unknown rights return permitted=false and Add current license
evidence… rather than an implied approval. Different action reviews are independent.
Retry the same command/key for the original result; changed input/key reuse is 409.

## Real release onboarding — blocked, not an approved import example

The named I-SPY2 source documentation could not be fetched during this task. No
release was downloaded, approved, de-identified or scientifically reviewed. D01/D03
remain open. A runnable **approved real-release** guide cannot truthfully be supplied
until the owner/data steward provides a selected release manifest, component terms,
attribution, intended-use review and privacy/linkage evidence.

Once available, register exact metadata/checksums without uploading patient content;
an authorized administrator records the actual review evidence for each component
and action. Availability alone never grants processing. Later imports must pin the
artifact-source UUID and call require_source_action; external transmission also
requires the separately gated destination policy. Carry attribution into descendants.

## Private patient linkage

Install `LINKAGE_KEYS` as private JSON mapping key-version names to base64-encoded
32 random bytes and `LINKAGE_ACTIVE_KEY` as an installed version. Use secure secret
injection; do not paste real keys into commands, examples or source control. Without
these settings GET `/api/v1/projects/{project_id}/patient-linkage/status` reports
disabled and a concrete key-install action.

An administrator can POST `/source-patient-resolutions` under that project with
`source_version_id` (permitted artifact-source UUID) and protected
`source_patient_key` in the HTTPS request body. The response contains only opaque
patient/mapping IDs, random display code, source badge and immutable release ID.
Repeated exact resolution returns the same result; whitespace ambiguity is rejected.
General mapping reads and key rotation are administrator only. No plaintext lookup
or bulk export endpoint exists. Add patient grants before editor/viewer workflows.

POST `/person-link-events` records distinct left/right patient IDs, status,
confidence, evidence reference/hash and optional supersedes_id. It requires
Idempotency-Key and administrator role. A conflicting stale predecessor is 409.
GET the returned Location for the immutable event. An uncertain link never merges
patients. Append withdrawn/rejected corrections to preserve history.

Run `uv run pytest tests/test_patient_linkage.py -q` after disposable migrations for
encryption, rotation, missing keys, concurrency, isolation and correction checks.
See ADR-005 for backup and key-rotation obligations before real use.
