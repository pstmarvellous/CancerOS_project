"""Enforce complete-manifest publication and current-pointer scope in PostgreSQL."""

from alembic import op

revision = "0037_publication_scope"
down_revision = "0036_complete_simulation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""ALTER TABLE imaging.simulation_completions ADD CONSTRAINT completion_run_identity
      UNIQUE(project_id,patient_id,branch_id,run_id,id)""")
    op.execute("""ALTER TABLE imaging.simulation_publications ADD CONSTRAINT publication_completion_scope
      FOREIGN KEY(project_id,patient_id,branch_id,run_id,completion_id)
      REFERENCES imaging.simulation_completions(project_id,patient_id,branch_id,run_id,id),
      ADD CONSTRAINT publication_run_identity UNIQUE(project_id,patient_id,branch_id,run_id,id)""")
    op.execute("""ALTER TABLE imaging.simulation_current_runs ADD CONSTRAINT current_publication_scope
      FOREIGN KEY(project_id,patient_id,branch_id,run_id,publication_id)
      REFERENCES imaging.simulation_publications(project_id,patient_id,branch_id,run_id,id)""")


def downgrade():
    raise RuntimeError("Forward-only migration policy")
