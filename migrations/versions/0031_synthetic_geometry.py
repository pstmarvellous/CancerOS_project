"""Immutable isolated simulation run inputs, hypothetical geometry and state results."""

from alembic import op

revision = "0031_synthetic_geometry"
down_revision = "0030_twin_states"
branch_labels = None
depends_on = None


def upgrade():
    for table, extra in {
        "simulation_fixture_runs": ", branch_id uuid NOT NULL, FOREIGN KEY(project_id,patient_id,branch_id) REFERENCES imaging.twin_branches(project_id,patient_id,id)",
        "synthetic_geometries": ", run_id uuid NOT NULL, branch_id uuid NOT NULL, FOREIGN KEY(project_id,patient_id,run_id) REFERENCES imaging.simulation_fixture_runs(project_id,patient_id,id), FOREIGN KEY(project_id,patient_id,branch_id) REFERENCES imaging.twin_branches(project_id,patient_id,id)",
        "synthetic_geometry_results": ", geometry_id uuid NOT NULL, state_id uuid, FOREIGN KEY(project_id,patient_id,geometry_id) REFERENCES imaging.synthetic_geometries(project_id,patient_id,id), FOREIGN KEY(project_id,patient_id,state_id) REFERENCES imaging.twin_snapshots(project_id,patient_id,id)",
    }.items():
        op.execute(f"""CREATE TABLE imaging.{table} (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 actor_id uuid NOT NULL REFERENCES access.users(id), command_key text NOT NULL, input_hash text NOT NULL,
 report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,actor_id,command_key){extra})""")
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON imaging.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
