"""Administrative cohort partitioning and explicit leakage audits."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, Response

from canceros.evaluation_splits import (
    LeakageAudit,
    SplitInput,
    SplitManifest,
    freeze_split,
    load_split,
    split_audit,
)
from canceros.identity import authenticate, authorize_project
from canceros.persistence import engine_for
from canceros.source_registry import registry_command


def evaluation_routes(config, memberships):
    router = APIRouter(prefix="/api/v1/projects/{project_id}/evaluation-splits")

    @contextmanager
    def session(header):
        identity = authenticate(header, config, memberships)
        engine = engine_for(config)
        try:
            with engine.begin() as connection:
                yield connection, identity
        finally:
            engine.dispose()

    @router.post("", response_model=SplitManifest, status_code=201)
    def freeze(
        project_id: UUID,
        value: SplitInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = SplitManifest.model_validate(
                registry_command(
                    connection,
                    identity,
                    project_id,
                    "freeze_split",
                    idempotency_key,
                    value,
                    lambda: freeze_split(connection, identity, project_id, value),
                )
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/evaluation-splits/{result.id}"
            )
            return result

    @router.get("/{split_id}", response_model=SplitManifest)
    def detail(project_id: UUID, split_id: UUID, authorization: str | None = Header(default=None)):
        with session(authorization) as (connection, identity):
            authorize_project(identity, project_id, "admin")
            return load_split(connection, project_id, split_id)

    @router.get("/{split_id}/leakage", response_model=LeakageAudit)
    def leakage(project_id: UUID, split_id: UUID, authorization: str | None = Header(default=None)):
        with session(authorization) as (connection, identity):
            return split_audit(connection, identity, project_id, split_id)

    @router.post("/{split_id}/leakage-audits", response_model=LeakageAudit)
    def audit(project_id: UUID, split_id: UUID, authorization: str | None = Header(default=None)):
        with session(authorization) as (connection, identity):
            return split_audit(connection, identity, project_id, split_id, persist=True)

    return router
