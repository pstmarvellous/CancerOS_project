"""Atomic registry command replay bound to actor, project and input hash."""

from alembic import op

revision = "0005_registry_commands"
down_revision = "0004_source_registry"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE source.registry_commands (
 project_id uuid NOT NULL REFERENCES access.projects(id),
 actor_id uuid NOT NULL REFERENCES access.users(id), operation text NOT NULL,
 key text NOT NULL CHECK(length(key) BETWEEN 1 AND 128),
 input_hash text NOT NULL CHECK(input_hash ~ '^[0-9a-f]{64}$'), response jsonb NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(project_id,actor_id,operation,key)
 )""")
    op.execute(
        "CREATE TRIGGER registry_commands_immutable BEFORE UPDATE OR DELETE ON source.registry_commands FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
