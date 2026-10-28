"""Frozen patient-group manifests and append-only contamination audits."""

from alembic import op

revision = "0012_patient_splits"
down_revision = "0011_quality_reports"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE source.evaluation_splits (
 id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES access.projects(id),
 manifest jsonb NOT NULL, manifest_hash text NOT NULL,
 created_by uuid NOT NULL REFERENCES access.users(id), recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,id)
 )""")
    op.execute("""CREATE TABLE source.split_audits (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, split_id uuid NOT NULL,
 report jsonb NOT NULL, report_hash text NOT NULL, recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(project_id,split_id) REFERENCES source.evaluation_splits(project_id,id)
 )""")
    for table in ("evaluation_splits", "split_audits"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON source.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
