"""Immutable capability-specific simulation eligibility audit results."""

from alembic import op

revision = "0033_simulation_eligibility"
down_revision = "0032_simulation_configs"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.simulation_eligibility_checks (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      config_id uuid NOT NULL, actor_id uuid NOT NULL REFERENCES access.users(id),
      report jsonb NOT NULL, report_hash text NOT NULL,
      UNIQUE(project_id,patient_id,id),
      FOREIGN KEY(project_id,patient_id,config_id) REFERENCES imaging.simulation_config_versions(project_id,patient_id,id))""")
    op.execute("""CREATE TRIGGER simulation_eligibility_checks_immutable BEFORE UPDATE OR DELETE
      ON imaging.simulation_eligibility_checks FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()""")


def downgrade():
    raise RuntimeError("Forward-only migration policy")
