"""Thin canonical adapters for bounded template interpretations."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException

from canceros.context_runs import build_context
from canceros.identity import authenticate
from canceros.interpretation_contracts import InterpretationInput, InterpretationReport
from canceros.interpretation_runs import build_interpretation
from canceros.persistence import engine_for
from canceros.storage import PrivateStorage


def interpretation_routes(config, memberships):
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
        "/states/{state_id}/interpretations",
        response_model=InterpretationReport,
    )
    def interpretation_build(
        project_id: UUID,
        patient_id: UUID,
        state_id: UUID,
        value: InterpretationInput,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            from canceros.context_contracts import ContextBuildInput

            context_input = value.context_input or ContextBuildInput(
                patient_id=patient_id, snapshot_id=state_id
            )
            if context_input.patient_id != patient_id or context_input.snapshot_id != state_id:
                raise HTTPException(404)
            context = build_context(
                c,
                i,
                project_id,
                patient_id,
                context_input,
                storage=PrivateStorage(config),
            )
            return build_interpretation(context, value)

    return router
