"""Thin canonical adapters for saved validated interpretations."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, Response

from canceros.context_contracts import ContextBuildInput
from canceros.context_runs import build_context
from canceros.identity import authenticate
from canceros.interpretation_contracts import InterpretationInput
from canceros.interpretation_runs import build_interpretation
from canceros.persistence import engine_for
from canceros.saved_runs import persist_validated, read_saved, reuse_exact
from canceros.saved_runs_contracts import (
    InterpretationPersistInput,
    PersistedInterpretation,
    SavedResultQuery,
)


def saved_routes(config, memberships):
    router = APIRouter(prefix="/api/v1/projects/{project_id}/patients/{patient_id}")

    @contextmanager
    def session(header):
        identity = authenticate(header, config, memberships)
        engine = engine_for(config)
        try:
            with engine.begin() as connection:
                yield connection, identity
        finally:
            engine.dispose()

    @router.post(
        "/states/{state_id}/interpretations/{interpretation_id}/saved-results",
        response_model=PersistedInterpretation,
        status_code=201,
    )
    def saved_create(
        project_id: UUID,
        patient_id: UUID,
        state_id: UUID,
        interpretation_id: UUID,
        value: InterpretationPersistInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            context = build_context(
                c,
                i,
                project_id,
                patient_id,
                ContextBuildInput(patient_id=patient_id, snapshot_id=state_id),
            )
            report = build_interpretation(
                context,
                InterpretationInput(context_snapshot_id=interpretation_id, mode="template"),
            )
            saved = persist_validated(c, i, project_id, context, report, idempotency_key)
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}"
                f"/saved-interpretations/{saved.id}"
            )
            return saved

    @router.get(
        "/saved-interpretations/{saved_id}", response_model=PersistedInterpretation
    )
    def saved_detail(
        project_id: UUID,
        patient_id: UUID,
        saved_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        _ = patient_id
        with session(authorization) as (c, i):
            return read_saved(c, i, project_id, saved_id)

    @router.post(
        "/states/{state_id}/saved-result-queries",
        response_model=PersistedInterpretation,
    )
    def saved_reuse(
        project_id: UUID,
        patient_id: UUID,
        state_id: UUID,
        value: SavedResultQuery,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            context = build_context(
                c,
                i,
                project_id,
                patient_id,
                ContextBuildInput(patient_id=patient_id, snapshot_id=state_id),
            )
            return reuse_exact(c, i, project_id, context, value)

    return router
