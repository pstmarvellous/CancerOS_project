"""Private state assembly reads and explicit engineering review/publication commands."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, Query, Response

from canceros.identity import authenticate
from canceros.persistence import engine_for
from canceros.storage import PrivateStorage
from canceros.synthetic_contracts import GeneratedMesh
from canceros.synthetic_geometry import (
    FixtureRun,
    FixtureRunInput,
    GeometryResult,
    authorize_fixture_run,
    read_fixture_run,
    read_generated_mesh,
    read_geometry_result,
)
from canceros.twin_states import (
    BranchInput,
    BranchReport,
    Publication,
    PublishInput,
    ReviewEvent,
    ReviewInput,
    StatePage,
    StateView,
    create_branch,
    list_states,
    publish_state,
    read_branch,
    read_state,
    review_state,
)


def state_routes(config, memberships):
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

    @router.post("/branches", response_model=BranchReport, status_code=201)
    def post_branch(
        project_id: UUID,
        patient_id: UUID,
        value: BranchInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            result = create_branch(
                c, i, project_id, patient_id, value, PrivateStorage(config), idempotency_key
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/branches/{result.id}"
            )
            return result

    @router.get("/branches/{branch_id}", response_model=BranchReport)
    def get_branch(
        project_id: UUID,
        patient_id: UUID,
        branch_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_branch(c, i, project_id, patient_id, branch_id)

    @router.get("/states", response_model=StatePage)
    def get_states(
        project_id: UUID,
        patient_id: UUID,
        branch_id: UUID | None = None,
        published_only: bool = False,
        cursor: str | None = Query(default=None, max_length=128),
        limit: int = Query(default=25, ge=1, le=64),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return list_states(
                c,
                i,
                project_id,
                patient_id,
                branch_id=branch_id,
                published_only=published_only,
                cursor=cursor,
                limit=limit,
            )

    @router.get("/states/{state_id}", response_model=StateView)
    def get_state(
        project_id: UUID,
        patient_id: UUID,
        state_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_state(c, i, project_id, patient_id, state_id)

    @router.post("/states/{state_id}/reviews", response_model=ReviewEvent, status_code=201)
    def post_state_review(
        project_id: UUID,
        patient_id: UUID,
        state_id: UUID,
        value: ReviewInput,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return review_state(c, i, project_id, patient_id, state_id, value, idempotency_key)

    @router.post("/states/{state_id}/publications", response_model=Publication, status_code=201)
    def post_state_publication(
        project_id: UUID,
        patient_id: UUID,
        state_id: UUID,
        value: PublishInput,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return publish_state(c, i, project_id, patient_id, state_id, value, idempotency_key)

    @router.post("/simulation-fixture-runs", response_model=FixtureRun, status_code=201)
    def post_fixture_run(
        project_id: UUID,
        patient_id: UUID,
        value: FixtureRunInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            result = authorize_fixture_run(
                c, i, project_id, patient_id, value, PrivateStorage(config), idempotency_key, config
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/simulation-fixture-runs/{result.id}"
            )
            return result

    @router.get("/simulation-fixture-runs/{run_id}", response_model=FixtureRun)
    def get_fixture_run(
        project_id: UUID,
        patient_id: UUID,
        run_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_fixture_run(c, i, project_id, patient_id, run_id)

    @router.get("/synthetic-geometry-results/{result_id}", response_model=GeometryResult)
    def get_geometry_result(
        project_id: UUID,
        patient_id: UUID,
        result_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_geometry_result(c, i, project_id, patient_id, result_id)

    @router.get("/synthetic-geometry-results/{result_id}/mesh", response_model=GeneratedMesh)
    def get_geometry_mesh(
        project_id: UUID,
        patient_id: UUID,
        result_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_generated_mesh(
                c, i, project_id, patient_id, result_id, PrivateStorage(config)
            )

    return router
