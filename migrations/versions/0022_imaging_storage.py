"""Private bounded fixture cleanup reservations and grant audit; no URLs in SQL."""

from alembic import op

revision = "0022_imaging_storage"
down_revision = "0021_imaging_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.asset_grant_events (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      artifact_id uuid NOT NULL, actor_id uuid NOT NULL REFERENCES access.users(id),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp(), expires_at timestamptz NOT NULL,
      FOREIGN KEY(project_id,patient_id,artifact_id) REFERENCES ops.artifacts(project_id,patient_id,id))""")
    op.execute("""CREATE TABLE imaging.cleanup_plans (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      actor_id uuid NOT NULL REFERENCES access.users(id), created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      created_xid bigint NOT NULL DEFAULT txid_current(), expires_at timestamptz NOT NULL,
      FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id))""")
    op.execute("""CREATE TABLE imaging.cleanup_candidates (
      id uuid PRIMARY KEY, plan_id uuid NOT NULL REFERENCES imaging.cleanup_plans(id),
      object_key text NOT NULL, object_version text NOT NULL, sha256 text NOT NULL,
      UNIQUE(object_key,object_version))""")
    op.execute("""CREATE TABLE imaging.cleanup_outcomes (
      id uuid PRIMARY KEY, candidate_id uuid NOT NULL REFERENCES imaging.cleanup_candidates(id),
      actor_id uuid NOT NULL REFERENCES access.users(id), outcome text NOT NULL CHECK(outcome IN ('deleted','retained','retryable_failure')),
      created_at timestamptz NOT NULL DEFAULT clock_timestamp())""")
    for name in ("asset_grant_events", "cleanup_plans", "cleanup_candidates", "cleanup_outcomes"):
        op.execute(
            f"CREATE TRIGGER {name}_immutable BEFORE UPDATE OR DELETE ON imaging.{name} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )
    op.execute("""CREATE FUNCTION imaging.reject_reserved_artifact() RETURNS trigger LANGUAGE plpgsql AS $$
      BEGIN
      IF EXISTS(SELECT 1 FROM imaging.cleanup_candidates WHERE object_key=NEW.object_key AND object_version=NEW.object_version)
      THEN RAISE EXCEPTION 'OBJECT_VERSION_RESERVED_FOR_FIXTURE_CLEANUP'; END IF;
      RETURN NEW; END $$""")
    op.execute(
        "CREATE TRIGGER reject_reserved_artifact BEFORE INSERT ON ops.artifacts FOR EACH ROW EXECUTE FUNCTION imaging.reject_reserved_artifact()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
