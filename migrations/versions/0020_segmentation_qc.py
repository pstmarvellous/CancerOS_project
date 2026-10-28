"""Append-only per-case segmentation QC attempts, including failures and exclusions."""

from alembic import op

revision = "0020_segmentation_qc"
down_revision = "0019_mask_study_binding"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.segmentation_qc_reports (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL, segmentation_id uuid NOT NULL,
 reference_segmentation_id uuid, actor_id uuid NOT NULL REFERENCES access.users(id), command_key text NOT NULL,
 input_hash text NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,actor_id,command_key),
 FOREIGN KEY(project_id,patient_id,segmentation_id) REFERENCES imaging.segmentations(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,reference_segmentation_id) REFERENCES imaging.segmentations(project_id,patient_id,id)
 )""")
    op.execute(
        "CREATE TRIGGER segmentation_qc_reports_immutable BEFORE UPDATE OR DELETE ON imaging.segmentation_qc_reports FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
