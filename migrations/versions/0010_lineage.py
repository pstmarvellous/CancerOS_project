"""Immutable project/patient lineage graph with restricted withdrawal events."""

from alembic import op

revision = "0010_lineage"
down_revision = "0009_metadata_adapters"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE ops.resource_registry (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 kind text NOT NULL, content_hash text NOT NULL CHECK(content_hash ~ '^[0-9a-f]{64}$'),
 origin text NOT NULL CHECK(origin IN ('REAL_OBSERVED','REAL_DERIVED','SYNTHETIC_GENERATED','INTERPOLATED','MODEL_PREDICTED')),
 source_version_id uuid, manifest jsonb NOT NULL, manifest_hash text NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,source_version_id) REFERENCES source.registry_versions(project_id,id)
 )""")
    op.execute("""CREATE TABLE source.provenance_edges (
 project_id uuid NOT NULL, patient_id uuid NOT NULL, child_id uuid NOT NULL, parent_id uuid NOT NULL,
 relation text NOT NULL CHECK(relation IN ('derived_from','supersedes')),
 PRIMARY KEY(project_id,child_id,parent_id), CHECK(child_id<>parent_id),
 FOREIGN KEY(project_id,patient_id,child_id) REFERENCES ops.resource_registry(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,parent_id) REFERENCES ops.resource_registry(project_id,patient_id,id)
 )""")
    op.execute("""CREATE FUNCTION source.guard_lineage() RETURNS trigger LANGUAGE plpgsql AS $$
 BEGIN
 IF EXISTS(WITH RECURSIVE ancestors(id) AS (
 SELECT NEW.parent_id UNION SELECT e.parent_id FROM source.provenance_edges e JOIN ancestors a ON e.child_id=a.id WHERE e.project_id=NEW.project_id)
 SELECT 1 FROM ancestors WHERE id=NEW.child_id) THEN RAISE EXCEPTION 'LINEAGE_CYCLE'; END IF;
 RETURN NEW; END $$""")
    op.execute(
        "CREATE TRIGGER lineage_cycle BEFORE INSERT ON source.provenance_edges FOR EACH ROW EXECUTE FUNCTION source.guard_lineage()"
    )
    op.execute("""CREATE TABLE source.withdrawal_events (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL, resource_id uuid NOT NULL,
 reason_code text NOT NULL CHECK(reason_code IN ('rights_withdrawn','source_corrected','scientific_review','privacy_review')),
 actor_id uuid NOT NULL REFERENCES access.users(id), recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(project_id,patient_id,resource_id) REFERENCES ops.resource_registry(project_id,patient_id,id)
 )""")
    for schema, table in (
        ("ops", "resource_registry"),
        ("source", "provenance_edges"),
        ("source", "withdrawal_events"),
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {schema}.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
