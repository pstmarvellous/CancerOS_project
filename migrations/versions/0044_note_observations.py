"""Owned immutable clinical source-note pointers, separate from extracted facts."""

from alembic import op

revision = "0044_note_observations"
down_revision = "0043_evidence_corpus"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE clinical.note_documents (
      observation_id uuid PRIMARY KEY, project_id uuid NOT NULL, patient_id uuid NOT NULL,
      note_document_id uuid NOT NULL, artifact_id uuid NOT NULL,
      language text NOT NULL CHECK(language='en'),
      content_sha256 text NOT NULL CHECK(content_sha256 ~ '^[0-9a-f]{64}$'),
      FOREIGN KEY(project_id,patient_id,observation_id) REFERENCES clinical.observations(project_id,patient_id,id),
      FOREIGN KEY(project_id,patient_id,note_document_id) REFERENCES intelligence.note_documents(project_id,patient_id,id),
      FOREIGN KEY(project_id,patient_id,artifact_id) REFERENCES ops.artifacts(project_id,patient_id,id))""")
    op.execute("""CREATE FUNCTION clinical.guard_note_pointer() RETURNS trigger LANGUAGE plpgsql AS $$
      DECLARE document jsonb; observation jsonb; branch uuid; BEGIN
      SELECT payload,branch_id INTO document,branch FROM intelligence.note_documents
        WHERE project_id=NEW.project_id AND patient_id=NEW.patient_id AND id=NEW.note_document_id;
      SELECT payload INTO observation FROM clinical.observations
        WHERE project_id=NEW.project_id AND patient_id=NEW.patient_id AND id=NEW.observation_id AND kind='note';
      IF document IS NULL OR observation IS NULL OR branch IS NOT NULL
        OR document->>'provenance' IS DISTINCT FROM 'SYNTHETIC_GENERATED'
        OR document->>'context' IS DISTINCT FROM 'SYNTHETIC'
        OR document->>'artifact_id' IS DISTINCT FROM NEW.artifact_id::text
        OR document->>'source_sha256' IS DISTINCT FROM NEW.content_sha256
        OR document->>'language' IS DISTINCT FROM NEW.language
        OR observation->'item'->>'note_document_id' IS DISTINCT FROM NEW.note_document_id::text
        OR observation->'item'->>'artifact_id' IS DISTINCT FROM NEW.artifact_id::text
        OR observation->'item'->>'content_sha256' IS DISTINCT FROM NEW.content_sha256
        OR observation->'item'->>'language' IS DISTINCT FROM NEW.language
        OR (document->'anchor' IS DISTINCT FROM 'null'::jsonb AND document->'anchor' IS DISTINCT FROM observation->'item'->'time')
        OR (document->'anchor'='null'::jsonb AND observation->'item'->'time'->'reference'->>'basis' IS DISTINCT FROM 'unknown')
        THEN RAISE EXCEPTION 'INVALID_NOTE_SOURCE_POINTER'; END IF;
      RETURN NEW; END $$""")
    op.execute(
        "CREATE TRIGGER note_documents_kind BEFORE INSERT ON clinical.note_documents FOR EACH ROW EXECUTE FUNCTION clinical.guard_note_pointer()"
    )
    op.execute(
        "CREATE TRIGGER note_documents_immutable BEFORE UPDATE OR DELETE ON clinical.note_documents FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
    )
    op.execute("""CREATE OR REPLACE FUNCTION clinical.check_subtype() RETURNS trigger LANGUAGE plpgsql AS $$
      DECLARE n integer; matched boolean; BEGIN
      SELECT (EXISTS(SELECT 1 FROM clinical.numeric_results WHERE observation_id=NEW.id))::int
      +(EXISTS(SELECT 1 FROM clinical.visits WHERE observation_id=NEW.id))::int
      +(EXISTS(SELECT 1 FROM clinical.diagnosis_results WHERE observation_id=NEW.id))::int
      +(EXISTS(SELECT 1 FROM clinical.treatment_events WHERE observation_id=NEW.id))::int
      +(EXISTS(SELECT 1 FROM clinical.symptom_results WHERE observation_id=NEW.id))::int
      +(EXISTS(SELECT 1 FROM clinical.note_documents WHERE observation_id=NEW.id))::int INTO n;
      SELECT CASE WHEN NEW.kind IN ('laboratory','vital') THEN EXISTS(SELECT 1 FROM clinical.numeric_results WHERE observation_id=NEW.id)
      WHEN NEW.kind='visit' THEN EXISTS(SELECT 1 FROM clinical.visits WHERE observation_id=NEW.id)
      WHEN NEW.kind='diagnosis' THEN EXISTS(SELECT 1 FROM clinical.diagnosis_results WHERE observation_id=NEW.id)
      WHEN NEW.kind='treatment' THEN EXISTS(SELECT 1 FROM clinical.treatment_events WHERE observation_id=NEW.id)
      WHEN NEW.kind='symptom' THEN EXISTS(SELECT 1 FROM clinical.symptom_results WHERE observation_id=NEW.id)
      WHEN NEW.kind='note' THEN EXISTS(SELECT 1 FROM clinical.note_documents WHERE observation_id=NEW.id)
      ELSE false END INTO matched;
      IF n<>1 OR NOT matched THEN RAISE EXCEPTION 'CLINICAL_SUBTYPE_REQUIRED'; END IF;
      RETURN NULL; END $$""")


def downgrade():
    raise RuntimeError("Forward-only migration policy")
