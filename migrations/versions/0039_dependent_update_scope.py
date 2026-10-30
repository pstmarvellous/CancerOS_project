"""Bind event, job, revision and report identities together at the SQL boundary."""

from alembic import op

revision = "0039_dependent_update_scope"
down_revision = "0038_dependent_updates"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE ops.domain_outbox ADD CONSTRAINT domain_event_owned_revision UNIQUE(project_id,patient_id,revision,id)"
    )
    op.execute(
        "ALTER TABLE ops.dependent_update_requests ADD CONSTRAINT update_request_event_scope FOREIGN KEY(project_id,patient_id,revision,event_id) REFERENCES ops.domain_outbox(project_id,patient_id,revision,id)"
    )
    op.execute(
        "ALTER TABLE ops.dependent_update_requests ADD CONSTRAINT update_request_execution UNIQUE(project_id,patient_id,revision,scope_key,event_id,job_id)"
    )
    op.execute(
        "ALTER TABLE ops.dependent_update_reports ADD CONSTRAINT update_report_execution_scope FOREIGN KEY(project_id,patient_id,revision,scope_key,event_id,job_id) REFERENCES ops.dependent_update_requests(project_id,patient_id,revision,scope_key,event_id,job_id)"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
