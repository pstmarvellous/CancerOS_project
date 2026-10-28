"""Immutable revision-pinned engineering twin states and scoped cursor snapshots."""

from alembic import op

revision = "0030_twin_states"
down_revision = "0029_lesion_tracking"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("twin_branches", "twin_snapshots", "twin_reviews", "twin_publications"):
        extra = {
            "twin_branches": ", baseline_measurement_id uuid NOT NULL, baseline_hash text NOT NULL, timeline_origin_id uuid NOT NULL, time_domain text NOT NULL DEFAULT 'simulation' CHECK(time_domain='simulation'), FOREIGN KEY(project_id,patient_id,baseline_measurement_id) REFERENCES imaging.measurement_reports(project_id,patient_id,id), FOREIGN KEY(project_id,patient_id,timeline_origin_id,time_domain) REFERENCES source.timeline_origins(project_id,patient_id,id,time_domain)",
            "twin_snapshots": ", branch_id uuid NOT NULL, input_revision bigint NOT NULL, FOREIGN KEY(project_id,patient_id,branch_id) REFERENCES imaging.twin_branches(project_id,patient_id,id), FOREIGN KEY(project_id,patient_id,input_revision) REFERENCES source.patient_revisions(project_id,patient_id,revision)",
            "twin_reviews": ", snapshot_id uuid NOT NULL, sequence bigserial NOT NULL, FOREIGN KEY(project_id,patient_id,snapshot_id) REFERENCES imaging.twin_snapshots(project_id,patient_id,id)",
            "twin_publications": ", snapshot_id uuid NOT NULL UNIQUE, review_id uuid NOT NULL, FOREIGN KEY(project_id,patient_id,snapshot_id) REFERENCES imaging.twin_snapshots(project_id,patient_id,id), FOREIGN KEY(project_id,patient_id,review_id) REFERENCES imaging.twin_reviews(project_id,patient_id,id)",
        }[table]
        op.execute(f"""CREATE TABLE imaging.{table} (
          id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
          actor_id uuid NOT NULL REFERENCES access.users(id), command_key text NOT NULL,
          input_hash text NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
          UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,actor_id,command_key)
          {extra})""")
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON imaging.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )
    op.execute("""CREATE TABLE imaging.twin_members (
      project_id uuid NOT NULL, patient_id uuid NOT NULL, snapshot_id uuid NOT NULL, resource_id uuid NOT NULL,
      PRIMARY KEY(project_id,patient_id,snapshot_id,resource_id),
      FOREIGN KEY(project_id,patient_id,snapshot_id) REFERENCES imaging.twin_snapshots(project_id,patient_id,id),
      FOREIGN KEY(project_id,patient_id,resource_id) REFERENCES ops.resource_registry(project_id,patient_id,id))""")
    op.execute(
        "CREATE TRIGGER twin_members_immutable BEFORE UPDATE OR DELETE ON imaging.twin_members FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )
    op.execute("""CREATE TABLE imaging.twin_cursors (
      token_hash text PRIMARY KEY, scope_hash text NOT NULL, manifest jsonb NOT NULL,
      manifest_hash text NOT NULL, expires_at timestamptz NOT NULL)""")


def downgrade():
    raise RuntimeError("Forward-only migration policy")
