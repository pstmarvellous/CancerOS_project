"""Immutable capability evidence and explicit revalidation snapshots."""

from alembic import op

revision = "0011_quality_reports"
down_revision = "0010_lineage"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE source.technical_validations (
 sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE, id uuid PRIMARY KEY,
 project_id uuid NOT NULL, patient_id uuid NOT NULL, resource_id uuid NOT NULL,
 status text NOT NULL CHECK(status IN ('pending','pass','warning','fail')),
 rule_version text NOT NULL, checks jsonb NOT NULL, checks_hash text NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(project_id,patient_id,resource_id) REFERENCES ops.resource_registry(project_id,patient_id,id)
 )""")
    op.execute("""CREATE TABLE source.quality_reports (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 revision bigint NOT NULL, input_hash text NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
 recorded_by uuid NOT NULL REFERENCES access.users(id), recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 FOREIGN KEY(project_id,patient_id,revision) REFERENCES source.patient_revisions(project_id,patient_id,revision)
 )""")
    for table in ("technical_validations", "quality_reports"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON source.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
