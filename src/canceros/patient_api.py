"""Administrative private-linkage commands; no plaintext lookup/export endpoint."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, Response

from canceros.clinical_contracts import ClinicalDictionary, clinical_dictionary
from canceros.identity import authenticate, authorize_project
from canceros.patient_linkage import (
    LinkageInput,
    LinkageStatus,
    PatientIdentity,
    PersonLinkEvent,
    PersonLinkInput,
    append_person_link,
    mapping_summary,
    resolve_mapping,
    rotate_mapping,
)
from canceros.persistence import engine_for
from canceros.source_registry import registry_command


def patient_routes(config, memberships):
    router = APIRouter(prefix="/api/v1/projects/{project_id}")

    @router.get("/dictionaries/clinical", response_model=ClinicalDictionary)
    def dictionary(project_id: UUID, authorization: str | None = Header(default=None)):
        identity = authenticate(authorization, config, memberships)
        authorize_project(identity, project_id)
        return clinical_dictionary()

    @contextmanager
    def session(header):
        identity = authenticate(header, config, memberships)
        engine = engine_for(config)
        try:
            with engine.begin() as connection:
                yield connection, identity
        finally:
            engine.dispose()

    @router.get("/patient-linkage/status", response_model=LinkageStatus)
    def status(project_id: UUID, authorization: str | None = Header(default=None)):
        with session(authorization) as (_, identity):
            authorize_project(identity, project_id, "admin")
            enabled = bool(config.linkage_active_key)
            return LinkageStatus(
                enabled=enabled,
                next_action="Resolve only permitted source identities"
                if enabled
                else "Install a private versioned linkage key ring",
            )

    @router.post("/source-patient-resolutions", response_model=PatientIdentity)
    def resolve(
        project_id: UUID, value: LinkageInput, authorization: str | None = Header(default=None)
    ):
        # Naturally idempotent by private namespace/digest, with namespace lock.
        with session(authorization) as (connection, identity):
            return resolve_mapping(connection, identity, project_id, value, config)

    @router.get("/patient-mappings/{mapping_id}", response_model=PatientIdentity)
    def detail(
        project_id: UUID, mapping_id: UUID, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (connection, identity):
            return mapping_summary(connection, identity, project_id, mapping_id)

    @router.post("/patient-mappings/{mapping_id}/key-rotations", response_model=PatientIdentity)
    def rotate(
        project_id: UUID, mapping_id: UUID, authorization: str | None = Header(default=None)
    ):
        with session(authorization) as (connection, identity):
            return rotate_mapping(connection, identity, project_id, mapping_id, config)

    @router.post("/person-link-events", response_model=PersonLinkEvent, status_code=201)
    def link(
        project_id: UUID,
        value: PersonLinkInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            result = PersonLinkEvent.model_validate(
                registry_command(
                    connection,
                    identity,
                    project_id,
                    "person_link",
                    idempotency_key,
                    value,
                    lambda: append_person_link(connection, identity, project_id, value),
                )
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/person-link-events/{result.id}"
            )
            return result

    @router.get("/person-link-events/{event_id}", response_model=PersonLinkEvent)
    def link_detail(
        project_id: UUID, event_id: UUID, authorization: str | None = Header(default=None)
    ):
        from fastapi import HTTPException
        from sqlalchemy import text

        with session(authorization) as (connection, identity):
            authorize_project(identity, project_id, "admin")
            row = (
                connection.execute(
                    text("SELECT * FROM source.person_link_events WHERE project_id=:p AND id=:id"),
                    {"p": project_id, "id": event_id},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise HTTPException(404)
            return PersonLinkEvent.model_validate(
                {
                    **{k: row[k] for k in PersonLinkInput.model_fields},
                    "confidence": format(row["confidence"], "f"),
                    "id": row["id"],
                    "reviewed_by": row["reviewed_by"],
                    "reviewed_at": row["reviewed_at"],
                }
            )

    return router
