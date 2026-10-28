"""Revision- and mask-pinned immutable physical measurement reports."""

from alembic import op

revision = "0025_physical_measurements"
down_revision = "0024_lost_attempt_metrics"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.measurement_reports (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL, input_revision bigint NOT NULL,
 actor_id uuid NOT NULL REFERENCES access.users(id), command_key text NOT NULL,
 input_hash text NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,actor_id,command_key),
 FOREIGN KEY(project_id,patient_id,input_revision) REFERENCES source.patient_revisions(project_id,patient_id,revision)
 )""")
    op.execute(
        "CREATE TRIGGER measurement_reports_immutable BEFORE UPDATE OR DELETE ON imaging.measurement_reports FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
