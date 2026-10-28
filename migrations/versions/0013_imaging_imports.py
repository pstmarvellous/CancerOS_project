"""Private staged imaging and immutable association/confirmation reports."""

from alembic import op

revision = "0013_imaging_imports"
down_revision = "0012_patient_splits"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SCHEMA IF NOT EXISTS imaging")
    op.execute("""CREATE TABLE imaging.staged_files (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 mapping_id uuid NOT NULL, source_version_id uuid NOT NULL, format text NOT NULL CHECK(format IN ('dicom','nifti')),
 input_hash text NOT NULL CHECK(input_hash ~ '^[0-9a-f]{64}$'),
 UNIQUE(project_id,id), UNIQUE(project_id,patient_id,mapping_id,source_version_id,format,input_hash),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,mapping_id) REFERENCES source.patient_mappings(project_id,id),
 FOREIGN KEY(project_id,source_version_id) REFERENCES source.registry_versions(project_id,id),
 FOREIGN KEY(project_id,id) REFERENCES ops.artifacts(project_id,id)
 )""")
    op.execute("""CREATE TABLE imaging.imports (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 input_hash text NOT NULL, report jsonb NOT NULL, association jsonb NOT NULL,
 private_manifest_id uuid NOT NULL, UNIQUE(project_id,id), UNIQUE(project_id,patient_id,input_hash),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,private_manifest_id) REFERENCES ops.artifacts(project_id,id)
 )""")
    op.execute("""CREATE TABLE imaging.associations (
 project_id uuid NOT NULL, patient_id uuid NOT NULL, mapping_id uuid NOT NULL,
 study_id uuid NOT NULL, series_id uuid NOT NULL, key_version text NOT NULL,
 study_digest text NOT NULL, series_digest text NOT NULL, import_id uuid NOT NULL,
 PRIMARY KEY(project_id,series_id), UNIQUE(project_id,mapping_id,key_version,series_digest),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,mapping_id) REFERENCES source.patient_mappings(project_id,id),
 FOREIGN KEY(project_id,import_id) REFERENCES imaging.imports(project_id,id)
 )""")
    op.execute("""CREATE TABLE imaging.confirmations (
 project_id uuid NOT NULL, patient_id uuid NOT NULL, import_id uuid NOT NULL,
 confirmed_by uuid NOT NULL REFERENCES access.users(id), recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(project_id,import_id),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,import_id) REFERENCES imaging.imports(project_id,id)
 )""")
    for table in ("staged_files", "imports", "associations", "confirmations"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON imaging.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
