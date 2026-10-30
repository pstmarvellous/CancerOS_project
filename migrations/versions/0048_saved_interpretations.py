"""Persist validated interpretations; withdrawals never rewrite history."""

from alembic import op

revision = "0048_saved_interpretations"
down_revision = "0047_grounding_decisions"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE intelligence.saved_interpretations (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      context_snapshot_id uuid NOT NULL,
      context_hash text NOT NULL CHECK(context_hash ~ '^[0-9a-f]{64}$'),
      execution_mode text NOT NULL CHECK(execution_mode IN ('rule_based_summary','external_candidate_private')),
      visibility text NOT NULL CHECK(visibility IN ('visible_template','private_candidate')),
      model_identifier text NOT NULL CHECK(char_length(model_identifier) BETWEEN 1 AND 200),
      model_revision text NOT NULL DEFAULT 'unresolved',
      prompt_version text NOT NULL CHECK(char_length(prompt_version) BETWEEN 1 AND 200),
      validator_version text NOT NULL CHECK(char_length(validator_version) BETWEEN 1 AND 200),
      corpus_manifest text NOT NULL CHECK(char_length(corpus_manifest) BETWEEN 1 AND 500),
      finding_count integer NOT NULL CHECK(finding_count>=0),
      usage_tokens integer CHECK(usage_tokens IS NULL OR usage_tokens>=0),
      failure_stage text CHECK(failure_stage IS NULL OR char_length(failure_stage) BETWEEN 1 AND 200),
      idempotency_key text NOT NULL,
      status text NOT NULL CHECK(status IN ('validated_ready','private_candidate','superseded','withdrawn')),
      superseded_by_id uuid,
      built_at timestamptz NOT NULL DEFAULT now(),
      UNIQUE(project_id,idempotency_key))""")
    op.execute(
        "CREATE TRIGGER saved_interpretations_immutable BEFORE UPDATE OR DELETE ON intelligence.saved_interpretations FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
