# Persistence foundation

COS-012. PostgreSQL15.4 native binaries were already installed. A separate owned
cluster in ignored .local/postgres listens only on 127.0.0.1:55432 with generated
private SCRAM credentials. Existing system service/databases are untouched. Migration
0001 uses access/source/clinical/ops schemas. An advisory lock serializes migration
launchers. Repeated upgrade is supported; destructive reset is not a startup action.

Implemented: projects, external user identities/memberships, patient ownership keys,
independent patient timeline origins, observed time references, append-only captured
revision manifests, engineering-only artifact metadata, digest jobs/attempts/outbox
and append-only audit. Composite FKs reject cross-patient/project links. Origins and
time references are immutable. Relative roots cannot form state cycles because they
reference independent origins, never snapshots. Future state anchors/branch time
exceptions need their own migrations and tests before enablement.

Revision N stores exact input membership/hash and remains readable after N+1.
Database triggers reject journal mutation; transaction rollback tests use artificial
records. This proves the foundation journal, not a complete clinical snapshot builder.

Private S3 adapter uses server-generated quarantine/verified keys, byte/size/hash
checks, explicit immutable object versions, bounded grants and project checks.
SeaweedFS4.51 is the selected local service after official MinIO Windows download
URLs returned HTTP410. Tests use actual signed HTTP operations, versioning, anonymous
denial and controlled grants; no patient objects are uploaded. Native startup may
need a warm allocation interval, so startup readiness must include an actual tiny
private write/read rather than port availability alone.

Deferred: protected source mappings/encryption-key rotation, full clinical subtypes,
imaging frames/lesions, simulation branches, snapshot membership, evidence/interpretation,
source rights approvals, production RLS/roles and domain publication workflows.
Do not publish real data through this foundation-only artifact schema. D01–D03 remain open.

```powershell
uv run python scripts/local_postgres.py
uv run alembic upgrade head
uv run python scripts/migrate_test.py
uv run pytest tests/test_persistence.py --tb=line
uv run python scripts/local_services.py start storage
uv run pytest tests/test_storage.py --tb=line
```

The disposable test database is explicitly named canceros_disposable_test. Tests
rollback their records; ordinary startup preserves all local service data. Downgrade
is forward-only by policy; no non-disposable database is reset or dropped.
