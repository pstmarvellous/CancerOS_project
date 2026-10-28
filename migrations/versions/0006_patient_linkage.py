"""Restricted encrypted linkage, patient grants and append-only correspondence review."""

from alembic import op

revision = "0006_patient_linkage"
down_revision = "0005_registry_commands"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE access.patient_grants (
 project_id uuid NOT NULL, patient_id uuid NOT NULL, user_id uuid NOT NULL,
 permission text NOT NULL CHECK(permission IN ('view','edit')),
 PRIMARY KEY(project_id,patient_id,user_id),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,user_id) REFERENCES access.memberships(project_id,user_id)
 )""")
    op.execute("""CREATE TABLE source.patient_mappings (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 release_version_id uuid NOT NULL, source_version_id uuid NOT NULL,
 recorded_by uuid NOT NULL REFERENCES access.users(id), recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,id), UNIQUE(project_id,release_version_id,id),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,release_version_id) REFERENCES source.registry_versions(project_id,id),
 FOREIGN KEY(project_id,source_version_id) REFERENCES source.registry_versions(project_id,id)
 )""")
    op.execute("""CREATE TABLE source.mapping_secrets (
 project_id uuid NOT NULL, release_version_id uuid NOT NULL, mapping_id uuid NOT NULL,
 key_version text NOT NULL, lookup_digest text NOT NULL CHECK(lookup_digest ~ '^[0-9a-f]{64}$'),
 nonce bytea NOT NULL CHECK(octet_length(nonce)=12), ciphertext bytea NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(project_id,mapping_id,key_version),
 UNIQUE(project_id,release_version_id,key_version,lookup_digest),
 FOREIGN KEY(project_id,release_version_id,mapping_id) REFERENCES source.patient_mappings(project_id,release_version_id,id)
 )""")
    op.execute("""CREATE TABLE source.person_link_events (
 sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE, id uuid PRIMARY KEY,
 project_id uuid NOT NULL, left_patient_id uuid NOT NULL, right_patient_id uuid NOT NULL,
 supersedes_id uuid UNIQUE, status text NOT NULL CHECK(status IN ('uncertain','confirmed','rejected','withdrawn')),
 confidence numeric(10,9) NOT NULL CHECK(confidence BETWEEN 0 AND 1 AND confidence::text<>'NaN'),
 evidence_reference text NOT NULL, evidence_sha256 text NOT NULL CHECK(evidence_sha256 ~ '^[0-9a-f]{64}$'),
 reviewed_by uuid NOT NULL REFERENCES access.users(id), reviewed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,id), CHECK(left_patient_id<>right_patient_id),
 FOREIGN KEY(project_id,left_patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,right_patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,supersedes_id) REFERENCES source.person_link_events(project_id,id)
 )""")
    for table in ("patient_mappings", "mapping_secrets", "person_link_events"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON source.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
