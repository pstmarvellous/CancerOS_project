"""Preserve source-provided reference intervals without default clinical ranges."""

from alembic import op

revision = "0008_source_intervals"
down_revision = "0007_clinical_ingestion"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE clinical.reference_intervals (
 id uuid PRIMARY KEY, observation_id uuid NOT NULL UNIQUE REFERENCES clinical.observations(id),
 low numeric(24,9), high numeric(24,9), unit text NOT NULL,
 source_description text NOT NULL, population_context text NOT NULL, version text NOT NULL,
 CHECK(low IS NOT NULL OR high IS NOT NULL), CHECK(low IS NULL OR high IS NULL OR low<=high),
 CHECK(coalesce(low::text,'') NOT IN ('NaN','Infinity','-Infinity') AND coalesce(high::text,'') NOT IN ('NaN','Infinity','-Infinity'))
 )""")
    op.execute(
        "CREATE TRIGGER reference_intervals_immutable BEFORE UPDATE OR DELETE ON clinical.reference_intervals FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
