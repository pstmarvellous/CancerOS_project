"""Foundation identity, ownership, independent time origins and durable operations."""

from pathlib import Path

from alembic import op

revision = "0001_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    sql = Path(__file__).resolve().parents[1] / "0001_foundation.sql"
    op.get_bind().exec_driver_sql(sql.read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError(
        "Forward-only migration; disposable test databases may be replaced explicitly"
    )
