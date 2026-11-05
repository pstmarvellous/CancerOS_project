"""Authorized research workspace adapters. Tokens still use the existing verifier."""

import hashlib
from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, Query
from sqlalchemy import text

from canceros.clinical_ingestion import BatchReport
from canceros.contracts import Contract, Hash
from canceros.identity import authenticate, authorize_project
from canceros.patient_linkage import authorize_patient
from canceros.persistence import engine_for, science_hash
from canceros.research_workspace import (
    ManualObservationInput,
    ResearchCaseInput,
    ResearchCasePage,
    ResearchCaseSources,
    ResearchCaseView,
    ResearchProfileUpdate,
    WorkspaceView,
    _creation_gate,
    case_sources,
    create_case,
    manual_observation,
    research_cases,
    research_profile,
    update_profile,
    workspace,
)
from canceros.source_registry import SourceAction, registry_command, require_source_action
from canceros.storage import PrivateStorage


class ManualFingerprint(Contract):
    sha256: Hash


def research_routes(config, memberships):
    router = APIRouter(prefix="/api/v1")

    @contextmanager
    def session(header):
        identity = authenticate(header, config, memberships)
        engine = engine_for(config)
        try:
            with engine.begin() as connection:
                yield connection, identity
        finally:
            engine.dispose()

    @router.get("/workspace", response_model=WorkspaceView)
    def authorized_workspace(authorization: str | None = Header(default=None)):
        with session(authorization) as (c, i):
            return workspace(c, i)

    @router.get("/projects/{project_id}/research-case-sources", response_model=ResearchCaseSources)
    def sources(project_id: UUID, authorization: str | None = Header(default=None)):
        with session(authorization) as (c, i):
            return case_sources(c, i, project_id, config)

    @router.get("/projects/{project_id}/research-cases", response_model=ResearchCasePage)
    def cases(
        project_id: UUID,
        search: str = Query(default="", max_length=100),
        limit: int = Query(default=25, ge=1, le=100),
        cursor: UUID | None = None,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return research_cases(c, i, project_id, search, limit, cursor)

    @router.post(
        "/projects/{project_id}/research-cases", response_model=ResearchCaseView, status_code=201
    )
    def create(
        project_id: UUID,
        value: ResearchCaseInput,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            _creation_gate(c, i, project_id, value.source_version_id)
            result = registry_command(
                c,
                i,
                project_id,
                "research-case-create",
                idempotency_key,
                value,
                lambda: create_case(c, i, project_id, value, config),
            )
            return research_profile(c, i, project_id, UUID(result["patient_id"]))

    @router.get(
        "/projects/{project_id}/patients/{patient_id}/research-profile",
        response_model=ResearchCaseView,
    )
    def profile(
        project_id: UUID, patient_id: UUID, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (c, i):
            return research_profile(c, i, project_id, patient_id)

    @router.post(
        "/projects/{project_id}/patients/{patient_id}/research-profile",
        response_model=ResearchCaseView,
    )
    def save_profile(
        project_id: UUID,
        patient_id: UUID,
        value: ResearchProfileUpdate,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            authorize_project(i, project_id, "admin")
            authorize_patient(c, i, project_id, patient_id, edit=True)
            c.execute(
                text(
                    "SELECT id FROM source.research_patients WHERE project_id=:p AND id=:u FOR UPDATE"
                ),
                {"p": project_id, "u": patient_id},
            ).one()
            current = research_profile(c, i, project_id, patient_id)
            _creation_gate(c, i, project_id, current.source_version_id)
            registry_command(
                c,
                i,
                project_id,
                "research-profile:" + str(patient_id),
                idempotency_key,
                value,
                lambda: update_profile(c, i, project_id, patient_id, value),
            )
            return research_profile(c, i, project_id, patient_id)

    @router.post(
        "/projects/{project_id}/patients/{patient_id}/manual-observations",
        response_model=BatchReport,
        status_code=201,
    )
    def manual(
        project_id: UUID,
        patient_id: UUID,
        value: ManualObservationInput,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            authorize_project(i, project_id, "admin")
            authorize_patient(c, i, project_id, patient_id, edit=True)
            c.execute(
                text(
                    "SELECT id FROM source.research_patients WHERE project_id=:p AND id=:u FOR UPDATE"
                ),
                {"p": project_id, "u": patient_id},
            ).one()
            profile = research_profile(c, i, project_id, patient_id)
            _creation_gate(c, i, project_id, profile.source_version_id)
            require_source_action(
                c, i, project_id, profile.source_version_id, SourceAction.DERIVATIVE
            )
            data = value.model_dump(mode="json")
            if value.observation.kind == "note":
                # Idempotency binds secret content without storing it in command metadata.
                data["observation"]["text"] = hashlib.sha256(
                    value.observation.text.get_secret_value().encode()
                ).hexdigest()
            result = registry_command(
                c,
                i,
                project_id,
                "manual-observation:" + str(patient_id),
                idempotency_key,
                ManualFingerprint(sha256=science_hash(data)),
                lambda: manual_observation(
                    c, i, project_id, patient_id, value, idempotency_key, PrivateStorage(config)
                ),
            )
            return BatchReport.model_validate(result)

    return router
