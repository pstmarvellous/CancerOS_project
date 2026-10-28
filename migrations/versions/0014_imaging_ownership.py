"""Database-enforced patient/mapping/study ownership for imaging imports."""

from alembic import op

revision = "0014_imaging_ownership"
down_revision = "0013_imaging_imports"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE source.patient_mappings ADD CONSTRAINT mapping_patient_owned UNIQUE(project_id,patient_id,id)"
    )
    op.execute(
        "ALTER TABLE ops.artifacts ADD CONSTRAINT artifact_patient_owned UNIQUE(project_id,patient_id,id)"
    )
    op.execute(
        "ALTER TABLE imaging.imports ADD CONSTRAINT import_patient_owned UNIQUE(project_id,patient_id,id)"
    )
    op.execute("""CREATE TABLE imaging.studies (
 project_id uuid NOT NULL, patient_id uuid NOT NULL, mapping_id uuid NOT NULL, study_id uuid NOT NULL,
 PRIMARY KEY(project_id,study_id), UNIQUE(project_id,patient_id,mapping_id,study_id),
 FOREIGN KEY(project_id,patient_id,mapping_id) REFERENCES source.patient_mappings(project_id,patient_id,id)
 )""")
    op.execute(
        "INSERT INTO imaging.studies SELECT DISTINCT project_id,patient_id,mapping_id,study_id FROM imaging.associations"
    )
    op.execute(
        "CREATE TRIGGER studies_immutable BEFORE UPDATE OR DELETE ON imaging.studies FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )
    op.execute(
        "ALTER TABLE imaging.staged_files ADD CONSTRAINT imaging_file_mapping_owned FOREIGN KEY(project_id,patient_id,mapping_id) REFERENCES source.patient_mappings(project_id,patient_id,id)"
    )
    op.execute(
        "ALTER TABLE imaging.staged_files ADD CONSTRAINT imaging_file_artifact_owned FOREIGN KEY(project_id,patient_id,id) REFERENCES ops.artifacts(project_id,patient_id,id)"
    )
    op.execute(
        "ALTER TABLE imaging.imports ADD CONSTRAINT imaging_manifest_owned FOREIGN KEY(project_id,patient_id,private_manifest_id) REFERENCES ops.artifacts(project_id,patient_id,id)"
    )
    op.execute(
        "ALTER TABLE imaging.associations ADD CONSTRAINT imaging_series_study_owned FOREIGN KEY(project_id,patient_id,mapping_id,study_id) REFERENCES imaging.studies(project_id,patient_id,mapping_id,study_id)"
    )
    op.execute(
        "ALTER TABLE imaging.associations ADD CONSTRAINT imaging_series_import_owned FOREIGN KEY(project_id,patient_id,import_id) REFERENCES imaging.imports(project_id,patient_id,id)"
    )
    op.execute(
        "ALTER TABLE imaging.confirmations ADD CONSTRAINT imaging_confirmation_owned FOREIGN KEY(project_id,patient_id,import_id) REFERENCES imaging.imports(project_id,patient_id,id)"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
