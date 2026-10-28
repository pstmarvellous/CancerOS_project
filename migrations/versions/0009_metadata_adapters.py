"""Immutable adapter versions/results and exact raw/derived artifact association."""

from alembic import op

revision = "0009_metadata_adapters"
down_revision = "0008_source_intervals"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE source.adapter_runs (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 source_version_id uuid NOT NULL, input_artifact_id uuid NOT NULL, output_artifact_id uuid,
 input_hash text NOT NULL CHECK(input_hash ~ '^[0-9a-f]{64}$'), report jsonb NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,patient_id,input_hash),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,source_version_id) REFERENCES source.registry_versions(project_id,id),
 FOREIGN KEY(project_id,input_artifact_id) REFERENCES ops.artifacts(project_id,id),
 FOREIGN KEY(project_id,output_artifact_id) REFERENCES ops.artifacts(project_id,id)
 )""")
    op.execute(
        "CREATE TRIGGER adapter_runs_immutable BEFORE UPDATE OR DELETE ON source.adapter_runs FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
