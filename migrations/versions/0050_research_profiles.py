"""Additive research profile revisions and explicit privacy/linkage review action."""

from alembic import op

revision = "0050_research_profiles"
down_revision = "0049_interpretation_jobs"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE source.rights_reviews DROP CONSTRAINT rights_reviews_action_check")
    op.execute("""ALTER TABLE source.rights_reviews ADD CONSTRAINT rights_reviews_action_check
      CHECK(action IN ('internal_processing','external_inference','derivative_creation',
      'public_demo_redistribution','patient_linkage_privacy'))""")
    op.execute("""CREATE TABLE source.research_profile_revisions (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      profile_revision integer NOT NULL CHECK(profile_revision>0),
      case_identifier text NOT NULL, source_version_id uuid NOT NULL,
      payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
      recorded_by uuid NOT NULL REFERENCES access.users(id),
      recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
      UNIQUE(project_id,patient_id,profile_revision),
      FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
      FOREIGN KEY(project_id,source_version_id) REFERENCES source.registry_versions(project_id,id))""")
    op.execute("""CREATE TABLE source.research_case_identifiers (
      project_id uuid NOT NULL, case_identifier text NOT NULL, patient_id uuid NOT NULL,
      PRIMARY KEY(project_id,case_identifier), UNIQUE(project_id,patient_id),
      FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id))""")
    for table in ("research_profile_revisions", "research_case_identifiers"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON source.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
