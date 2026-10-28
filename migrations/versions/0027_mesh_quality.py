"""Immutable owned mesh quality reports and private LOD selection."""

from alembic import op

revision = "0027_mesh_quality"
down_revision = "0026_mesh_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.mesh_qc_reports (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 actor_id uuid NOT NULL REFERENCES access.users(id), command_key text NOT NULL,
 input_hash text NOT NULL, mesh_run_id uuid NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,actor_id,command_key),
 FOREIGN KEY(project_id,patient_id,mesh_run_id) REFERENCES imaging.mesh_runs(project_id,patient_id,id)
 )""")
    op.execute(
        "CREATE TRIGGER mesh_qc_immutable BEFORE UPDATE OR DELETE ON imaging.mesh_qc_reports FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
