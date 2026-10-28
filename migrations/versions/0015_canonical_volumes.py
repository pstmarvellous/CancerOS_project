"""Immutable canonical volumes and geometry validation results."""

from alembic import op

revision = "0015_canonical_volumes"
down_revision = "0014_imaging_ownership"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.volume_validations (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL, import_id uuid NOT NULL,
 artifact_id uuid, input_hash text NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,input_hash),
 FOREIGN KEY(project_id,patient_id,import_id) REFERENCES imaging.imports(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,artifact_id) REFERENCES ops.artifacts(project_id,patient_id,id)
 )""")
    op.execute(
        "CREATE TRIGGER volume_validations_immutable BEFORE UPDATE OR DELETE ON imaging.volume_validations FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
