"""Project-scoped source registry HTTP adapter; all writes require administrator."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, Response

from canceros.identity import authenticate
from canceros.persistence import engine_for
from canceros.source_registry import (
    RightsReview,
    RightsReviewInput,
    SourceAction,
    SourceCapability,
    SourceVersion,
    SourceVersionInput,
    add_review,
    add_source,
    capability,
    get_source,
    registry_command,
)


def source_routes(config, memberships):
    router = APIRouter(prefix="/api/v1/projects/{project_id}/sources")

    @contextmanager
    def session(header):
        identity = authenticate(header, config, memberships)
        engine = engine_for(config)
        try:
            with engine.begin() as connection:
                yield connection, identity
        finally:
            engine.dispose()

    @router.post("", response_model=SourceVersion, status_code=201)
    def create(
        project_id: UUID,
        value: SourceVersionInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            source = SourceVersion.model_validate(
                registry_command(
                    connection,
                    identity,
                    project_id,
                    "create_source",
                    idempotency_key,
                    value,
                    lambda: add_source(connection, identity, project_id, value),
                )
            )
            response.headers["Location"] = f"/api/v1/projects/{project_id}/sources/{source.id}"
            return source

    @router.get("/{source_id}", response_model=SourceVersion)
    def detail(project_id: UUID, source_id: UUID, authorization: str | None = Header(default=None)):
        with session(authorization) as (connection, identity):
            return get_source(connection, identity, project_id, source_id)

    @router.post("/{source_id}/rights-reviews", response_model=RightsReview, status_code=201)
    def review(
        project_id: UUID,
        source_id: UUID,
        value: RightsReviewInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = RightsReview.model_validate(
                registry_command(
                    connection,
                    identity,
                    project_id,
                    "review:" + str(source_id),
                    idempotency_key,
                    value,
                    lambda: add_review(connection, identity, project_id, source_id, value),
                )
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/sources/{source_id}/capabilities/{value.action.value}"
            )
            return result

    @router.get("/{source_id}/capabilities/{action}", response_model=SourceCapability)
    def permissions(
        project_id: UUID,
        source_id: UUID,
        action: SourceAction,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return capability(connection, identity, project_id, source_id, action)

    return router
