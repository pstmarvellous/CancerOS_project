"""Owned immutable reconstruction artifacts, not publication records."""

from alembic import op

revision = "0026_mesh_runs"
down_revision = "0025_physical_measurements"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.mesh_runs (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 actor_id uuid NOT NULL REFERENCES access.users(id), command_key text NOT NULL,
 input_hash text NOT NULL, measurement_id uuid NOT NULL, output_artifact_id uuid NOT NULL,
 report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,actor_id,command_key),
 FOREIGN KEY(project_id,patient_id,measurement_id) REFERENCES imaging.measurement_reports(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,output_artifact_id) REFERENCES ops.artifacts(project_id,patient_id,id)
 )""")
    op.execute(
        "CREATE TRIGGER mesh_runs_immutable BEFORE UPDATE OR DELETE ON imaging.mesh_runs FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
