"""Private evidence versions and atomic corpus activation; no URL fetching or export."""

import hashlib
import json
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import HTTPException
from sqlalchemy import text

from canceros.contracts import Contract, Hash
from canceros.evidence_contracts import (
    CorpusBuildInput,
    EvidenceManifest,
    EvidenceTextInput,
    PassageDescriptor,
    build_passages,
    prepare_text,
)
from canceros.identity import authorize_project
from canceros.patient_linkage import audit
from canceros.persistence import science_hash
from canceros.source_registry import SourceAction, get_source, require_source_action


class EvidenceDocument(Contract):
    id: UUID
    manifest: EvidenceManifest
    original_sha256: Hash | None
    normalized_sha256: Hash | None
    artifact_id: UUID | None
    passage_ids: tuple[UUID, ...]
    status: Literal["approved_excerpt", "metadata_only", "needs_review", "excluded"]
    limitations: tuple[str, ...] = (
        "Source eligibility is not evidence of clinical claim support.",
        "External processing requires its independent denied-by-default policy.",
    )


class EvidenceCorpus(Contract):
    id: UUID
    document_ids: tuple[UUID, ...]
    passage_hashes: tuple[tuple[UUID, Hash], ...]
    index_configuration: Literal["english"] = "english"
    index_version: Literal["postgres-keyword/1"] = "postgres-keyword/1"
    content_hash: Hash


class CorpusActivationInput(Contract):
    corpus_id: UUID
    expected_activation_id: UUID | None = None


class CorpusActivation(Contract):
    id: UUID
    corpus_id: UUID
    prior_activation_id: UUID | None


class EvidenceStatusInput(Contract):
    action: Literal["retracted", "withdrawn", "retention_review_required"]
    reason: Literal["publisher_notice", "source_rights", "extraction_error", "curator_review"]


class EvidenceStatusReceipt(Contract):
    id: UUID
    document_id: UUID
    search_content_removed: bool
    original_private_object_retention: Literal["review_required_no_complete_deletion_claim"] = (
        "review_required_no_complete_deletion_claim"
    )


def _lock(c, i, p, write=False):
    authorize_project(i, p, "admin" if write else "viewer")
    c.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:s,0))"), {"s": f"evidence:{p}"})


def _rights(c, i, p, manifest: EvidenceManifest, *, excerpt=False):
    source = get_source(c, i, p, manifest.source_version_id)
    if source.kind != "artifact_source":
        raise HTTPException(422)
    if (source.origin == "synthetic_engineering_fixture") != (
        manifest.review_basis == "synthetic_fixture"
    ):
        raise HTTPException(422)
    for action in (
        [SourceAction.INTERNAL, SourceAction.DERIVATIVE, SourceAction.PUBLIC]
        if excerpt
        else [SourceAction.INTERNAL]
    ):
        require_source_action(c, i, p, source.id, action, real_data=source.origin == "real_source")
    return source


def _row(c, p, identifier):
    row = (
        c.execute(
            text("SELECT * FROM intelligence.evidence_documents WHERE project_id=:p AND id=:id"),
            {"p": p, "id": identifier},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    if science_hash(row["payload"]) != row["content_hash"]:
        raise HTTPException(409)
    return row


def _eligible(c, i, p, document: EvidenceDocument, *, excerpt=False):
    if (
        document.manifest.retraction_status == "retracted"
        or c.execute(
            text(
                "SELECT 1 FROM intelligence.evidence_document_events WHERE project_id=:p AND document_id=:id LIMIT 1"
            ),
            {"p": p, "id": document.id},
        ).first()
    ):
        raise HTTPException(409)
    _rights(c, i, p, document.manifest, excerpt=excerpt)
    if excerpt and (
        document.status != "approved_excerpt" or document.manifest.retraction_status != "clear"
    ):
        raise HTTPException(409)


def read_document(c, i, p, identifier) -> EvidenceDocument:
    _lock(c, i, p)
    document = EvidenceDocument.model_validate(_row(c, p, identifier)["payload"])
    # Metadata can itself carry restrictions; viewer reads require public permission.
    _eligible(c, i, p, document)
    require_source_action(
        c,
        i,
        p,
        document.manifest.source_version_id,
        SourceAction.PUBLIC,
        real_data=document.manifest.review_basis == "documented_review",
    )
    return document


def import_document(
    c, i, p, manifest: EvidenceManifest, value: EvidenceTextInput | None, storage
) -> EvidenceDocument:
    _lock(c, i, p, write=True)
    source = _rights(c, i, p, manifest, excerpt=manifest.content_mode == "approved_excerpt")
    if manifest.retraction_status == "retracted":
        if value is not None:
            raise HTTPException(422)
    if (manifest.content_mode == "metadata_only") != (value is None):
        raise HTTPException(422)
    if value is not None and value.manifest != manifest:
        raise HTTPException(422)
    canonical_key = manifest.doi or manifest.canonical_url
    existing = c.execute(
        text(
            "SELECT id,manifest_hash FROM intelligence.evidence_documents WHERE project_id=:p AND canonical_key=:key AND document_version=:v"
        ),
        {"p": p, "key": canonical_key, "v": manifest.document_version},
    ).first()
    metadata_hash = science_hash(manifest.model_dump(mode="json"))
    prepared = prepare_text(value) if value else None
    original_sha = prepared.original_sha256 if prepared else None
    if original_sha and original_sha != source.manifest_sha256:
        raise HTTPException(422)
    fingerprint = science_hash(
        {
            "manifest": metadata_hash,
            "text": prepared.normalized_sha256 if prepared else None,
            "original_sha256": original_sha,
        }
    )
    if existing:
        if existing.manifest_hash != fingerprint:
            raise HTTPException(409)
        document = EvidenceDocument.model_validate(_row(c, p, existing.id)["payload"])
        _eligible(c, i, p, document, excerpt=prepared is not None)
        return document
    normalized_text = prepared.text.get_secret_value() if prepared else ""
    descriptor_list = build_passages(p, fingerprint, normalized_text) if prepared else ()
    if prepared and not descriptor_list:
        raise HTTPException(422)
    artifact_id = None
    if prepared:
        assert value is not None
        stored = storage.write_verified(p, value.text.get_secret_value().encode("utf-8"))
        artifact_id = uuid4()
        c.execute(
            text(
                "INSERT INTO ops.artifacts(id,project_id,object_key,object_version,byte_size,sha256,provenance,availability) VALUES(:id,:p,:key,:version,:size,:sha,:origin,'verified')"
            ),
            {
                "id": artifact_id,
                "p": p,
                "key": stored.key,
                "version": stored.version,
                "size": stored.byte_size,
                "sha": stored.sha256,
                "origin": "SYNTHETIC_GENERATED"
                if source.origin == "synthetic_engineering_fixture"
                else "REAL_DERIVED",
            },
        )
    identifier = uuid5(NAMESPACE_URL, f"canceros-evidence:{p}:{fingerprint}")
    document = EvidenceDocument(
        id=identifier,
        manifest=manifest,
        original_sha256=original_sha,
        normalized_sha256=prepared.normalized_sha256 if prepared else None,
        artifact_id=artifact_id,
        passage_ids=tuple(d.id for d in descriptor_list),
        status="excluded"
        if manifest.retraction_status == "retracted"
        else "needs_review"
        if manifest.retraction_status == "unknown" and prepared
        else manifest.content_mode,
    )
    payload = document.model_dump(mode="json")
    c.execute(
        text(
            "INSERT INTO intelligence.evidence_documents(id,project_id,source_version_id,canonical_key,document_version,manifest_hash,artifact_id,payload,content_hash) VALUES(:id,:p,:source,:key,:v,:mh,:a,CAST(:payload AS jsonb),:h)"
        ),
        {
            "id": identifier,
            "p": p,
            "source": source.id,
            "key": canonical_key,
            "v": manifest.document_version,
            "mh": fingerprint,
            "a": artifact_id,
            "payload": json.dumps(payload),
            "h": science_hash(payload),
        },
    )
    for descriptor in descriptor_list:
        info = descriptor.model_dump(mode="json")
        passage_text = normalized_text[descriptor.span.start : descriptor.span.end]
        c.execute(
            text(
                "INSERT INTO intelligence.evidence_passages(id,project_id,document_id,payload,content_hash) VALUES(:id,:p,:d,CAST(:payload AS jsonb),:h)"
            ),
            {
                "id": descriptor.id,
                "p": p,
                "d": identifier,
                "payload": json.dumps(info),
                "h": science_hash(info),
            },
        )
        c.execute(
            text(
                "INSERT INTO intelligence.evidence_passage_content(project_id,document_id,passage_id,text_content,text_sha256) VALUES(:p,:d,:id,:text,:h)"
            ),
            {
                "p": p,
                "d": identifier,
                "id": descriptor.id,
                "text": passage_text,
                "h": descriptor.text_sha256,
            },
        )
    audit(c, p, identifier, "EVIDENCE_VERSION_IMPORTED")
    return document


def build_corpus(c, i, p, value: CorpusBuildInput) -> EvidenceCorpus:
    _lock(c, i, p, write=True)
    if value.expected_activation_id is not None:
        head = c.execute(
            text(
                "SELECT activation_id FROM intelligence.evidence_corpus_heads WHERE project_id=:p"
            ),
            {"p": p},
        ).scalar_one_or_none()
        if head != value.expected_activation_id:
            raise HTTPException(412)
    documents = []
    passage_hashes = []
    for identifier in sorted(value.document_ids, key=str):
        document = EvidenceDocument.model_validate(_row(c, p, identifier)["payload"])
        _eligible(c, i, p, document, excerpt=True)
        documents.append(document.id)
        for passage in document.passage_ids:
            row = c.execute(
                text(
                    "SELECT payload,content_hash FROM intelligence.evidence_passages WHERE project_id=:p AND document_id=:d AND id=:id"
                ),
                {"p": p, "d": identifier, "id": passage},
            ).first()
            content = c.execute(
                text(
                    "SELECT text_content,text_sha256 FROM intelligence.evidence_passage_content WHERE project_id=:p AND passage_id=:id"
                ),
                {"p": p, "id": passage},
            ).first()
            if row is None or content is None or science_hash(row.payload) != row.content_hash:
                raise HTTPException(409)
            descriptor = PassageDescriptor.model_validate(row.payload)
            if (
                hashlib.sha256(content.text_content.encode()).hexdigest() != descriptor.text_sha256
                or content.text_sha256 != descriptor.text_sha256
            ):
                raise HTTPException(409)
            passage_hashes.append((passage, descriptor.text_sha256))
    manifest = {
        "document_ids": [str(d) for d in documents],
        "passages": [(str(a), b) for a, b in passage_hashes],
        "index": "english/postgres-keyword/1",
    }
    digest = science_hash(manifest)
    identifier = uuid5(NAMESPACE_URL, f"canceros-corpus:{p}:{digest}")
    existing = c.execute(
        text("SELECT payload FROM intelligence.evidence_corpora WHERE project_id=:p AND id=:id"),
        {"p": p, "id": identifier},
    ).first()
    if existing:
        return EvidenceCorpus.model_validate(existing.payload)
    corpus = EvidenceCorpus(
        id=identifier,
        document_ids=tuple(documents),
        passage_hashes=tuple(passage_hashes),
        content_hash=digest,
    )
    payload = corpus.model_dump(mode="json")
    c.execute(
        text(
            "INSERT INTO intelligence.evidence_corpora(id,project_id,payload,content_hash) VALUES(:id,:p,CAST(:payload AS jsonb),:h)"
        ),
        {"id": identifier, "p": p, "payload": json.dumps(payload), "h": science_hash(payload)},
    )
    for document_id in documents:
        c.execute(
            text(
                "INSERT INTO intelligence.evidence_corpus_members(project_id,corpus_id,document_id) VALUES(:p,:c,:d)"
            ),
            {"p": p, "c": identifier, "d": document_id},
        )
    audit(c, p, identifier, "EVIDENCE_CORPUS_BUILT")
    return corpus


def read_corpus(c, i, p, identifier) -> EvidenceCorpus:
    _lock(c, i, p)
    row = c.execute(
        text(
            "SELECT payload,content_hash FROM intelligence.evidence_corpora WHERE project_id=:p AND id=:id"
        ),
        {"p": p, "id": identifier},
    ).first()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.payload) != row.content_hash:
        raise HTTPException(409)
    corpus = EvidenceCorpus.model_validate(row.payload)
    for document_id in corpus.document_ids:
        _eligible(
            c,
            i,
            p,
            EvidenceDocument.model_validate(_row(c, p, document_id)["payload"]),
            excerpt=True,
        )
    for passage_id, expected_hash in corpus.passage_hashes:
        content = c.execute(
            text(
                "SELECT text_content,text_sha256 FROM intelligence.evidence_passage_content WHERE project_id=:p AND passage_id=:id"
            ),
            {"p": p, "id": passage_id},
        ).first()
        if (
            content is None
            or content.text_sha256 != expected_hash
            or hashlib.sha256(content.text_content.encode()).hexdigest() != expected_hash
        ):
            raise HTTPException(409)
    return corpus


def activate_corpus(c, i, p, value: CorpusActivationInput) -> CorpusActivation:
    _lock(c, i, p, write=True)
    read_corpus(c, i, p, value.corpus_id)
    head = c.execute(
        text(
            "SELECT activation_id FROM intelligence.evidence_corpus_heads WHERE project_id=:p FOR UPDATE"
        ),
        {"p": p},
    ).scalar_one_or_none()
    if head != value.expected_activation_id:
        raise HTTPException(412)
    receipt = CorpusActivation(id=uuid4(), corpus_id=value.corpus_id, prior_activation_id=head)
    c.execute(
        text(
            "INSERT INTO intelligence.evidence_activations(id,project_id,corpus_id,prior_activation_id) VALUES(:id,:p,:c,:prior)"
        ),
        {"id": receipt.id, "p": p, "c": value.corpus_id, "prior": head},
    )
    c.execute(
        text(
            "INSERT INTO intelligence.evidence_corpus_heads(project_id,activation_id) VALUES(:p,:id) ON CONFLICT(project_id) DO UPDATE SET activation_id=excluded.activation_id"
        ),
        {"p": p, "id": receipt.id},
    )
    audit(c, p, receipt.id, "EVIDENCE_CORPUS_ACTIVATED")
    return receipt


def restrict_document(c, i, p, document_id, value: EvidenceStatusInput) -> EvidenceStatusReceipt:
    _lock(c, i, p, write=True)
    _row(c, p, document_id)
    identifier = uuid4()
    c.execute(
        text(
            "INSERT INTO intelligence.evidence_document_events(id,project_id,document_id,action,reason,actor_id) VALUES(:id,:p,:d,:a,:reason,:actor)"
        ),
        {
            "id": identifier,
            "p": p,
            "d": document_id,
            "a": value.action,
            "reason": value.reason,
            "actor": i.user_id,
        },
    )
    c.execute(
        text(
            "DELETE FROM intelligence.evidence_passage_content WHERE project_id=:p AND document_id=:id"
        ),
        {"p": p, "id": document_id},
    )
    audit(c, p, document_id, "EVIDENCE_CURRENT_SEARCH_REMOVED")
    return EvidenceStatusReceipt(
        id=identifier, document_id=document_id, search_content_removed=True
    )


class EvidencePassageView(Contract):
    document_id: UUID
    corpus_id: UUID
    descriptor: PassageDescriptor
    excerpt: str
    attribution: str
    support_status: Literal["citation_resolves_meaningful_support_unreviewed"] = (
        "citation_resolves_meaningful_support_unreviewed"
    )


class CorpusHeadView(Contract):
    activation_id: UUID | None
    corpus_id: UUID | None
    status: Literal["active", "unconfigured", "unavailable"]
    next_action: Literal[
        "inspect_permitted_evidence", "curator_build_required", "curator_rebuild_required"
    ]


def read_current_corpus(c, i, p) -> CorpusHeadView:
    _lock(c, i, p)
    row = c.execute(
        text(
            "SELECT h.activation_id,a.corpus_id FROM intelligence.evidence_corpus_heads h JOIN intelligence.evidence_activations a ON (a.project_id,a.id)=(h.project_id,h.activation_id) WHERE h.project_id=:p"
        ),
        {"p": p},
    ).first()
    if row is None:
        return CorpusHeadView(
            activation_id=None,
            corpus_id=None,
            status="unconfigured",
            next_action="curator_build_required",
        )
    try:
        read_corpus(c, i, p, row.corpus_id)
    except HTTPException as exc:
        if exc.status_code not in (403, 404, 409):
            raise
        return CorpusHeadView(
            activation_id=row.activation_id,
            corpus_id=row.corpus_id,
            status="unavailable",
            next_action="curator_rebuild_required",
        )
    return CorpusHeadView(
        activation_id=row.activation_id,
        corpus_id=row.corpus_id,
        status="active",
        next_action="inspect_permitted_evidence",
    )


def read_passage(c, i, p, corpus_id, passage_id) -> EvidencePassageView:
    corpus = read_corpus(c, i, p, corpus_id)
    if passage_id not in {identifier for identifier, _ in corpus.passage_hashes}:
        raise HTTPException(404)
    row = c.execute(
        text(
            "SELECT m.document_id,m.payload,m.content_hash,t.text_content FROM intelligence.evidence_passages m JOIN intelligence.evidence_passage_content t ON (t.project_id,t.passage_id)=(m.project_id,m.id) WHERE m.project_id=:p AND m.id=:id"
        ),
        {"p": p, "id": passage_id},
    ).first()
    if row is None or science_hash(row.payload) != row.content_hash:
        raise HTTPException(409)
    descriptor = PassageDescriptor.model_validate(row.payload)
    if hashlib.sha256(row.text_content.encode()).hexdigest() != descriptor.text_sha256:
        raise HTTPException(409)
    document = read_document(c, i, p, row.document_id)
    return EvidencePassageView(
        document_id=document.id,
        corpus_id=corpus_id,
        descriptor=descriptor,
        excerpt=row.text_content,
        attribution=document.manifest.attribution,
    )
