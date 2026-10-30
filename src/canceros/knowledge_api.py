"""Thin canonical adapters for source-linked relationships and local concepts."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, Response

from canceros.identity import authenticate
from canceros.knowledge_runs import (
    ConceptInput,
    ConceptView,
    KnowledgeTraversal,
    RelationshipCommand,
    RelationshipPage,
    RelationshipView,
    _scope,
    create_concept,
    create_relationship,
    read_concept,
    read_relationship,
    traverse_relationships,
)
from canceros.persistence import engine_for
from canceros.source_registry import registry_command


def knowledge_routes(config, memberships):
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

    @router.post("/clinical-concepts", response_model=ConceptView, status_code=201)
    def concept_create(
        project_id: UUID,
        value: ConceptInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            result = registry_command(
                c,
                i,
                project_id,
                "local-concept",
                idempotency_key,
                value,
                lambda: create_concept(c, i, project_id, value),
            )
            concept = read_concept(c, i, project_id, UUID(result["id"]))
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/clinical-concepts/{concept.id}"
            )
            return concept

    @router.get("/clinical-concepts/{concept_id}", response_model=ConceptView)
    def concept_detail(
        project_id: UUID, concept_id: UUID, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (c, i):
            return read_concept(c, i, project_id, concept_id)

    def command(c, i, p, u, value, key):
        _scope(c, i, p, u, write=True)
        result = registry_command(
            c, i, p, f"relationship:{u}", key, value, lambda: create_relationship(c, i, p, u, value)
        )
        return read_relationship(c, i, p, u, UUID(result["id"]))

    @router.post(
        "/patients/{patient_id}/relationships", response_model=RelationshipView, status_code=201
    )
    def patient_relationship_create(
        project_id: UUID,
        patient_id: UUID,
        value: RelationshipCommand,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            result = command(c, i, project_id, patient_id, value, idempotency_key)
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/relationships/{result.id}"
            )
            return result

    @router.get(
        "/patients/{patient_id}/relationships/{relationship_id}", response_model=RelationshipView
    )
    def patient_relationship_detail(
        project_id: UUID,
        patient_id: UUID,
        relationship_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_relationship(c, i, project_id, patient_id, relationship_id)

    @router.post("/patients/{patient_id}/relationship-queries", response_model=RelationshipPage)
    def patient_relationship_query(
        project_id: UUID,
        patient_id: UUID,
        value: KnowledgeTraversal,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return traverse_relationships(c, i, project_id, patient_id, value)

    @router.post("/concept-relationships", response_model=RelationshipView, status_code=201)
    def concept_relationship_create(
        project_id: UUID,
        value: RelationshipCommand,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            result = command(c, i, project_id, None, value, idempotency_key)
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/concept-relationships/{result.id}"
            )
            return result

    @router.get("/concept-relationships/{relationship_id}", response_model=RelationshipView)
    def concept_relationship_detail(
        project_id: UUID, relationship_id: UUID, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (c, i):
            return read_relationship(c, i, project_id, None, relationship_id)

    @router.post("/concept-relationship-queries", response_model=RelationshipPage)
    def concept_relationship_query(
        project_id: UUID,
        value: KnowledgeTraversal,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return traverse_relationships(c, i, project_id, None, value)

    return router
