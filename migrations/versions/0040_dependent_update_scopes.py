"""One domain event can explicitly update independent source and branch scopes."""

from alembic import op

revision = "0040_dependent_update_scopes"
down_revision = "0039_dependent_update_scope"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""DO $$ DECLARE item record; BEGIN
 FOR item IN SELECT conname FROM pg_constraint WHERE conrelid='ops.dependent_update_reports'::regclass AND confrelid='ops.dependent_update_requests'::regclass AND contype='f'
 LOOP EXECUTE format('ALTER TABLE ops.dependent_update_reports DROP CONSTRAINT %I',item.conname); END LOOP;
 FOR item IN SELECT c.conname FROM pg_constraint c WHERE c.conrelid='ops.dependent_update_requests'::regclass AND c.contype IN ('p','u')
 AND (SELECT attnum FROM pg_attribute WHERE attrelid=c.conrelid AND attname='event_id')=ANY(c.conkey)
 AND NOT (SELECT attnum FROM pg_attribute WHERE attrelid=c.conrelid AND attname='job_id')=ANY(c.conkey)
 LOOP EXECUTE format('ALTER TABLE ops.dependent_update_requests DROP CONSTRAINT %I',item.conname); END LOOP;
 END $$""")
    op.execute("ALTER TABLE ops.dependent_update_requests ADD PRIMARY KEY(event_id,scope_key)")
    op.execute(
        "ALTER TABLE ops.dependent_update_reports ADD CONSTRAINT update_report_execution_scope FOREIGN KEY(project_id,patient_id,revision,scope_key,event_id,job_id) REFERENCES ops.dependent_update_requests(project_id,patient_id,revision,scope_key,event_id,job_id)"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
