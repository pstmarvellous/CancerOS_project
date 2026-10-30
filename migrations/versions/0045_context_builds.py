"""Append-only interpretation context build audit."""

from alembic import op

revision = "0045_context_builds"
down_revision = "0044_note_observations"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE intelligence.context_builds (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      snapshot_id uuid NOT NULL, snapshot_hash text NOT NULL CHECK(snapshot_hash ~ '^[0-9a-f]{64}$'),
      context_hash text NOT NULL CHECK(context_hash ~ '^[0-9a-f]{64}$'),
      payload_hash text NOT NULL CHECK(payload_hash ~ '^[0-9a-f]{64}$'),
      purpose text NOT NULL CHECK(purpose IN ('research_summary','fact_extraction')),
      stale boolean NOT NULL, omitted_count integer NOT NULL CHECK(omitted_count>=0),
      built_at timestamptz NOT NULL DEFAULT now())""")
    op.execute(
        "CREATE TRIGGER context_builds_immutable BEFORE UPDATE OR DELETE ON intelligence.context_builds FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
