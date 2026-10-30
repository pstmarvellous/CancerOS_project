"""Immutable private note versions and unpromoted extracted assertions."""

from alembic import op

revision = "0041_note_extraction"
down_revision = "0040_dependent_update_scopes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS intelligence")
    op.execute("""CREATE TABLE intelligence.note_documents (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      artifact_id uuid NOT NULL, branch_id uuid, version integer NOT NULL CHECK(version>0),
      supersedes_id uuid, payload jsonb NOT NULL, content_hash text NOT NULL,
      UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,branch_id,id),
      FOREIGN KEY(project_id,patient_id,artifact_id) REFERENCES ops.artifacts(project_id,patient_id,id),
      FOREIGN KEY(project_id,patient_id,branch_id) REFERENCES imaging.twin_branches(project_id,patient_id,id),
      FOREIGN KEY(project_id,patient_id,supersedes_id) REFERENCES intelligence.note_documents(project_id,patient_id,id),
      FOREIGN KEY(project_id,patient_id,id) REFERENCES ops.resource_registry(project_id,patient_id,id)
        DEFERRABLE INITIALLY DEFERRED)""")
    op.execute("""CREATE TABLE intelligence.note_extractions (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      note_id uuid NOT NULL, report jsonb NOT NULL, content_hash text NOT NULL,
      UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,note_id,content_hash),
      FOREIGN KEY(project_id,patient_id,note_id) REFERENCES intelligence.note_documents(project_id,patient_id,id),
      FOREIGN KEY(project_id,patient_id,id) REFERENCES ops.resource_registry(project_id,patient_id,id)
        DEFERRABLE INITIALLY DEFERRED)""")
    for table in ("note_documents", "note_extractions"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON intelligence.{table} "
            "FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
