"""Thin project/patient HTTP adapters for staged synthetic clinical source imports."""

from contextlib import contextmanager
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Response
from pydantic import Field
from sqlalchemy import text

from canceros.clinical_contracts import ClinicalRecord
from canceros.clinical_ingestion import (
    BatchCommand,
    BatchReport,
    ClinicalSourceReceipt,
    ClinicalSourceUpload,
    RetractionInput,
    RetractionReceipt,
    accept_batch,
    read_record,
    retract_record,
    upload_source,
    validate_batch,
)
from canceros.contracts import Contract, TimeDomain, TimelineOrigin
from canceros.evaluation_splits import InheritedAssignment, inherited_assignment
from canceros.identity import authenticate
from canceros.lineage import (
    ResourceLineage,
    WithdrawalInput,
    WithdrawalReceipt,
    lineage_detail,
    withdraw_resource,
)
from canceros.metadata_adapters import AdapterInput, AdapterReport, run_adapter
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import engine_for
from canceros.quality import (
    QualityRequest,
    QualityView,
    create_quality_report,
    read_quality_report,
    revalidate_source,
)
from canceros.source_registry import registry_command
from canceros.storage import PrivateStorage


class OriginInput(Contract):
    reference_meaning: Annotated[str, Field(min_length=1, max_length=200)]
    time_domain: TimeDomain


def clinical_routes(config, memberships):
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

    @router.get("/evaluation-splits/{split_id}/assignment", response_model=InheritedAssignment)
    def assignment(
        project_id: UUID,
        patient_id: UUID,
        split_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return inherited_assignment(connection, identity, project_id, patient_id, split_id)

    @router.post("/quality-reports", response_model=QualityView, status_code=201)
    def quality_report(
        project_id: UUID,
        patient_id: UUID,
        value: QualityRequest,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            authorize_patient(connection, identity, project_id, patient_id, edit=True)
            reference = registry_command(
                connection,
                identity,
                project_id,
                "quality:" + str(patient_id),
                idempotency_key,
                value,
                lambda: create_quality_report(
                    connection, identity, project_id, patient_id, value.expected_revision
                ),
                minimum="editor",
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/quality-reports/{reference['id']}"
            )
            return read_quality_report(
                connection, identity, project_id, patient_id, UUID(reference["id"])
            )

    @router.get("/quality-reports/{report_id}", response_model=QualityView)
    def quality_detail(
        project_id: UUID,
        patient_id: UUID,
        report_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_quality_report(connection, identity, project_id, patient_id, report_id)

    @router.post("/quality-revalidations", response_model=QualityView, status_code=201)
    def revalidate(
        project_id: UUID,
        patient_id: UUID,
        value: BatchCommand,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            authorize_patient(connection, identity, project_id, patient_id, edit=True)
            reference = registry_command(
                connection,
                identity,
                project_id,
                "revalidate:" + str(patient_id),
                idempotency_key,
                value,
                lambda: revalidate_source(
                    connection, identity, project_id, patient_id, value, PrivateStorage(config)
                ),
                minimum="editor",
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/quality-reports/{reference['id']}"
            )
            return read_quality_report(
                connection, identity, project_id, patient_id, UUID(reference["id"])
            )

    @router.get("/resources/{resource_id}/provenance", response_model=ResourceLineage)
    def provenance(
        project_id: UUID,
        patient_id: UUID,
        resource_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return lineage_detail(connection, identity, project_id, patient_id, resource_id)

    @router.post("/resources/{resource_id}/withdrawals", response_model=WithdrawalReceipt)
    def withdraw(
        project_id: UUID,
        patient_id: UUID,
        resource_id: UUID,
        value: WithdrawalInput,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return registry_command(
                connection,
                identity,
                project_id,
                "withdraw:" + str(resource_id),
                idempotency_key,
                value,
                lambda: withdraw_resource(
                    connection, identity, project_id, patient_id, resource_id, value
                ),
            )

    @router.post("/metadata-adapter-runs", response_model=AdapterReport, status_code=201)
    def adapt(
        project_id: UUID,
        patient_id: UUID,
        value: AdapterInput,
        response: Response,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            report = run_adapter(
                connection, identity, project_id, patient_id, value, PrivateStorage(config)
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/metadata-adapter-runs/{report.id}"
            )
            return report

    @router.get("/metadata-adapter-runs/{run_id}", response_model=AdapterReport)
    def adapter_detail(
        project_id: UUID,
        patient_id: UUID,
        run_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        from fastapi import HTTPException

        with session(authorization) as (connection, identity):
            authorize_patient(connection, identity, project_id, patient_id, edit=True)
            result = connection.execute(
                text(
                    "SELECT report FROM source.adapter_runs WHERE project_id=:p AND patient_id=:u AND id=:id"
                ),
                {"p": project_id, "u": patient_id, "id": run_id},
            ).scalar_one_or_none()
            if result is None:
                raise HTTPException(404)
            return AdapterReport.model_validate(result)

    @router.post("/timeline-origins", response_model=TimelineOrigin, status_code=201)
    def origin(
        project_id: UUID,
        patient_id: UUID,
        value: OriginInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            authorize_patient(connection, identity, project_id, patient_id, edit=True)

            def execute():
                result = TimelineOrigin(
                    id=uuid4(), project_id=project_id, patient_id=patient_id, **value.model_dump()
                )
                connection.execute(
                    text(
                        "INSERT INTO source.timeline_origins(id,project_id,patient_id,reference_meaning,time_domain) VALUES(:id,:project_id,:patient_id,:reference_meaning,:time_domain)"
                    ),
                    result.model_dump(),
                )
                audit(connection, project_id, result.id, "TIMELINE_ORIGIN_CREATED")
                return result

            result = TimelineOrigin.model_validate(
                registry_command(
                    connection,
                    identity,
                    project_id,
                    "origin:" + str(patient_id),
                    idempotency_key,
                    value,
                    execute,
                )
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/timeline-origins/{result.id}"
            )
            return result

    @router.get("/timeline-origins/{origin_id}", response_model=TimelineOrigin)
    def origin_detail(
        project_id: UUID,
        patient_id: UUID,
        origin_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        from fastapi import HTTPException

        with session(authorization) as (connection, identity):
            authorize_patient(connection, identity, project_id, patient_id, edit=True)
            row = (
                connection.execute(
                    text(
                        "SELECT id,project_id,patient_id,reference_meaning,time_domain FROM source.timeline_origins WHERE project_id=:p AND patient_id=:u AND id=:id"
                    ),
                    {"p": project_id, "u": patient_id, "id": origin_id},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise HTTPException(404)
            return TimelineOrigin.model_validate(dict(row))

    @router.post(
        "/clinical-source-artifacts", response_model=ClinicalSourceReceipt, status_code=201
    )
    def upload(
        project_id: UUID,
        patient_id: UUID,
        value: ClinicalSourceUpload,
        response: Response,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            receipt = upload_source(
                connection, identity, project_id, patient_id, value, PrivateStorage(config)
            )
            # Source bytes remain private: no download URL is returned.
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/clinical-source-artifacts/{receipt.artifact_id}"
            )
            return receipt

    @router.get("/clinical-source-artifacts/{artifact_id}", response_model=ClinicalSourceReceipt)
    def source_detail(
        project_id: UUID,
        patient_id: UUID,
        artifact_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        from fastapi import HTTPException

        with session(authorization) as (connection, identity):
            authorize_patient(connection, identity, project_id, patient_id, edit=True)
            row = connection.execute(
                text(
                    "SELECT a.sha256 FROM source.ingestion_artifacts i JOIN ops.artifacts a ON (a.project_id,a.id)=(i.project_id,i.id) WHERE i.project_id=:p AND i.patient_id=:u AND i.id=:id"
                ),
                {"p": project_id, "u": patient_id, "id": artifact_id},
            ).one_or_none()
            if row is None:
                raise HTTPException(404)
            return ClinicalSourceReceipt(
                artifact_id=artifact_id, patient_id=patient_id, sha256=row.sha256
            )

    @router.post("/observation-batches/validations", response_model=BatchReport)
    def validate(
        project_id: UUID,
        patient_id: UUID,
        value: BatchCommand,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return validate_batch(
                connection, identity, project_id, patient_id, value, PrivateStorage(config)
            )[0]

    @router.post("/observation-batches", response_model=BatchReport)
    def accept(
        project_id: UUID,
        patient_id: UUID,
        value: BatchCommand,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return accept_batch(
                connection,
                identity,
                project_id,
                patient_id,
                value,
                idempotency_key,
                PrivateStorage(config),
            )

    @router.get("/observations/{record_id}", response_model=ClinicalRecord)
    def observation(
        project_id: UUID,
        patient_id: UUID,
        record_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            return read_record(connection, identity, project_id, patient_id, record_id)

    @router.post("/observations/{record_id}/retractions", response_model=RetractionReceipt)
    def retract(
        project_id: UUID,
        patient_id: UUID,
        record_id: UUID,
        value: RetractionInput,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (connection, identity):
            authorize_patient(connection, identity, project_id, patient_id, edit=True)
            return registry_command(
                connection,
                identity,
                project_id,
                "retract:" + str(record_id),
                idempotency_key,
                value,
                lambda: retract_record(
                    connection, identity, project_id, patient_id, record_id, value
                ),
                minimum="editor",
            )

    return router
