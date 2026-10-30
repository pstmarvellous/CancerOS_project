"""Actual fixed-grid quantization cannot be passed off as realized SC-01 reduction."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_imaging_ingestion import http_session, imaging_db
from test_imaging_jobs import runtime
from test_simulation_runs import TEST, inputs, request
from test_source_registry import registry_db

from canceros.imaging_jobs import (
    ImagingJobInput,
    SyntheticGeometryCommand,
    dispatch_imaging,
    enqueue_imaging,
    process_imaging_one,
    read_imaging_job,
)
from canceros.scenario_families import SC01_VERSION
from canceros.scenario_geometry import GeometryValidationInput, validate_run_geometry
from canceros.simulation_contracts import SimulationConfig
from canceros.simulation_runs import SaveConfigInput, queue_run, read_run_targets, save_config
from canceros.synthetic_geometry import GeometryInput, generate_geometry, read_geometry_result
from canceros.twin_states import (
    PublishInput,
    ReviewInput,
    publish_state,
    read_branch,
    read_state,
    review_state,
)

__all__ = ["imaging_db", "registry_db", "runtime"]


def queued(
    data, mode=None, zero=False, growth=False, geometry=True, regrowth=False, deterioration=None
):
    c, i, p, patient, _, storage, _ = data
    branch, config, _ = inputs(data)
    raw = config.model_dump(mode="json")
    raw["scenario"] = {"family": "SC-01", "definition_version": SC01_VERSION}
    if growth:
        raw["scenario"] = {"family": "SC-03", "definition_version": "sc03-explicit/1"}
        raw["clinical_profile"]["configuration"] = "stable"
    if regrowth:
        raw["scenario"] = {"family": "SC-04", "definition_version": "sc04-explicit/1"}
        raw["sc04_parameters"] = {"change_point_day": "20", "nadir_mm3": "16"}
    if mode:
        raw["scenario"] = {"family": "SC-02", "definition_version": "sc02-explicit/1"}
        raw["sc02_parameters"] = (
            {
                "mode": mode,
                "max_absolute_change_mm3": "24" if zero else "0",
                "max_relative_change": "1" if zero else "0",
            }
            if mode == "near_stable"
            else {"mode": mode, "min_relative_decline": "0.1", "max_relative_decline": "0.2"}
        )
    raw["geometry_policy"] = "isotropic-fixed-grid/1" if geometry else "none"
    for point, volume in zip(
        raw["tumor_profile"]["points"],
        ("20", "16", "20")
        if regrowth
        else ("25", "26", "27")
        if growth
        else ("0", "0", "0")
        if zero
        else ("24", "24", "24")
        if mode == "near_stable"
        else ("23", "22", "21"),
        strict=True,
    ):
        point["target_mm3"] = volume
    if deterioration:
        raw["scenario"] = {"family": "SC-05", "definition_version": "sc05-explicit/1"}
        tumor_family = {"stable": "SC-02", "shrink": "SC-01", "growth": "SC-03"}[deterioration]
        raw["sc05_parameters"] = {
            "profile_version": "clinical-condition/1",
            "tumor_family": tumor_family,
            "affected_concepts": [{"concept": "fatigue", "numeric_direction": None}],
            "onset_day": "0",
            "recovery_day": None,
            "internal_severity": "moderate",
            "symptom_course": [
                {
                    "slot_id": f"symptom-{n}",
                    "concept": "fatigue",
                    "rating": rating,
                    "presence": "present",
                }
                for n, rating in enumerate((1, 3, 6), start=1)
            ],
        }
        raw["schedule"]["slots"].extend(
            [
                {"slot_id": f"symptom-{n}", "modality": "symptom", "relative_day": str(n * 10)}
                for n in range(1, 4)
            ]
        )
        raw["clinical_profile"]["configuration"] = "moderate_deterioration"
    draft = save_config(
        c,
        i,
        p,
        patient.patient_id,
        branch.id,
        SaveConfigInput(expected_draft_revision=0, config=SimulationConfig.model_validate(raw)),
        storage,
        "sc01-config",
        TEST,
    )
    run = queue_run(
        c, i, p, patient.patient_id, branch.id, request(draft), storage, "sc01-run", TEST
    )
    return branch, draft, run


def test_common_run_realized_plateau_blocks_ordering_and_never_publishes(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, draft, run = queued(imaging_db)
    assert run.id != branch.input.run_id and run.association_head is not None
    results = [
        generate_geometry(
            c,
            i,
            p,
            u,
            GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=n),
            storage,
            f"common-shape-{n}",
            TEST,
        )
        for n in range(3)
    ]
    assert all(result.status == "ready" and result.state_id for result in results)
    value = GeometryValidationInput(result_ids=[result.id for result in results])
    validated = validate_run_geometry(c, i, p, u, run.id, value)
    assert validated.target_mm3 == ["23", "22", "21"]
    assert validated.realized_mm3 == ["24", "24", "24"]
    assert validated.ordering.status == "blocked" and not validated.ordering.ordering_valid
    assert any("plateau" in reason for reason in validated.ordering.reasons)
    assert read_branch(c, i, p, u, branch.id) == branch
    with pytest.raises(DBAPIError), c.begin_nested():
        c.execute(
            text(
                "INSERT INTO imaging.synthetic_geometries(id,project_id,patient_id,actor_id,command_key,input_hash,report,report_hash,run_id,branch_id) SELECT :new_id,project_id,patient_id,actor_id,'invalid-run-kind',input_hash,report,report_hash,:not_run,branch_id FROM imaging.synthetic_geometries WHERE id=:id"
            ),
            {
                "new_id": uuid4(),
                "not_run": branch.input.baseline_measurement_id,
                "id": results[0].geometry.id,
            },
        )
    for result in results:
        state = read_state(c, i, p, u, result.state_id)
        assert (
            state.publication is None
            and state.snapshot.generated_geometry_members[0].geometry.run_id == run.id
        )
    first_state = read_state(c, i, p, u, results[0].state_id)
    review = review_state(
        c,
        i,
        p,
        u,
        first_state.snapshot.id,
        ReviewInput(
            snapshot_hash=first_state.snapshot_hash,
            decision="accepted_engineering",
            evidence_sha256="a" * 64,
        ),
        "attempt-individual-review",
    )
    assert (
        "publish_private_fixture"
        not in read_state(c, i, p, u, first_state.snapshot.id).available_actions
    )
    with pytest.raises(HTTPException) as publication:
        publish_state(
            c,
            i,
            p,
            u,
            first_state.snapshot.id,
            PublishInput(
                snapshot_hash=first_state.snapshot_hash,
                expected_patient_revision=run.input_revision,
                expected_association_head=run.association_head,
                expected_review_id=review.id,
            ),
            "attempt-individual-publication",
        )
    assert (
        publication.value.detail
        == "common_run_requires_complete_validation_and_separate_publication"
    )
    other_run = queue_run(c, i, p, u, branch.id, request(draft), storage, "other-run", TEST)
    with pytest.raises(HTTPException):
        validate_run_geometry(c, i, p, u, other_run.id, value)
    with pytest.raises(HTTPException):
        validate_run_geometry(
            c, i, p, u, run.id, GeometryValidationInput(result_ids=[results[0].id] * 3)
        )
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{u}/simulation-runs/{run.id}/geometry-validation"
    with client:
        assert client.post(path, json=value.model_dump(mode="json")).status_code == 401
        response = client.post(path, json=value.model_dump(mode="json"), headers=headers)
        assert response.status_code == 200 and response.json()["ordering"]["status"] == "blocked"
        assert response.json()["publication"] == "draft"


def test_common_run_uses_existing_shared_worker_and_frozen_state_membership(runtime):
    data, queue, config = runtime
    c, i, p, patient, _, storage, _ = data
    u = patient.patient_id
    branch, _, run = queued(data)
    job = enqueue_imaging(
        c,
        i,
        p,
        u,
        ImagingJobInput(
            expected_revision=run.input_revision,
            command=SyntheticGeometryCommand(
                operation="synthetic_geometry",
                input=GeometryInput(
                    run_id=run.id, baseline_hash=branch.baseline_hash, target_index=0
                ),
            ),
        ),
        "common-geometry-job",
        storage,
    )
    c.commit()
    assert dispatch_imaging(c.engine, queue, p) == 1
    assert process_imaging_one(c.engine, queue, storage, config) == job.id
    with c.engine.begin() as connection:
        complete = read_imaging_job(connection, i, p, u, job.id)
        assert complete.status == "succeeded" and complete.result_report_id
        result = read_geometry_result(connection, i, p, u, complete.result_report_id)
        assert result.geometry.run_id == run.id and result.state_id
        state = read_state(connection, i, p, u, result.state_id)
        assert state.snapshot.baseline_hash == branch.baseline_hash and state.publication is None


@pytest.mark.parametrize(
    "mode,expected", [("near_stable", "ready"), ("modest_reduction", "blocked")]
)
def test_sc02_modes_use_actual_geometry_and_preserve_requested_mode(imaging_db, mode, expected):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, _, run = queued(imaging_db, mode)
    results = [
        generate_geometry(
            c,
            i,
            p,
            u,
            GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=n),
            storage,
            f"sc02-{n}",
            TEST,
        )
        for n in range(3)
    ]
    report = validate_run_geometry(
        c, i, p, u, run.id, GeometryValidationInput(result_ids=[r.id for r in results])
    )
    assert report.family == "SC-02" and report.mode == mode
    assert report.ordering.status == expected and report.publication == "draft"
    assert report.realized_mm3 == ["24", "24", "24"]
    assert run.config.clinical_profile.configuration == "moderate_deterioration"


def test_sc02_explicit_zero_band_preserves_simulated_absence_semantics(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, _, run = queued(imaging_db, "near_stable", zero=True)
    results = [
        generate_geometry(
            c,
            i,
            p,
            u,
            GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=n),
            storage,
            f"zero-sc02-{n}",
            TEST,
        )
        for n in range(3)
    ]
    assert all(r.status == "zero" and r.geometry.mesh_artifact_id is None for r in results)
    assert all(
        r.geometry.shape.realized_values.availability == "configured_simulated_absent"
        for r in results
    )
    report = validate_run_geometry(
        c, i, p, u, run.id, GeometryValidationInput(result_ids=[r.id for r in results])
    )
    assert report.realized_mm3 == ["0", "0", "0"] and report.ordering.ordering_valid
    assert report.publication == "draft" and report.measurement_uncertainty == "not_established"


def test_sc04_configured_and_realized_minima_are_distinct_when_quantization_erases_turn(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, _, run = queued(imaging_db, regrowth=True)
    latent = read_run_targets(c, i, p, u, run.id).output
    assert latent.turning_point.configured_day == "20"
    assert latent.turning_point.configured_nadir_mm3 == "16"
    assert latent.turning_point.latent_sampled_minimum_slot_id == "scan-2"
    results = [
        generate_geometry(
            c,
            i,
            p,
            u,
            GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=n),
            storage,
            f"regrowth-{n}",
            TEST,
        )
        for n in range(3)
    ]
    report = validate_run_geometry(
        c, i, p, u, run.id, GeometryValidationInput(result_ids=[r.id for r in results])
    )
    assert report.family == "SC-04" and report.ordering.status == "blocked"
    assert report.configured_turning_point == latent.turning_point
    assert report.realized_mm3 == ["24", "24", "24"]
    assert report.realized_minimum_mm3 == "24" and report.realized_minimum_slot_ids == [
        "scan-1",
        "scan-2",
        "scan-3",
    ]
    assert report.publication == "draft" and read_branch(c, i, p, u, branch.id) == branch


def test_sc03_measurement_only_targets_are_available_without_geometry_jobs(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, _, run = queued(imaging_db, growth=True, geometry=False)
    summary = read_run_targets(c, i, p, u, run.id)
    assert [point.target_mm3 for point in summary.output.tumor_targets] == ["25", "26", "27"]
    assert summary.geometry_policy == "none" and summary.publication == "draft"
    with pytest.raises(HTTPException) as disabled:
        generate_geometry(
            c,
            i,
            p,
            u,
            GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=0),
            storage,
            "disabled-geometry",
            TEST,
        )
    assert disabled.value.detail == "frozen_geometry_policy_and_association_head_required"
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{u}/simulation-runs/{run.id}/targets"
    with client:
        assert client.get(path).status_code == 401
        response = client.get(path, headers=headers)
        assert response.status_code == 200 and response.json()["output"]["family"] == "SC-03"


@pytest.mark.parametrize("course", ["stable", "shrink"])
def test_sc05_condition_is_independent_and_never_fills_baseline_clinical_missingness(
    imaging_db, course
):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, _, run = queued(
        imaging_db, mode="near_stable" if course == "stable" else None, deterioration=course
    )
    latent = read_run_targets(c, i, p, u, run.id).output
    assert (
        latent.family == "SC-05"
        and latent.clinical_condition.severity_meaning == "internal_simulation_setting_not_ctcae"
    )
    assert all(
        event.grading == "ungraded" and event.attribution == "hypothetical_association_not_causal"
        for event in latent.clinical_condition.events
    )
    assert [point.rating for point in latent.clinical_condition.parameters.symptom_course] == [
        1,
        3,
        6,
    ]
    results = [
        generate_geometry(
            c,
            i,
            p,
            u,
            GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=n),
            storage,
            f"condition-{n}",
            TEST,
        )
        for n in range(3)
    ]
    report = validate_run_geometry(
        c, i, p, u, run.id, GeometryValidationInput(result_ids=[r.id for r in results])
    )
    assert report.family == "SC-05" and report.clinical_condition == latent.clinical_condition
    assert report.ordering.status == ("ready" if course == "stable" else "blocked")
    assert all(
        not read_state(c, i, p, u, result.state_id).snapshot.clinical_members for result in results
    )
    assert report.publication == "draft" and not run.baseline_observed_verified


def test_sc03_field_of_view_failure_is_explicit_and_creates_no_fake_followup(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, _, run = queued(imaging_db, growth=True)
    before = c.execute(
        text("SELECT count(*) FROM imaging.imports WHERE project_id=:p AND patient_id=:u"),
        {"p": p, "u": u},
    ).scalar_one()
    results = [
        generate_geometry(
            c,
            i,
            p,
            u,
            GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=n),
            storage,
            f"growth-{n}",
            TEST,
        )
        for n in range(3)
    ]
    assert all(result.status == "blocked" and result.state_id is None for result in results)
    assert all(
        result.geometry.mask_artifact_id is None and result.geometry.shape.realized_values is None
        for result in results
    )
    assert all(result.geometry.anatomical_containment == "not_established" for result in results)
    assert all("outside_fixed_grid" in result.geometry.next_action for result in results)
    report = validate_run_geometry(
        c, i, p, u, run.id, GeometryValidationInput(result_ids=[r.id for r in results])
    )
    assert report.family == "SC-03" and report.ordering.status == "blocked"
    assert report.target_mm3 == ["25", "26", "27"] and report.realized_mm3 == [None, None, None]
    assert read_branch(c, i, p, u, branch.id) == branch
    assert run.config.clinical_profile.configuration == "stable"
    assert (
        c.execute(
            text("SELECT count(*) FROM imaging.imports WHERE project_id=:p AND patient_id=:u"),
            {"p": p, "u": u},
        ).scalar_one()
        == before
    )
