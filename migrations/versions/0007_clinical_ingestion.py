"""Private source manifests and append-only clinical ingestion/revision outbox."""

from alembic import op

revision = "0007_clinical_ingestion"
down_revision = "0006_patient_linkage"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE source.ingestion_artifacts (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 source_version_id uuid NOT NULL, mapping_id uuid NOT NULL,
 recorded_by uuid NOT NULL REFERENCES access.users(id), recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,patient_id,id),
 FOREIGN KEY(project_id,id) REFERENCES ops.artifacts(project_id,id),
 FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
 FOREIGN KEY(project_id,source_version_id) REFERENCES source.registry_versions(project_id,id),
 FOREIGN KEY(project_id,mapping_id) REFERENCES source.patient_mappings(project_id,id)
 )""")
    op.execute("""CREATE TABLE source.source_locators (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 artifact_id uuid NOT NULL, row_index integer NOT NULL CHECK(row_index>=0), record_hash text NOT NULL,
 UNIQUE(project_id,patient_id,id), UNIQUE(project_id,artifact_id,row_index),
 FOREIGN KEY(project_id,patient_id,artifact_id) REFERENCES source.ingestion_artifacts(project_id,patient_id,id)
 )""")
    op.execute(
        "ALTER TABLE clinical.time_references ADD CONSTRAINT time_owned UNIQUE(project_id,patient_id,id)"
    )
    op.execute("""CREATE TABLE clinical.observations (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 source_locator_id uuid NOT NULL, logical_key text NOT NULL, kind text NOT NULL CHECK(kind IN ('visit','laboratory','vital','diagnosis','treatment','symptom','note')),
 time_reference_id uuid NOT NULL, lifecycle text NOT NULL DEFAULT 'accepted' CHECK(lifecycle='accepted'),
 supersedes_id uuid, payload jsonb NOT NULL, payload_hash text NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,source_locator_id) REFERENCES source.source_locators(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,supersedes_id) REFERENCES clinical.observations(project_id,patient_id,id),
 FOREIGN KEY(project_id,patient_id,time_reference_id) REFERENCES clinical.time_references(project_id,patient_id,id)
 )""")
    op.execute("""CREATE TABLE clinical.observation_heads (
 project_id uuid NOT NULL, patient_id uuid NOT NULL, logical_key text NOT NULL,
 record_id uuid NOT NULL, retracted boolean NOT NULL DEFAULT false,
 PRIMARY KEY(project_id,patient_id,logical_key),
 FOREIGN KEY(project_id,patient_id,record_id) REFERENCES clinical.observations(project_id,patient_id,id)
 )""")
    op.execute("""CREATE TABLE clinical.retractions (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 record_id uuid NOT NULL, reason_code text NOT NULL, actor_id uuid NOT NULL REFERENCES access.users(id),
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,patient_id,record_id),
 FOREIGN KEY(project_id,patient_id,record_id) REFERENCES clinical.observations(project_id,patient_id,id)
 )""")
    op.execute("""CREATE TABLE source.ingestion_results (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 artifact_id uuid NOT NULL, actor_id uuid NOT NULL REFERENCES access.users(id),
 command_key text NOT NULL, request_hash text NOT NULL, report jsonb NOT NULL,
 recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 UNIQUE(project_id,patient_id,actor_id,command_key),
 FOREIGN KEY(project_id,patient_id,artifact_id) REFERENCES source.ingestion_artifacts(project_id,patient_id,id)
 )""")
    op.execute("""CREATE TABLE ops.domain_outbox (
 id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
 revision bigint NOT NULL, event_code text NOT NULL, delivered_at timestamptz,
 FOREIGN KEY(project_id,patient_id,revision) REFERENCES source.patient_revisions(project_id,patient_id,revision),
 UNIQUE(project_id,patient_id,revision,event_code)
 )""")
    for schema, table in (
        ("source", "ingestion_artifacts"),
        ("source", "source_locators"),
        ("source", "ingestion_results"),
        ("clinical", "observations"),
        ("clinical", "retractions"),
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {schema}.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )
    op.execute("""CREATE TABLE clinical.numeric_results (
 observation_id uuid PRIMARY KEY REFERENCES clinical.observations(id),
 value numeric(24,9), comparator text CHECK(comparator IN ('<','<=','>','>=')),
 threshold numeric(24,9), unit text, missing_reason text,
 original_value text, original_unit text, conversion_version text,
 CHECK ((value IS NOT NULL AND comparator IS NULL AND threshold IS NULL AND missing_reason IS NULL AND unit IS NOT NULL)
 OR (value IS NULL AND comparator IS NOT NULL AND threshold IS NOT NULL AND missing_reason IS NULL AND unit IS NOT NULL)
 OR (value IS NULL AND comparator IS NULL AND threshold IS NULL AND missing_reason IS NOT NULL AND unit IS NULL))
 )""")
    op.execute("""CREATE TABLE clinical.visits (
 observation_id uuid PRIMARY KEY REFERENCES clinical.observations(id), label text NOT NULL, occasion_type text NOT NULL
 )""")
    op.execute("""CREATE TABLE clinical.diagnosis_results (
 observation_id uuid PRIMARY KEY REFERENCES clinical.observations(id), histology text, side text NOT NULL,
 er_status text NOT NULL, pr_status text NOT NULL, her2_status text NOT NULL,
 clinical_stage text, pathologic_stage text, staging_system text
 )""")
    op.execute("""CREATE TABLE clinical.treatment_events (
 observation_id uuid PRIMARY KEY REFERENCES clinical.observations(id), category text NOT NULL,
 event_type text NOT NULL, exposure_status text NOT NULL, regimen_text text,
 ended_time_id uuid REFERENCES clinical.time_references(id)
 )""")
    op.execute("""CREATE TABLE clinical.symptom_results (
 observation_id uuid PRIMARY KEY REFERENCES clinical.observations(id), presence text NOT NULL,
 reporter text NOT NULL, severity_value numeric(24,9), severity_scale_id text, severity_scale_version text
 )""")
    op.execute("""CREATE FUNCTION clinical.check_subtype() RETURNS trigger LANGUAGE plpgsql AS $$
 DECLARE n integer; matched boolean;
 BEGIN
 SELECT (EXISTS(SELECT 1 FROM clinical.numeric_results WHERE observation_id=NEW.id))::int
 +(EXISTS(SELECT 1 FROM clinical.visits WHERE observation_id=NEW.id))::int
 +(EXISTS(SELECT 1 FROM clinical.diagnosis_results WHERE observation_id=NEW.id))::int
 +(EXISTS(SELECT 1 FROM clinical.treatment_events WHERE observation_id=NEW.id))::int
 +(EXISTS(SELECT 1 FROM clinical.symptom_results WHERE observation_id=NEW.id))::int INTO n;
 SELECT CASE WHEN NEW.kind IN ('laboratory','vital') THEN EXISTS(SELECT 1 FROM clinical.numeric_results WHERE observation_id=NEW.id)
 WHEN NEW.kind='visit' THEN EXISTS(SELECT 1 FROM clinical.visits WHERE observation_id=NEW.id)
 WHEN NEW.kind='diagnosis' THEN EXISTS(SELECT 1 FROM clinical.diagnosis_results WHERE observation_id=NEW.id)
 WHEN NEW.kind='treatment' THEN EXISTS(SELECT 1 FROM clinical.treatment_events WHERE observation_id=NEW.id)
 WHEN NEW.kind='symptom' THEN EXISTS(SELECT 1 FROM clinical.symptom_results WHERE observation_id=NEW.id)
 ELSE false END INTO matched;
 IF n<>1 OR NOT matched THEN RAISE EXCEPTION 'CLINICAL_SUBTYPE_REQUIRED'; END IF;
 RETURN NULL; END $$""")
    op.execute(
        "CREATE CONSTRAINT TRIGGER observation_subtype AFTER INSERT ON clinical.observations DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION clinical.check_subtype()"
    )
    for table in (
        "numeric_results",
        "visits",
        "diagnosis_results",
        "treatment_events",
        "symptom_results",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON clinical.{table} FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )
    op.execute("""CREATE FUNCTION clinical.guard_subtype_kind() RETURNS trigger LANGUAGE plpgsql AS $$
 DECLARE k text;
 BEGIN SELECT kind INTO k FROM clinical.observations WHERE id=NEW.observation_id;
 IF NOT ((TG_TABLE_NAME='numeric_results' AND k IN ('laboratory','vital'))
 OR (TG_TABLE_NAME='visits' AND k='visit') OR (TG_TABLE_NAME='diagnosis_results' AND k='diagnosis')
 OR (TG_TABLE_NAME='treatment_events' AND k='treatment') OR (TG_TABLE_NAME='symptom_results' AND k='symptom'))
 THEN RAISE EXCEPTION 'WRONG_CLINICAL_SUBTYPE'; END IF; RETURN NEW; END $$""")
    for table in (
        "numeric_results",
        "visits",
        "diagnosis_results",
        "treatment_events",
        "symptom_results",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_kind BEFORE INSERT ON clinical.{table} FOR EACH ROW EXECUTE FUNCTION clinical.guard_subtype_kind()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
