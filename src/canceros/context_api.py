"""Thin canonical adapters for snapshot-bound interpretation contexts."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header

from canceros.context_contracts import ContextBuildInput, InterpretationContext
from canceros.context_runs import build_context, context_export_view, record_context_build
from canceros.identity import authenticate
from canceros.persistence import engine_for


def context_routes(config, memberships):
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
        "/interpretation-contexts",
        response_model=InterpretationContext,
    )
    def context_build(
        project_id: UUID,
        patient_id: UUID,
        value: ContextBuildInput,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            context = build_context(c, i, project_id, patient_id, value)
            record_context_build(c, project_id, context)
            return context

    @router.post(
        "/interpretation-contexts/export-view",
        response_model=dict,
    )
    def export_view(
        project_id: UUID,
        patient_id: UUID,
        value: ContextBuildInput,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            context = build_context(c, i, project_id, patient_id, value)
            return context_export_view(context)

    return router
