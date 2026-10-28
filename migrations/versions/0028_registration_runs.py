"""Immutable patient/revision-owned fixture registration records."""

from alembic import op

revision = "0028_registration_runs"
down_revision = "0027_mesh_quality"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.registration_runs (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 actor_id uuid NOT NULL REFERENCES access.users(id), command_key text NOT NULL,
 input_hash text NOT NULL, input_revision bigint NOT NULL,
 fixed_image_id uuid NOT NULL, moving_image_id uuid NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,actor_id,command_key),
 FOREIGN KEY(project_id,patient_id,input_revision) REFERENCES source.patient_revisions(project_id,patient_id,revision),
 FOREIGN KEY(project_id,patient_id,fixed_image_id) REFERENCES ops.artifacts(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,moving_image_id) REFERENCES ops.artifacts(project_id,patient_id,id)
 )""")
    op.execute(
        "CREATE TRIGGER registration_runs_immutable BEFORE UPDATE OR DELETE ON imaging.registration_runs FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
