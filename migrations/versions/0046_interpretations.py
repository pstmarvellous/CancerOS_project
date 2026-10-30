"""Append-only interpretation build audit; candidates stay private."""

from alembic import op

revision = "0046_interpretations"
down_revision = "0045_context_builds"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE intelligence.interpretation_builds (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      context_snapshot_id uuid NOT NULL, context_hash text NOT NULL CHECK(context_hash ~ '^[0-9a-f]{64}$'),
      execution_mode text NOT NULL CHECK(execution_mode IN ('rule_based_summary','external_candidate_private')),
      visibility text NOT NULL CHECK(visibility IN ('visible_template','private_candidate')),
      finding_count integer NOT NULL CHECK(finding_count>=0),
      built_at timestamptz NOT NULL DEFAULT now())""")
    op.execute(
        "CREATE TRIGGER interpretation_builds_immutable BEFORE UPDATE OR DELETE ON intelligence.interpretation_builds FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
