"""Immutable source-pinned preprocessing runs."""

from alembic import op

revision = "0016_preprocessing"
down_revision = "0015_canonical_volumes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.preprocess_runs (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 input_artifact_id uuid NOT NULL, output_artifact_id uuid, input_hash text NOT NULL,
 report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,input_hash),
 FOREIGN KEY(project_id,patient_id,input_artifact_id) REFERENCES ops.artifacts(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,output_artifact_id) REFERENCES ops.artifacts(project_id,patient_id,id)
 )""")
    op.execute(
        "CREATE TRIGGER preprocess_runs_immutable BEFORE UPDATE OR DELETE ON imaging.preprocess_runs FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
