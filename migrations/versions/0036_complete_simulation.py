"""Immutable run completions/publications and a guarded branch publication pointer."""

from alembic import op

revision = "0036_complete_simulation"
down_revision = "0035_generated_clinical"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("simulation_completions", "simulation_publications"):
        extra = (
            ""
            if table == "simulation_completions"
            else ", completion_id uuid NOT NULL, FOREIGN KEY(project_id,patient_id,completion_id) REFERENCES imaging.simulation_completions(project_id,patient_id,id)"
        )
        op.execute(f"""CREATE TABLE imaging.{table} (
          id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
          branch_id uuid NOT NULL, run_id uuid NOT NULL, actor_id uuid NOT NULL REFERENCES access.users(id),
          command_key text NOT NULL, input_hash text NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
          UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,actor_id,command_key),
          FOREIGN KEY(project_id,patient_id,branch_id,run_id) REFERENCES imaging.simulation_runs(project_id,patient_id,branch_id,id)
          {extra})""")
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON imaging.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )
    op.execute("""CREATE TABLE imaging.simulation_current_runs (
      project_id uuid NOT NULL, patient_id uuid NOT NULL, branch_id uuid NOT NULL,
      run_id uuid NOT NULL, publication_id uuid NOT NULL,
      PRIMARY KEY(project_id,patient_id,branch_id),
      FOREIGN KEY(project_id,patient_id,branch_id,run_id) REFERENCES imaging.simulation_runs(project_id,patient_id,branch_id,id),
      FOREIGN KEY(project_id,patient_id,publication_id) REFERENCES imaging.simulation_publications(project_id,patient_id,id))""")


def downgrade():
    raise RuntimeError("Forward-only migration policy")
