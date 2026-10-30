"""Curator imports and permitted evidence reads; never fetch arbitrary source URLs."""

import hashlib
from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Response

from canceros.contracts import Contract, Hash
from canceros.evidence_contracts import CorpusBuildInput, EvidenceManifest, EvidenceTextInput
from canceros.evidence_retrieval import (
    CitationCheck,
    CitationReport,
    EvidenceRetrievalQuery,
    EvidenceRetrievalReport,
    EvidenceSourceMetadata,
    public_source_metadata,
    retrieve_evidence,
    verify_citation,
)
from canceros.evidence_runs import (
    CorpusActivation,
    CorpusActivationInput,
    CorpusHeadView,
    EvidenceCorpus,
    EvidenceDocument,
    EvidencePassageView,
    EvidenceStatusInput,
    EvidenceStatusReceipt,
    activate_corpus,
    build_corpus,
    import_document,
    read_corpus,
    read_current_corpus,
    read_document,
    read_passage,
    restrict_document,
)
from canceros.identity import authenticate, authorize_project
from canceros.persistence import engine_for
from canceros.source_registry import registry_command
from canceros.storage import PrivateStorage


class EvidenceImportIdentity(Contract):
    manifest: EvidenceManifest
    original_sha256: Hash


class PublicEvidenceDocument(Contract):
    id: UUID
    source: EvidenceSourceMetadata
    normalized_sha256: Hash | None
    passage_ids: tuple[UUID, ...]
    status: str
    limitations: tuple[str, ...]


def evidence_routes(config, memberships):
    router = APIRouter(prefix="/api/v1/projects/{project_id}")

    @contextmanager
    def session(header):
        identity = authenticate(header, config, memberships)
        engine = engine_for(config)
        try:
            with engine.begin() as connection:
                yield connection, identity
        finally:
            engine.dispose()

    @router.post("/evidence-retrieval-queries", response_model=EvidenceRetrievalReport)
    def retrieval(
        project_id: UUID,
        value: EvidenceRetrievalQuery,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return retrieve_evidence(c, i, project_id, value)

    @router.post("/evidence-citation-checks", response_model=CitationReport)
    def citation(
        project_id: UUID, value: CitationCheck, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (c, i):
            return verify_citation(c, i, project_id, value)

    @router.post("/evidence-document-metadata", response_model=EvidenceDocument, status_code=201)
    def metadata_import(
        project_id: UUID,
        value: EvidenceManifest,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            if value.content_mode != "metadata_only":
                raise HTTPException(422)
            registry_command(
                c,
                i,
                project_id,
                "evidence-metadata",
                idempotency_key,
                value,
                lambda: import_document(c, i, project_id, value, None, None),
            )
            result = import_document(c, i, project_id, value, None, None)
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/evidence-documents/{result.id}"
            )
            return result

    @router.post("/evidence-document-excerpts", response_model=EvidenceDocument, status_code=201)
    def excerpt_import(
        project_id: UUID,
        value: EvidenceTextInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            identity = EvidenceImportIdentity(
                manifest=value.manifest,
                original_sha256=hashlib.sha256(value.text.get_secret_value().encode()).hexdigest(),
            )
            registry_command(
                c,
                i,
                project_id,
                "evidence-excerpt",
                idempotency_key,
                identity,
                lambda: import_document(
                    c, i, project_id, value.manifest, value, PrivateStorage(config)
                ),
            )
            result = import_document(
                c, i, project_id, value.manifest, value, PrivateStorage(config)
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/evidence-documents/{result.id}"
            )
            return result

    @router.get("/evidence-documents/{document_id}", response_model=PublicEvidenceDocument)
    def document(
        project_id: UUID, document_id: UUID, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (c, i):
            document = read_document(c, i, project_id, document_id)
            return PublicEvidenceDocument(
                id=document.id,
                source=public_source_metadata(document.manifest),
                normalized_sha256=document.normalized_sha256,
                passage_ids=document.passage_ids,
                status=document.status,
                limitations=document.limitations,
            )

    @router.post(
        "/evidence-documents/{document_id}/restrictions",
        response_model=EvidenceStatusReceipt,
        status_code=201,
    )
    def restriction(
        project_id: UUID,
        document_id: UUID,
        value: EvidenceStatusInput,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return registry_command(
                c,
                i,
                project_id,
                f"evidence-restriction:{document_id}",
                idempotency_key,
                value,
                lambda: restrict_document(c, i, project_id, document_id, value),
            )

    @router.post("/evidence-corpora", response_model=EvidenceCorpus, status_code=201)
    def corpus_build(
        project_id: UUID,
        value: CorpusBuildInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            result = registry_command(
                c,
                i,
                project_id,
                "evidence-corpus-build",
                idempotency_key,
                value,
                lambda: build_corpus(c, i, project_id, value),
            )
            corpus = read_corpus(c, i, project_id, UUID(result["id"]))
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/evidence-corpora/{corpus.id}"
            )
            return corpus

    @router.get("/evidence-corpora/{corpus_id}", response_model=EvidenceCorpus)
    def corpus_detail(
        project_id: UUID, corpus_id: UUID, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (c, i):
            return read_corpus(c, i, project_id, corpus_id)

    @router.get("/evidence-corpus-current", response_model=CorpusHeadView)
    def current(
        project_id: UUID, response: Response, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (c, i):
            view = read_current_corpus(c, i, project_id)
            response.headers["ETag"] = f'"{view.activation_id or "empty"}"'
            return view

    @router.post("/evidence-corpus-activations", response_model=CorpusActivation, status_code=201)
    def activation(
        project_id: UUID,
        value: CorpusActivationInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        if_match: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            authorize_project(i, project_id, "admin")
            read_corpus(c, i, project_id, value.corpus_id)

            def execute():
                if if_match is None:
                    raise HTTPException(428)
                if if_match != f'"{value.expected_activation_id or "empty"}"':
                    raise HTTPException(412)
                return activate_corpus(c, i, project_id, value)

            result = registry_command(
                c, i, project_id, "evidence-corpus-activate", idempotency_key, value, execute
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/evidence-corpora/{result['corpus_id']}"
            )
            response.headers["ETag"] = f'"{result["id"]}"'
            return result

    @router.get(
        "/evidence-corpora/{corpus_id}/passages/{passage_id}", response_model=EvidencePassageView
    )
    def passage(
        project_id: UUID,
        corpus_id: UUID,
        passage_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_passage(c, i, project_id, corpus_id, passage_id)

    return router
