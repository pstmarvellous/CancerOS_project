"""Owned durable revision calculations, immutable reports and preview heads."""

from alembic import op

revision = "0038_dependent_updates"
down_revision = "0037_publication_scope"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE ops.dependent_update_requests (
 event_id uuid PRIMARY KEY REFERENCES ops.domain_outbox(id), project_id uuid NOT NULL, patient_id uuid NOT NULL,
 revision bigint NOT NULL, scope_key text NOT NULL, job_id uuid NOT NULL UNIQUE REFERENCES ops.jobs(id),
 request_hash text NOT NULL, receipt jsonb NOT NULL,
 FOREIGN KEY(project_id,patient_id,revision) REFERENCES source.patient_revisions(project_id,patient_id,revision),
 UNIQUE(project_id,patient_id,event_id), UNIQUE(project_id,patient_id,job_id)
 )""")
    op.execute("""CREATE TABLE ops.dependent_update_reports (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL, revision bigint NOT NULL,
 scope_key text NOT NULL, event_id uuid NOT NULL, job_id uuid NOT NULL,
 report jsonb NOT NULL, report_hash text NOT NULL, recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,scope_key,revision,id),
 FOREIGN KEY(project_id,patient_id,event_id) REFERENCES ops.dependent_update_requests(project_id,patient_id,event_id),
 FOREIGN KEY(project_id,patient_id,job_id) REFERENCES ops.dependent_update_requests(project_id,patient_id,job_id),
 FOREIGN KEY(project_id,patient_id,revision) REFERENCES source.patient_revisions(project_id,patient_id,revision)
 )""")
    op.execute("""CREATE TABLE ops.dependent_update_heads (
 project_id uuid NOT NULL, patient_id uuid NOT NULL, scope_key text NOT NULL, revision bigint NOT NULL, report_id uuid NOT NULL,
 PRIMARY KEY(project_id,patient_id,scope_key),
 FOREIGN KEY(project_id,patient_id,scope_key,revision,report_id) REFERENCES ops.dependent_update_reports(project_id,patient_id,scope_key,revision,id)
 )""")
    for table in ("dependent_update_requests", "dependent_update_reports"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON ops.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
