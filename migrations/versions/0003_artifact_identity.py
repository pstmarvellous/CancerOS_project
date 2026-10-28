"""Protect committed artifact byte identity independently of availability updates."""

from alembic import op

revision = "0003_artifact_identity"
down_revision = "0002_job_lease"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE FUNCTION ops.protect_artifact_identity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NEW.id IS DISTINCT FROM OLD.id OR NEW.project_id IS DISTINCT FROM OLD.project_id
 OR NEW.patient_id IS DISTINCT FROM OLD.patient_id OR NEW.object_key IS DISTINCT FROM OLD.object_key
 OR NEW.object_version IS DISTINCT FROM OLD.object_version OR NEW.sha256 IS DISTINCT FROM OLD.sha256
 OR NEW.byte_size IS DISTINCT FROM OLD.byte_size OR NEW.provenance IS DISTINCT FROM OLD.provenance
 THEN RAISE EXCEPTION 'IMMUTABLE_ARTIFACT_IDENTITY'; END IF; RETURN NEW; END $$""")
    op.execute(
        "CREATE TRIGGER artifact_identity_immutable BEFORE UPDATE ON ops.artifacts FOR EACH ROW EXECUTE FUNCTION ops.protect_artifact_identity()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
