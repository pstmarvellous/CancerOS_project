"""Persist worker lease expiry for bounded recovery after a process restart."""

from alembic import op

revision = "0002_job_lease"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE ops.jobs ADD COLUMN leased_until timestamptz")


def downgrade():
    raise RuntimeError("Forward-only migration policy")
