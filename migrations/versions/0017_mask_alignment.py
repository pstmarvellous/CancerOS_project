"""Immutable mask alignment runs with private overlay assets."""

from alembic import op

revision = "0017_mask_alignment"
down_revision = "0016_preprocessing"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.alignment_runs (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 source_mask_id uuid NOT NULL, target_image_id uuid NOT NULL, output_artifact_id uuid,
 preview_artifact_id uuid, input_hash text NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,input_hash),
 FOREIGN KEY(project_id,patient_id,source_mask_id) REFERENCES ops.artifacts(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,target_image_id) REFERENCES ops.artifacts(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,output_artifact_id) REFERENCES ops.artifacts(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,preview_artifact_id) REFERENCES ops.artifacts(project_id,patient_id,id)
 )""")
    op.execute(
        "CREATE TRIGGER alignment_runs_immutable BEFORE UPDATE OR DELETE ON imaging.alignment_runs FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
