"""Versioned source evidence metadata, removable search projection and corpus heads."""

from alembic import op

revision = "0043_evidence_corpus"
down_revision = "0042_knowledge_relationships"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE TABLE intelligence.evidence_documents (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, source_version_id uuid NOT NULL,
      canonical_key text NOT NULL, document_version text NOT NULL, manifest_hash text NOT NULL,
      artifact_id uuid, payload jsonb NOT NULL, content_hash text NOT NULL,
      UNIQUE(project_id,id), UNIQUE(project_id,canonical_key,document_version), UNIQUE(project_id,manifest_hash),
      FOREIGN KEY(project_id,source_version_id) REFERENCES source.registry_versions(project_id,id),
      FOREIGN KEY(project_id,artifact_id) REFERENCES ops.artifacts(project_id,id))""")
    op.execute("""CREATE TABLE intelligence.evidence_passages (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, document_id uuid NOT NULL,
      payload jsonb NOT NULL, content_hash text NOT NULL,
      UNIQUE(project_id,id), UNIQUE(project_id,document_id,id),
      FOREIGN KEY(project_id,document_id) REFERENCES intelligence.evidence_documents(project_id,id))""")
    op.execute("""CREATE TABLE intelligence.evidence_passage_content (
      project_id uuid NOT NULL, document_id uuid NOT NULL, passage_id uuid NOT NULL,
      text_content text NOT NULL, text_sha256 text NOT NULL,
      search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english'::regconfig,text_content)) STORED,
      PRIMARY KEY(project_id,passage_id),
      FOREIGN KEY(project_id,document_id,passage_id) REFERENCES intelligence.evidence_passages(project_id,document_id,id))""")
    op.execute(
        "CREATE INDEX evidence_english_search ON intelligence.evidence_passage_content USING GIN(search_vector)"
    )
    op.execute("""CREATE TABLE intelligence.evidence_document_events (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, document_id uuid NOT NULL,
      sequence bigserial NOT NULL, action text NOT NULL CHECK(action IN ('retracted','withdrawn','retention_review_required')),
      reason text NOT NULL, actor_id uuid NOT NULL REFERENCES access.users(id),
      FOREIGN KEY(project_id,document_id) REFERENCES intelligence.evidence_documents(project_id,id))""")
    op.execute("""CREATE TABLE intelligence.evidence_corpora (
      id uuid PRIMARY KEY, project_id uuid NOT NULL REFERENCES access.projects(id),
      payload jsonb NOT NULL, content_hash text NOT NULL, UNIQUE(project_id,id), UNIQUE(project_id,content_hash))""")
    op.execute("""CREATE TABLE intelligence.evidence_corpus_members (
      project_id uuid NOT NULL, corpus_id uuid NOT NULL, document_id uuid NOT NULL,
      PRIMARY KEY(project_id,corpus_id,document_id),
      FOREIGN KEY(project_id,corpus_id) REFERENCES intelligence.evidence_corpora(project_id,id),
      FOREIGN KEY(project_id,document_id) REFERENCES intelligence.evidence_documents(project_id,id))""")
    op.execute("""CREATE TABLE intelligence.evidence_activations (
      id uuid PRIMARY KEY, project_id uuid NOT NULL, corpus_id uuid NOT NULL, prior_activation_id uuid,
      UNIQUE(project_id,id), FOREIGN KEY(project_id,corpus_id) REFERENCES intelligence.evidence_corpora(project_id,id),
      FOREIGN KEY(project_id,prior_activation_id) REFERENCES intelligence.evidence_activations(project_id,id))""")
    op.execute("""CREATE TABLE intelligence.evidence_corpus_heads (
      project_id uuid PRIMARY KEY REFERENCES access.projects(id), activation_id uuid NOT NULL,
      FOREIGN KEY(project_id,activation_id) REFERENCES intelligence.evidence_activations(project_id,id))""")
    for table in (
        "evidence_documents",
        "evidence_passages",
        "evidence_document_events",
        "evidence_corpora",
        "evidence_corpus_members",
        "evidence_activations",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON intelligence.{table} "
            "FOR EACH ROW EXECUTE FUNCTION source.reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Forward-only migration policy")
