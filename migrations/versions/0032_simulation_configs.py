"""Versioned simulation drafts and immutable queued run snapshots on existing branches."""

from alembic import op

revision = "0032_simulation_configs"
down_revision = "0031_synthetic_geometry"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("simulation_config_versions", "simulation_runs"):
        extra = (
            ", draft_revision bigint NOT NULL CHECK(draft_revision>0), UNIQUE(project_id,patient_id,branch_id,draft_revision)"
            if table == "simulation_config_versions"
            else ", config_id uuid NOT NULL, input_revision bigint NOT NULL, input_manifest jsonb NOT NULL, input_manifest_hash text NOT NULL, FOREIGN KEY(project_id,patient_id,config_id) REFERENCES imaging.simulation_config_versions(project_id,patient_id,id), FOREIGN KEY(project_id,patient_id,input_revision) REFERENCES source.patient_revisions(project_id,patient_id,revision)"
        )
        op.execute(f"""CREATE TABLE imaging.{table} (
          id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
          branch_id uuid NOT NULL, actor_id uuid NOT NULL REFERENCES access.users(id),
          command_key text NOT NULL, input_hash text NOT NULL,
          report jsonb NOT NULL, report_hash text NOT NULL,
          UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,actor_id,command_key),
          FOREIGN KEY(project_id,patient_id,branch_id) REFERENCES imaging.twin_branches(project_id,patient_id,id)
          {extra})""")
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON imaging.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
