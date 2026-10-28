"""Private SQL/S3 and worker integration for isolated hypothetical geometry."""

from decimal import Decimal

import pytest
from fastapi import HTTPException
from test_imaging_ingestion import http_session, imaging_db
from test_imaging_jobs import runtime
from test_source_registry import registry_db
from test_twin_states import setup

from canceros.evaluation_splits import SplitInput, freeze_split, require_independent_test_resource
from canceros.imaging_jobs import (
    ImagingJobInput,
    SyntheticGeometryCommand,
    dispatch_imaging,
    enqueue_imaging,
    process_imaging_one,
    read_imaging_job,
)
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.settings import Settings
from canceros.synthetic_geometry import (
    FixtureRunInput,
    GeometryInput,
    TargetPoint,
    authorize_fixture_run,
    generate_geometry,
    read_generated_mesh,
    read_geometry_result,
)
from canceros.synthetic_shape import ShapeConfig
from canceros.twin_states import GeneratedGeometryMember, StateBuildInput, build_state, read_state

__all__ = ["imaging_db", "registry_db", "runtime"]


def frozen(data, config):
    c, i, p, patient, _, storage, _ = data
    branch, _, measures, _ = setup(data)
    value = FixtureRunInput(
        branch_id=branch.id,
        baseline_hash=branch.baseline_hash,
        targets=[
            TargetPoint(relative_day="10", target_mm3=measures[0].values.volume_mm3),
            TargetPoint(relative_day="20", target_mm3="0"),
            TargetPoint(relative_day="30", target_mm3="48"),
        ],
        shape_config=ShapeConfig(seed=42),
    )
    run = authorize_fixture_run(c, i, p, patient.patient_id, value, storage, "run", config)
    return branch, run, value, measures


def test_persisted_targets_zero_blocked_provenance_and_withdrawal(runtime):
    data, _, config = runtime
    c, i, p, patient, _, storage, _ = data
    u = patient.patient_id
    branch, run, value, measures = frozen(data, config)
    assert authorize_fixture_run(c, i, p, u, value, storage, "run", config) == run
    with pytest.raises(HTTPException) as denied:
        authorize_fixture_run(c, i, p, u, value, storage, "dev", Settings(mode="development"))
    assert denied.value.status_code == 409
    request = GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=0)
    result = generate_geometry(c, i, p, u, request, storage, "shape", config)
    assert result.status == "ready" and result.state_id
    assert generate_geometry(c, i, p, u, request, storage, "shape", config) == result
    assert Decimal(result.geometry.shape.realized_values.volume_mm3) == Decimal(
        measures[0].values.volume_mm3
    )
    assert result.geometry.origin == "SYNTHETIC_GENERATED"
    assert not result.geometry.actual_followup_imaging_acquired
    mesh = read_generated_mesh(c, i, p, u, result.id, storage)
    assert mesh.origin == "SYNTHETIC_GENERATED" and mesh.display_label == "Simulated"
    state = read_state(c, i, p, u, result.state_id)
    assert state.publication is None and state.review is None
    assert state.snapshot.generated_geometry_members[0].geometry == result.geometry
    manifest = freeze_split(
        c,
        i,
        p,
        SplitInput.model_validate({"seed": 42, "assignments": [{"patient_id": u, "role": "test"}]}),
    )
    for resource_id in (
        result.id,
        result.geometry.id,
        result.geometry.mesh_artifact_id,
        result.state_id,
    ):
        with pytest.raises(HTTPException):
            require_independent_test_resource(c, i, p, u, manifest.id, resource_id)
    with pytest.raises(HTTPException):
        build_state(
            c,
            i,
            p,
            u,
            StateBuildInput(
                context="OBSERVED",
                target_revision=run.input_revision,
                association_head=run.association_head,
                branch_id=branch.id,
                time=result.geometry.time,
                generated_geometry_members=[
                    GeneratedGeometryMember(geometry_id=result.geometry.id)
                ],
            ),
            storage,
            "observed-denied",
        )
    zero = generate_geometry(
        c, i, p, u, request.model_copy(update={"target_index": 1}), storage, "zero", config
    )
    assert zero.status == "zero" and zero.state_id and zero.geometry.mesh_artifact_id is None
    assert zero.geometry.shape.realized_values.availability == "configured_simulated_absent"
    with pytest.raises(HTTPException):
        read_generated_mesh(c, i, p, u, zero.id, storage)
    blocked = generate_geometry(
        c, i, p, u, request.model_copy(update={"target_index": 2}), storage, "clipped", config
    )
    assert blocked.status == "blocked" and blocked.state_id is None
    with pytest.raises(HTTPException):
        generate_geometry(
            c, i, p, u, request.model_copy(update={"target_index": 1}), storage, "shape", config
        )
    withdraw_resource(
        c,
        i,
        p,
        u,
        result.id,
        WithdrawalInput(reason_code="scientific_review"),
    )
    assert read_geometry_result(c, i, p, u, result.id) == result
    with pytest.raises(HTTPException):
        read_generated_mesh(c, i, p, u, result.id, storage)


def test_shared_worker_and_authenticated_mesh_http(runtime):
    data, queue, config = runtime
    c, i, p, patient, _, storage, _ = data
    u = patient.patient_id
    branch, run, _, _ = frozen(data, config)
    command = GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=0)
    job = enqueue_imaging(
        c,
        i,
        p,
        u,
        ImagingJobInput(
            expected_revision=run.input_revision,
            command=SyntheticGeometryCommand(operation="synthetic_geometry", input=command),
        ),
        "geometry-worker",
        storage,
    )
    c.commit()
    assert dispatch_imaging(c.engine, queue, p) == 1
    assert process_imaging_one(c.engine, queue, storage, config) == job.id
    with c.engine.begin() as connection:
        completed = read_imaging_job(connection, i, p, u, job.id)
        assert completed.status == "succeeded" and completed.result_report_id
        result = read_geometry_result(connection, i, p, u, completed.result_report_id)
        assert result.state_id
    client, headers = http_session(data)
    path = f"/api/v1/projects/{p}/patients/{u}/synthetic-geometry-results/{result.id}"
    with client:
        assert client.get(path).status_code == 401
        assert client.get(path, headers=headers).json()["publication"] == "draft"
        assert client.get(path + "/mesh", headers=headers).json()["display_label"] == "Simulated"
