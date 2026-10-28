"""Immutable administrator-attested mask/study/image binding before alignment."""

from alembic import op

revision = "0019_mask_study_binding"
down_revision = "0018_annotation_import"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE imaging.studies ADD CONSTRAINT study_patient_owned UNIQUE(project_id,patient_id,study_id)"
    )
    op.execute("""CREATE TABLE imaging.mask_associations (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 source_mask_id uuid NOT NULL, target_image_id uuid NOT NULL, study_id uuid NOT NULL,
 report jsonb NOT NULL, report_hash text NOT NULL,
 attested_by uuid NOT NULL REFERENCES access.users(id), recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,source_mask_id),
 FOREIGN KEY(project_id,patient_id,source_mask_id) REFERENCES ops.artifacts(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,target_image_id) REFERENCES ops.artifacts(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,study_id) REFERENCES imaging.studies(project_id,patient_id,study_id)
 )""")
    op.execute(
        "CREATE TRIGGER mask_associations_immutable BEFORE UPDATE OR DELETE ON imaging.mask_associations FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
