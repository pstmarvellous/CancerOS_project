"""Durable imaging command receipts, retry scheduling and immutable attempt evidence."""

from alembic import op

revision = "0021_imaging_jobs"
down_revision = "0020_segmentation_qc"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE ops.jobs DROP CONSTRAINT jobs_kind_check")
    op.execute(
        "ALTER TABLE ops.jobs ADD CONSTRAINT jobs_kind_check CHECK(kind IN ('engineering.digest','imaging.pipeline/1'))"
    )
    op.execute(
        "ALTER TABLE ops.jobs ADD COLUMN next_attempt_at timestamptz NOT NULL DEFAULT clock_timestamp()"
    )
    op.execute("ALTER TABLE ops.jobs ADD COLUMN error_code text")
    op.execute("""CREATE TABLE imaging.job_commands (
 job_id uuid PRIMARY KEY REFERENCES ops.jobs(id), project_id uuid NOT NULL, patient_id uuid NOT NULL,
 actor_id uuid NOT NULL REFERENCES access.users(id), command_key text NOT NULL CHECK(length(command_key) BETWEEN 1 AND 128),
 request_hash text NOT NULL, UNIQUE(project_id,patient_id,actor_id,command_key),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id)
 )""")
    op.execute("""CREATE TABLE imaging.job_results (
 job_id uuid PRIMARY KEY REFERENCES ops.jobs(id), result jsonb NOT NULL, result_hash text NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp()
 )""")
    op.execute("""CREATE TABLE imaging.job_attempt_evidence (
 job_id uuid NOT NULL REFERENCES ops.jobs(id), attempt_number integer NOT NULL, lease_token uuid NOT NULL,
 outcome text NOT NULL, error_code text, wall_seconds double precision NOT NULL CHECK(wall_seconds>=0),
 rss_peak_bytes bigint NOT NULL CHECK(rss_peak_bytes>=0), recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(job_id,attempt_number), FOREIGN KEY(job_id,attempt_number) REFERENCES ops.job_attempts(job_id,attempt_number)
 )""")
    for table in ("job_commands", "job_results", "job_attempt_evidence"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON imaging.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )
    op.execute("""CREATE FUNCTION ops.protect_job_kind() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NEW.kind IS DISTINCT FROM OLD.kind THEN RAISE EXCEPTION 'IMMUTABLE_JOB_KIND'; END IF; RETURN NEW; END $$""")
    op.execute(
        "CREATE TRIGGER immutable_job_kind BEFORE UPDATE ON ops.jobs FOR EACH ROW EXECUTE FUNCTION ops.protect_job_kind()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
