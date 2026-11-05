"""Extend owned note pointers to reviewed observed sources without origin promotion."""

from alembic import op

revision = "0052_reviewed_note_pointers"
down_revision = "0051_manual_source_references"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE OR REPLACE FUNCTION clinical.guard_note_pointer() RETURNS trigger LANGUAGE plpgsql AS $$
      DECLARE document jsonb; observation jsonb; branch uuid; BEGIN
      SELECT payload,branch_id INTO document,branch FROM intelligence.note_documents
        WHERE project_id=NEW.project_id AND patient_id=NEW.patient_id AND id=NEW.note_document_id;
      SELECT payload INTO observation FROM clinical.observations
        WHERE project_id=NEW.project_id AND patient_id=NEW.patient_id AND id=NEW.observation_id AND kind='note';
      IF document IS NULL OR observation IS NULL OR branch IS NOT NULL
        OR (((document->>'provenance'='SYNTHETIC_GENERATED' AND document->>'context'='SYNTHETIC')
          OR (document->>'provenance'='REAL_DERIVED' AND document->>'context'='OBSERVED')) IS NOT TRUE)
        OR observation->>'origin' IS DISTINCT FROM document->>'provenance'
        OR observation->>'context' IS DISTINCT FROM document->>'context'
        OR (observation->>'context'='OBSERVED' AND observation->'item'->'time'->'reference'->>'time_domain'='simulation')
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


def downgrade():
    raise RuntimeError("Forward-only migration policy")
