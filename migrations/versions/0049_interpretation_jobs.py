"""Append-only interpretation job ledger; no raw candidate storage."""

from alembic import op

revision = "0049_interpretation_jobs"
down_revision = "0048_saved_interpretations"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE intelligence.interpretation_jobs (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      context_snapshot_id uuid NOT NULL,
      context_hash text NOT NULL CHECK(context_hash ~ '^[0-9a-f]{64}$'),
      snapshot_hash text NOT NULL CHECK(snapshot_hash ~ '^[0-9a-f]{64}$'),
      execution_mode text NOT NULL CHECK(execution_mode IN ('rule_based_summary','external_candidate_private')),
      visibility text NOT NULL CHECK(visibility IN ('visible_template','private_candidate')),
      status text NOT NULL CHECK(status IN ('validated_ready','failed_grounding','withheld_insufficient_evidence')),
      reason_codes text[] NOT NULL DEFAULT '{}',
      finding_count integer NOT NULL CHECK(finding_count>=0),
      saved_id uuid,
      idempotency_key text NOT NULL,
      built_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(project_id,idempotency_key))""")
    op.execute(
        "CREATE TRIGGER interpretation_jobs_immutable BEFORE UPDATE OR DELETE ON intelligence.interpretation_jobs FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
