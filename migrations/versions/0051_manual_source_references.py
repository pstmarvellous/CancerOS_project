"""Patient-owned private source-reference metadata, without registry disclosure."""

from alembic import op

revision = "0051_manual_source_references"
down_revision = "0050_research_profiles"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""ALTER TABLE source.source_locators ADD COLUMN source_reference text
      CHECK(source_reference IS NULL OR length(source_reference) BETWEEN 1 AND 1000)""")


def downgrade():
    raise RuntimeError("Forward-only migration policy")
