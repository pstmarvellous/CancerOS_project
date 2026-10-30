"""Append-only grounding decision audit; rejections never publish remnants."""

from alembic import op

revision = "0047_grounding_decisions"
down_revision = "0046_interpretations"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE intelligence.grounding_decisions (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      interpretation_snapshot_id uuid NOT NULL,
      context_hash text NOT NULL CHECK(context_hash ~ '^[0-9a-f]{64}$'),
      verdict text NOT NULL CHECK(verdict IN ('published','withheld_insufficient_evidence','failed_grounding')),
      reason_codes text[] NOT NULL DEFAULT '{}',
      prohibited_critical integer NOT NULL CHECK(prohibited_critical>=0),
      built_at timestamptz NOT NULL DEFAULT now())""")
    op.execute(
        "CREATE TRIGGER grounding_decisions_immutable BEFORE UPDATE OR DELETE ON intelligence.grounding_decisions FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
