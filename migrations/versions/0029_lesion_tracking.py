"""Immutable patient-scoped lesion identities, association events and scalar series."""

from alembic import op

revision = "0029_lesion_tracking"
down_revision = "0028_registration_runs"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE imaging.lesion_identities (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 baseline_segmentation_id uuid NOT NULL, actor_id uuid NOT NULL REFERENCES access.users(id),
 command_key text NOT NULL, input_hash text NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,actor_id,command_key),
 FOREIGN KEY(project_id,patient_id,baseline_segmentation_id) REFERENCES imaging.segmentations(project_id,patient_id,id)
 )""")
    op.execute("""CREATE TABLE imaging.lesion_association_events (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 sequence bigint NOT NULL CHECK(sequence>0), lesion_id uuid NOT NULL, segmentation_id uuid NOT NULL,
 supersedes_event_id uuid, measurement_id uuid,
 actor_id uuid NOT NULL REFERENCES access.users(id), command_key text NOT NULL, input_hash text NOT NULL,
 report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,sequence),
 UNIQUE(project_id,patient_id,actor_id,command_key), UNIQUE(supersedes_event_id),
 FOREIGN KEY(project_id,patient_id,lesion_id) REFERENCES imaging.lesion_identities(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,segmentation_id) REFERENCES imaging.segmentations(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,supersedes_event_id) REFERENCES imaging.lesion_association_events(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,measurement_id) REFERENCES imaging.measurement_reports(project_id,patient_id,id)
 )""")
    op.execute("""CREATE TABLE imaging.lesion_event_relations (
 project_id uuid NOT NULL, patient_id uuid NOT NULL, event_id uuid NOT NULL, related_lesion_id uuid NOT NULL,
 PRIMARY KEY(project_id,patient_id,event_id,related_lesion_id),
 FOREIGN KEY(project_id,patient_id,event_id) REFERENCES imaging.lesion_association_events(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,related_lesion_id) REFERENCES imaging.lesion_identities(project_id,patient_id,id)
 )""")
    op.execute("""CREATE TABLE imaging.lesion_measurement_series (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL, lesion_id uuid NOT NULL,
 input_revision bigint NOT NULL, actor_id uuid NOT NULL REFERENCES access.users(id), command_key text NOT NULL,
 input_hash text NOT NULL, report jsonb NOT NULL, report_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,patient_id,actor_id,command_key),
 FOREIGN KEY(project_id,patient_id,lesion_id) REFERENCES imaging.lesion_identities(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,input_revision) REFERENCES source.patient_revisions(project_id,patient_id,revision)
 )""")
    for table in (
        "lesion_identities",
        "lesion_association_events",
        "lesion_event_relations",
        "lesion_measurement_series",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON imaging.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
