"""Immutable generated clinical batches separate from source clinical history."""

from alembic import op

revision = "0035_generated_clinical"
down_revision = "0034_common_geometry_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""ALTER TABLE imaging.simulation_runs ADD CONSTRAINT simulation_run_branch_identity
      UNIQUE(project_id,patient_id,branch_id,id)""")
    op.execute("""CREATE TABLE imaging.generated_clinical_batches (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      branch_id uuid NOT NULL, run_id uuid NOT NULL, actor_id uuid NOT NULL REFERENCES access.users(id),
      command_key text NOT NULL, input_hash text NOT NULL,
      report jsonb NOT NULL, report_hash text NOT NULL,
      UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,run_id),
      UNIQUE(project_id,patient_id,actor_id,command_key),
      FOREIGN KEY(project_id,patient_id,branch_id) REFERENCES imaging.twin_branches(project_id,patient_id,id),
      FOREIGN KEY(project_id,patient_id,branch_id,run_id) REFERENCES imaging.simulation_runs(project_id,patient_id,branch_id,id))""")
    op.execute("""CREATE TRIGGER generated_clinical_batches_immutable BEFORE UPDATE OR DELETE
      ON imaging.generated_clinical_batches FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()""")


def downgrade():
    raise RuntimeError("Forward-only migration policy")
