"""Private state assembly reads and explicit engineering review/publication commands."""

from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Header, Query, Response

from canceros.clinical_generation_runs import ClinicalGenerationReport, read_clinical_batch
from canceros.dependent_updates import (
    DependentUpdateInput,
    DependentUpdateReceipt,
    DependentUpdateView,
    dispatch_update,
    read_update_view,
)
from canceros.eligibility_checks import (
    EligibilityCheckInput,
    EligibilityReport,
    check_eligibility,
    read_eligibility,
)
from canceros.forecast_baselines import ForecastReport
from canceros.forecast_runs import ForecastQuery, query_forecast
from canceros.fusion_runs import FusionQuery, query_fusion
from canceros.identity import authenticate
from canceros.persistence import engine_for
from canceros.sampling import SampledObservations
from canceros.scenario_geometry import (
    GeometryValidationInput,
    RunGeometryValidation,
    validate_run_geometry,
)
from canceros.simulation_execution import (
    CompletionReport,
    CurrentRunView,
    PublishRunInput,
    RunPublication,
    publish_completion,
    read_completion,
    read_current_run,
)
from canceros.simulation_runs import (
    ConfigVersion,
    QueueRunInput,
    RunTargetSummary,
    SaveConfigInput,
    SimulationRun,
    preview_config_schedule,
    queue_run,
    read_config,
    read_run,
    read_run_sampling,
    read_run_targets,
    save_config,
)
from canceros.state_fusion import FusionReport
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
from canceros.temporal_trends import TrendReport
from canceros.timeline_runs import TimelinePage, TimelineQuery, query_timeline
from canceros.trend_runs import TrendQuery, query_trends
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

    @router.post("/forecast-queries", response_model=ForecastReport)
    def post_forecast_query(
        project_id: UUID,
        patient_id: UUID,
        value: ForecastQuery,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return query_forecast(c, i, project_id, patient_id, value)

    @router.post("/dependent-updates", response_model=DependentUpdateReceipt, status_code=201)
    def post_dependent_update(
        project_id: UUID,
        patient_id: UUID,
        value: DependentUpdateInput,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return dispatch_update(
                c, i, project_id, patient_id, value, idempotency_key, PrivateStorage(config)
            )

    @router.get("/dependent-updates/latest", response_model=DependentUpdateView)
    def get_dependent_update(
        project_id: UUID,
        patient_id: UUID,
        branch_id: UUID | None = None,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_update_view(c, i, project_id, patient_id, branch_id)

    @router.post("/fusion-queries", response_model=FusionReport)
    def post_fusion_query(
        project_id: UUID,
        patient_id: UUID,
        value: FusionQuery,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return query_fusion(c, i, project_id, patient_id, value)

    @router.post("/trend-queries", response_model=TrendReport)
    def post_trend_query(
        project_id: UUID,
        patient_id: UUID,
        value: TrendQuery,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return query_trends(c, i, project_id, patient_id, value)

    @router.post("/timeline-queries", response_model=TimelinePage)
    def post_timeline_query(
        project_id: UUID,
        patient_id: UUID,
        value: TimelineQuery,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return query_timeline(c, i, project_id, patient_id, value)

    @router.get("/simulation-completions/{completion_id}", response_model=CompletionReport)
    def get_completion(
        project_id: UUID,
        patient_id: UUID,
        completion_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_completion(c, i, project_id, patient_id, completion_id)

    @router.post(
        "/simulation-completions/{completion_id}/publications",
        response_model=RunPublication,
        status_code=201,
    )
    def post_complete_publication(
        project_id: UUID,
        patient_id: UUID,
        completion_id: UUID,
        value: PublishRunInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            result = publish_completion(
                c,
                i,
                project_id,
                patient_id,
                completion_id,
                value,
                PrivateStorage(config),
                idempotency_key,
                config,
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/branches/{result.branch_id}/current-simulation"
            )
            return result

    @router.get("/branches/{branch_id}/current-simulation", response_model=CurrentRunView)
    def get_current_simulation(
        project_id: UUID,
        patient_id: UUID,
        branch_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_current_run(c, i, project_id, patient_id, branch_id)

    @router.get("/generated-clinical-batches/{batch_id}", response_model=ClinicalGenerationReport)
    def get_clinical_batch(
        project_id: UUID,
        patient_id: UUID,
        batch_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_clinical_batch(c, i, project_id, patient_id, batch_id)

    @router.get(
        "/simulation-configs/{config_id}/schedule-preview", response_model=SampledObservations
    )
    def get_schedule_preview(
        project_id: UUID,
        patient_id: UUID,
        config_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return preview_config_schedule(c, i, project_id, patient_id, config_id)

    @router.get("/simulation-runs/{run_id}/sampling", response_model=SampledObservations)
    def get_run_sampling(
        project_id: UUID,
        patient_id: UUID,
        run_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_run_sampling(c, i, project_id, patient_id, run_id)

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

    @router.post(
        "/branches/{branch_id}/simulation-configs", response_model=ConfigVersion, status_code=201
    )
    def post_simulation_config(
        project_id: UUID,
        patient_id: UUID,
        branch_id: UUID,
        value: SaveConfigInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            result = save_config(
                c,
                i,
                project_id,
                patient_id,
                branch_id,
                value,
                PrivateStorage(config),
                idempotency_key,
                config,
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/simulation-configs/{result.id}"
            )
            return result

    @router.get("/simulation-configs/{config_id}", response_model=ConfigVersion)
    def get_simulation_config(
        project_id: UUID,
        patient_id: UUID,
        config_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_config(c, i, project_id, patient_id, config_id)

    @router.post(
        "/branches/{branch_id}/simulation-runs", response_model=SimulationRun, status_code=201
    )
    def post_simulation_run(
        project_id: UUID,
        patient_id: UUID,
        branch_id: UUID,
        value: QueueRunInput,
        response: Response,
        idempotency_key: str = Header(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$"),
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            result = queue_run(
                c,
                i,
                project_id,
                patient_id,
                branch_id,
                value,
                PrivateStorage(config),
                idempotency_key,
                config,
            )
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/simulation-runs/{result.id}"
            )
            return result

    @router.get("/simulation-runs/{run_id}", response_model=SimulationRun)
    def get_simulation_run(
        project_id: UUID,
        patient_id: UUID,
        run_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_run(c, i, project_id, patient_id, run_id)

    @router.post("/eligibility-checks", response_model=EligibilityReport, status_code=201)
    def post_eligibility_check(
        project_id: UUID,
        patient_id: UUID,
        value: EligibilityCheckInput,
        response: Response,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            result = check_eligibility(c, i, project_id, patient_id, value)
            response.headers["Location"] = (
                f"/api/v1/projects/{project_id}/patients/{patient_id}/eligibility-checks/{result.id}"
            )
            return result

    @router.get("/eligibility-checks/{check_id}", response_model=EligibilityReport)
    def get_eligibility_check(
        project_id: UUID,
        patient_id: UUID,
        check_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_eligibility(c, i, project_id, patient_id, check_id)

    @router.post(
        "/simulation-runs/{run_id}/geometry-validation", response_model=RunGeometryValidation
    )
    def post_run_geometry_validation(
        project_id: UUID,
        patient_id: UUID,
        run_id: UUID,
        value: GeometryValidationInput,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return validate_run_geometry(c, i, project_id, patient_id, run_id, value)

    @router.get("/simulation-runs/{run_id}/targets", response_model=RunTargetSummary)
    def get_run_targets(
        project_id: UUID,
        patient_id: UUID,
        run_id: UUID,
        authorization: str | None = Header(default=None),
    ):
        with session(authorization) as (c, i):
            return read_run_targets(c, i, project_id, patient_id, run_id)

    return router
