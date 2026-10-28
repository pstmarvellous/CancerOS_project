"""Bind imaging command receipts and job results to their patient's aggregate."""

from alembic import op

revision = "0023_imaging_job_ownership"
down_revision = "0022_imaging_storage"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE ops.jobs ADD CONSTRAINT job_patient_owned UNIQUE(project_id,patient_id,id)"
    )
    op.execute(
        "ALTER TABLE imaging.job_commands ADD CONSTRAINT imaging_command_job_owned FOREIGN KEY(project_id,patient_id,job_id) REFERENCES ops.jobs(project_id,patient_id,id)"
    )
    op.execute(
        "ALTER TABLE ops.jobs ADD CONSTRAINT job_result_patient_owned FOREIGN KEY(project_id,patient_id,result_artifact_id) REFERENCES ops.artifacts(project_id,patient_id,id)"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
