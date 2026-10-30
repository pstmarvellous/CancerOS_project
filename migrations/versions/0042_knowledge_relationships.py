"""Typed relational source links with append-only corrections, not clinical causality."""

from alembic import op

revision = "0042_knowledge_relationships"
down_revision = "0041_note_extraction"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE intelligence.clinical_concepts (
      id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES access.projects(id),
      code text NOT NULL, version integer NOT NULL CHECK(version>0),
      supersedes_id uuid, payload jsonb NOT NULL, content_hash text NOT NULL,
      UNIQUE(project_id,id), UNIQUE(project_id,code,version),
      FOREIGN KEY(project_id,supersedes_id) REFERENCES intelligence.clinical_concepts(project_id,id))""")
    op.execute("""CREATE TABLE intelligence.relationship_events (
      id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES access.projects(id),
      patient_id uuid, branch_id uuid, root_id uuid NOT NULL, version integer NOT NULL CHECK(version>0),
      supersedes_id uuid, source_kind text NOT NULL, target_kind text NOT NULL,
      source_resource_id uuid, target_resource_id uuid, source_concept_id uuid, target_concept_id uuid,
      payload jsonb NOT NULL, content_hash text NOT NULL,
      UNIQUE(project_id,id), UNIQUE(project_id,patient_id,id), UNIQUE(project_id,root_id,version), UNIQUE(project_id,supersedes_id),
      FOREIGN KEY(project_id,patient_id) REFERENCES source.research_patients(project_id,id),
      FOREIGN KEY(project_id,patient_id,branch_id) REFERENCES imaging.twin_branches(project_id,patient_id,id),
      FOREIGN KEY(project_id,supersedes_id) REFERENCES intelligence.relationship_events(project_id,id),
      FOREIGN KEY(project_id,root_id) REFERENCES intelligence.relationship_events(project_id,id) DEFERRABLE INITIALLY DEFERRED,
      FOREIGN KEY(project_id,patient_id,source_resource_id) REFERENCES ops.resource_registry(project_id,patient_id,id),
      FOREIGN KEY(project_id,patient_id,target_resource_id) REFERENCES ops.resource_registry(project_id,patient_id,id),
      FOREIGN KEY(project_id,source_concept_id) REFERENCES intelligence.clinical_concepts(project_id,id),
      FOREIGN KEY(project_id,target_concept_id) REFERENCES intelligence.clinical_concepts(project_id,id),
      CHECK(patient_id IS NOT NULL OR (source_kind='clinical_concept' AND target_kind='clinical_concept' AND branch_id IS NULL)),
      CHECK((source_kind='patient' AND source_resource_id IS NULL AND source_concept_id IS NULL AND patient_id IS NOT NULL)
         OR (source_kind='clinical_concept' AND source_resource_id IS NULL AND source_concept_id IS NOT NULL)
         OR (source_kind NOT IN ('patient','clinical_concept') AND source_resource_id IS NOT NULL AND source_concept_id IS NULL AND patient_id IS NOT NULL)),
      CHECK((target_kind='patient' AND target_resource_id IS NULL AND target_concept_id IS NULL AND patient_id IS NOT NULL)
         OR (target_kind='clinical_concept' AND target_resource_id IS NULL AND target_concept_id IS NOT NULL)
         OR (target_kind NOT IN ('patient','clinical_concept') AND target_resource_id IS NOT NULL AND target_concept_id IS NULL AND patient_id IS NOT NULL)))""")
    op.execute("""CREATE TABLE intelligence.relationship_support (
      project_id uuid NOT NULL, patient_id uuid NOT NULL, relationship_id uuid NOT NULL, resource_id uuid NOT NULL,
      PRIMARY KEY(project_id,relationship_id,resource_id),
      FOREIGN KEY(project_id,patient_id,relationship_id) REFERENCES intelligence.relationship_events(project_id,patient_id,id),
      FOREIGN KEY(project_id,patient_id,resource_id) REFERENCES ops.resource_registry(project_id,patient_id,id))""")
    op.execute("""CREATE FUNCTION intelligence.check_relationship_scope() RETURNS trigger LANGUAGE plpgsql AS $$
      DECLARE prior intelligence.relationship_events; BEGIN
      IF NEW.version=1 THEN
        IF NEW.root_id<>NEW.id OR NEW.supersedes_id IS NOT NULL THEN RAISE EXCEPTION 'invalid relationship root'; END IF;
      ELSE
        SELECT * INTO prior FROM intelligence.relationship_events WHERE project_id=NEW.project_id AND id=NEW.supersedes_id;
        IF prior.id IS NULL OR prior.root_id<>NEW.root_id OR prior.version+1<>NEW.version
          OR prior.patient_id IS DISTINCT FROM NEW.patient_id OR prior.branch_id IS DISTINCT FROM NEW.branch_id
          THEN RAISE EXCEPTION 'invalid relationship correction scope'; END IF;
      END IF;
      IF NEW.source_resource_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM ops.resource_registry r
        WHERE r.project_id=NEW.project_id AND r.patient_id=NEW.patient_id AND r.id=NEW.source_resource_id AND r.kind=NEW.source_kind)
        THEN RAISE EXCEPTION 'invalid source resource kind'; END IF;
      IF NEW.target_resource_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM ops.resource_registry r
        WHERE r.project_id=NEW.project_id AND r.patient_id=NEW.patient_id AND r.id=NEW.target_resource_id AND r.kind=NEW.target_kind)
        THEN RAISE EXCEPTION 'invalid target resource kind'; END IF;
      RETURN NEW; END $$""")
    op.execute(
        "CREATE TRIGGER relationship_scope BEFORE INSERT ON intelligence.relationship_events FOR EACH ROW EXECUTE FUNCTION intelligence.check_relationship_scope()"
    )
    for table in ("clinical_concepts", "relationship_events", "relationship_support"):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON intelligence.{table} "
            "FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )
    op.execute(
        "CREATE INDEX relationship_patient_scope ON intelligence.relationship_events(project_id,patient_id,branch_id)"
    )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
