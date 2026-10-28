"""Unknown metrics after worker death remain null rather than fabricated zero."""

from alembic import op

revision = "0024_lost_attempt_metrics"
down_revision = "0023_imaging_job_ownership"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE imaging.job_attempt_evidence ALTER COLUMN wall_seconds DROP NOT NULL")
    op.execute("ALTER TABLE imaging.job_attempt_evidence ALTER COLUMN rss_peak_bytes DROP NOT NULL")


def downgrade():
    raise RuntimeError("Forward-only migration policy")
