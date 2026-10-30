"""Thin canonical adapters for bounded interpretation jobs."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, Response

from canceros.identity import authenticate
from canceros.interpretation_jobs import list_jobs, read_job, submit_job
from canceros.interpretation_jobs_contracts import (
    InterpretationJob,
    InterpretationJobInput,
    InterpretationJobPage,
)
from canceros.persistence import engine_for


def interpretation_job_routes(config, memberships):
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
        "/interpretation-jobs", response_model=InterpretationJob, status_code=201
    )
    def job_submit(
        project_id: UUID,
        patient_id: UUID,
        value: InterpretationJobInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            job = submit_job(c, i, project_id, patient_id, value, idempotency_key)
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}"
                f"/interpretation-jobs/{job.id}"
            )
            return job

    @router.get("/interpretation-jobs/{job_id}", response_model=InterpretationJob)
    def job_detail(
        project_id: UUID,
        patient_id: UUID,
        job_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_job(c, i, project_id, patient_id, job_id)

    @router.get("/interpretation-jobs", response_model=InterpretationJobPage)
    def job_list(
        project_id: UUID,
        patient_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return InterpretationJobPage(items=tuple(list_jobs(c, i, project_id, patient_id)))

    return router
