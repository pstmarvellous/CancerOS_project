"""Thin canonical adapters for the mandatory grounding publication gate."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header

from canceros.context_contracts import ContextBuildInput
from canceros.context_runs import build_context
from canceros.grounding_contracts import GroundingCheckInput, GroundingReport
from canceros.grounding_runs import require_published, validate_publication
from canceros.identity import authenticate
from canceros.interpretation_contracts import InterpretationInput
from canceros.interpretation_runs import build_interpretation
from canceros.persistence import engine_for


def grounding_routes(config, memberships):
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
        "/states/{state_id}/interpretations/{interpretation_id}/grounding",
        response_model=GroundingReport,
    )
    def grounding_check(
        project_id: UUID,
        patient_id: UUID,
        state_id: UUID,
        interpretation_id: UUID,
        value: GroundingCheckInput,
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
            grounded = validate_publication(context, report)
            require_published(grounded)
            return grounded

    return router
