"""Immutable annotation classification and per-label segmentation objects."""

from alembic import op

revision = "0018_annotation_import"
down_revision = "0017_mask_alignment"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.annotation_batches (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 alignment_run_id uuid NOT NULL, input_hash text NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,input_hash),
 FOREIGN KEY(project_id,patient_id,alignment_run_id) REFERENCES imaging.alignment_runs(project_id,patient_id,id)
 )""")
    op.execute("""CREATE TABLE imaging.segmentations (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 batch_id uuid NOT NULL, label_value integer NOT NULL CHECK(label_value BETWEEN 1 AND 65535),
 mask_artifact_id uuid NOT NULL, metadata jsonb NOT NULL, metadata_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,batch_id,label_value),
 FOREIGN KEY(project_id,patient_id,batch_id) REFERENCES imaging.annotation_batches(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,mask_artifact_id) REFERENCES ops.artifacts(project_id,patient_id,id)
 )""")
    for table in ("annotation_batches", "segmentations"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON imaging.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
