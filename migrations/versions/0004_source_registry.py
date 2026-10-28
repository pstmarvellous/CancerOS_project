"""Immutable source hierarchy and append-only action-specific rights attestations."""

from alembic import op

revision = "0004_source_registry"
down_revision = "0003_artifact_identity"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE source.registry_versions (
 id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES access.projects(id),
 record_key text NOT NULL, version integer NOT NULL CHECK(version>0),
 kind text NOT NULL CHECK(kind IN ('collection','release','component','artifact_source')),
 origin text NOT NULL CHECK(origin IN ('real_source','synthetic_engineering_fixture')),
 parent_version_id uuid, payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
 created_by uuid NOT NULL REFERENCES access.users(id), recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,id), UNIQUE(project_id,record_key,version),
 FOREIGN KEY(project_id,parent_version_id) REFERENCES source.registry_versions(project_id,id),
 CHECK((kind='collection')=(parent_version_id IS NULL))
 )""")
    op.execute("""CREATE TABLE source.rights_reviews (
 sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE, id uuid PRIMARY KEY,
 project_id uuid NOT NULL, source_version_id uuid NOT NULL,
 action text NOT NULL CHECK(action IN ('internal_processing','external_inference','derivative_creation','public_demo_redistribution')),
 decision text NOT NULL CHECK(decision IN ('allowed','denied','unknown')),
 basis text NOT NULL CHECK(basis IN ('documented_rights_review','engineering_fixture_example')),
 evidence_reference text NOT NULL CHECK(length(evidence_reference)>0),
 evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[0-9a-f]{64}$'),
 valid_until timestamptz NOT NULL, reviewed_by uuid NOT NULL REFERENCES access.users(id),
 reviewed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(project_id,source_version_id) REFERENCES source.registry_versions(project_id,id),
 CHECK(valid_until>reviewed_at)
 )""")
    for table in ("registry_versions", "rights_reviews"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON source.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )
    op.execute(
        "CREATE INDEX rights_latest ON source.rights_reviews(project_id,source_version_id,action,sequence DESC)"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
