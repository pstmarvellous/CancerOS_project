"""Actual five-family masks/meshes, shared worker and atomic private publication."""

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi import HTTPException
from simulation_fixtures import setup_simulation_baseline
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_imaging_ingestion import http_session, imaging_db
from test_imaging_jobs import runtime
from test_simulation_regression import regression_config
from test_simulation_runs import TEST, request
from test_source_registry import registry_db

from canceros import simulation_execution as execution
from canceros.identity import Identity
from canceros.imaging_jobs import (
    ImagingJobInput,
    SimulationCompleteCommand,
    dispatch_imaging,
    enqueue_imaging,
    process_imaging_one,
    read_imaging_job,
)
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.measurement_runs import read_measurement
from canceros.persistence import capture_revision
from canceros.simulation_contracts import SimulationConfig
from canceros.simulation_execution import (
    CompleteRunInput,
    PublishRunInput,
    complete_run,
    publish_completion,
    read_completion,
    read_current_run,
)
from canceros.simulation_runs import SaveConfigInput, queue_run, save_config
from canceros.synthetic_geometry import GeometryInput, generate_geometry, read_geometry_result
from canceros.twin_states import BranchInput, create_branch, read_state

__all__ = ["registry_db", "imaging_db", "runtime"]


def freeze(data, measurement, origin, family, *, geometry=True, seed=7, branch=None, key=None):
    c, i, p, patient, _, storage, _ = data
    key = key or family
    branch = branch or create_branch(
        c,
        i,
        p,
        patient.patient_id,
        BranchInput(
            baseline_measurement_id=measurement.id, timeline_origin_id=origin, run_id=uuid4()
        ),
        storage,
        "branch-" + key,
    )
    raw = regression_config(family, seed).model_dump(mode="json")
    # Curated actual geometry stays inside the existing 500k exact-support budget.
    targets = {
        "SC-01": ("64", "8", "1"),
        "SC-02": ("216",) * 3,
        "SC-03": ("343", "512", "729"),
        "SC-04": ("64", "8", "64"),
        "SC-05": ("216",) * 3,
    }[family]
    for point, target in zip(raw["tumor_profile"]["points"], targets, strict=True):
        point["target_mm3"] = target
    if family == "SC-04":
        raw["sc04_parameters"] = {"change_point_day": "26", "nadir_mm3": "8"}
        for slot, day in zip(
            [s for s in raw["schedule"]["slots"] if s["modality"] == "imaging"],
            ("19", "26", "52"),
            strict=True,
        ):
            slot["relative_day"] = day
    raw.update(
        branch_id=str(branch.id),
        baseline_hash=branch.baseline_hash,
        input_revision=1,
        geometry_policy="isotropic-fixed-grid/1" if geometry else "none",
    )
    draft = save_config(
        c,
        i,
        p,
        patient.patient_id,
        branch.id,
        SaveConfigInput(expected_draft_revision=0, config=SimulationConfig.model_validate(raw)),
        storage,
        "config-" + key,
        TEST,
    )
    run = queue_run(
        c, i, p, patient.patient_id, branch.id, request(draft), storage, "run-" + key, TEST
    )
    return branch, draft, run


def command(run):
    return CompleteRunInput(run_id=run.id, expected_config_hash=run.config_hash)


def test_large_grid_growth_realization_diagnostics(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    measurement, origin, _ = setup_simulation_baseline(imaging_db)
    branch, _, run = freeze(imaging_db, measurement, origin, "SC-03")
    for index in range(3):
        result = generate_geometry(
            c,
            i,
            p,
            patient.patient_id,
            GeometryInput(run_id=run.id, baseline_hash=branch.baseline_hash, target_index=index),
            storage,
            "growth-diagnostic-" + str(index),
            TEST,
        )
        assert result.status == "ready", (
            index,
            result.geometry.shape.reasons,
            result.geometry.shape.realized_values.exact_volume_mm3
            if result.geometry.shape.realized_values
            else None,
            result.geometry.mesh_qc.failures if result.geometry.mesh_qc else None,
        )


def publication_value(run, current=None):
    return PublishRunInput(
        expected_config_hash=run.config_hash,
        expected_patient_revision=run.input_revision,
        expected_association_head=run.association_head,
        expected_current_run_id=current,
        engineering_attestation_sha256="e" * 64,
    )


def test_all_five_families_have_actual_complete_geometry_and_atomic_publication(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    measurement, origin, _ = setup_simulation_baseline(imaging_db)
    before = read_measurement(c, i, p, u, measurement.id)
    attempted = []
    prior_publication = None
    for family in ("SC-01", "SC-02", "SC-03", "SC-04", "SC-05"):
        branch, _, run = freeze(imaging_db, measurement, origin, family)
        report = complete_run(c, i, p, u, command(run), storage, "complete-" + family, TEST)
        attempted.append(report.status)
        assert report.status == "ready", (
            family,
            report.stage,
            report.failure_reason,
            report.validation,
        )
        assert report.validation.scope == "anatomical_engineering"
        assert len(report.geometry_result_ids) == 3 and len(report.state_ids) >= 4
        assert read_current_run(c, i, p, u, branch.id).publication is None
        for identifier in report.geometry_result_ids:
            geometry = read_geometry_result(c, i, p, u, identifier)
            assert (
                geometry.status == "ready"
                and geometry.geometry.mask_artifact_id
                and geometry.geometry.mesh_artifact_id
            )
            assert geometry.geometry.mesh_qc.display_allowed
            assert (
                geometry.geometry.shape.realized_values.exact_volume_mm3
                == geometry.geometry.shape.target_mm3
            )
        states = [read_state(c, i, p, u, s) for s in report.state_ids]
        assert states[0].snapshot.time.value == "0" and all(s.publication is None for s in states)
        assert any(s.snapshot.generated_clinical_members for s in states)
        published = publish_completion(
            c, i, p, u, report.id, publication_value(run), storage, "publish-" + family, TEST
        )
        assert (
            publish_completion(
                c, i, p, u, report.id, publication_value(run), storage, "publish-" + family, TEST
            )
            == published
        )
        assert len(published.state_publication_ids) == len(states)
        current = read_current_run(c, i, p, u, branch.id)
        assert current.publication == published and current.current_use_allowed
        assert all(read_state(c, i, p, u, s).publication for s in report.state_ids)
        assert read_measurement(c, i, p, u, measurement.id) == before
        if prior_publication:
            with pytest.raises(DBAPIError), c.begin_nested():
                c.execute(
                    text(
                        "UPDATE imaging.simulation_current_runs SET publication_id=:wrong WHERE project_id=:p AND patient_id=:u AND branch_id=:b"
                    ),
                    {"wrong": prior_publication.id, "p": p, "u": u, "b": branch.id},
                )
            with pytest.raises(DBAPIError), c.begin_nested():
                c.execute(
                    text(
                        "INSERT INTO imaging.simulation_publications SELECT :new_id,project_id,patient_id,branch_id,run_id,actor_id,'wrong-completion-scope',input_hash,report,report_hash,:wrong FROM imaging.simulation_publications WHERE id=:id"
                    ),
                    {
                        "new_id": uuid4(),
                        "wrong": prior_publication.completion_id,
                        "id": published.id,
                    },
                )
        prior_publication = published
    assert attempted == ["ready"] * 5


def test_measurement_only_worker_http_and_ownership(runtime):
    data, queue, settings = runtime
    c, i, p, patient, _, storage, _ = data
    u = patient.patient_id
    measurement, origin, _ = setup_simulation_baseline(data)
    branch, _, run = freeze(data, measurement, origin, "SC-01", geometry=False)
    job = enqueue_imaging(
        c,
        i,
        p,
        u,
        ImagingJobInput(
            expected_revision=1,
            command=SimulationCompleteCommand(operation="simulation_complete", input=command(run)),
        ),
        "complete-worker",
        storage,
    )
    c.commit()
    assert dispatch_imaging(c.engine, queue, p) == 1
    assert process_imaging_one(c.engine, queue, storage, settings) == job.id
    with c.engine.begin() as connection:
        result = read_imaging_job(connection, i, p, u, job.id)
        assert result.status == "succeeded", result
        report = read_completion(connection, i, p, u, result.result_report_id)
        assert report.status == "ready" and report.validation.scope == "measurement_only"
        assert not report.geometry_result_ids and len(report.state_ids) >= 4
        assert read_current_run(connection, i, p, u, branch.id).publication is None
        for actor, project, person in [
            (i, p, uuid4()),
            (i, uuid4(), u),
            (Identity(i.user_id, {p: "viewer"}), p, u),
        ]:
            with pytest.raises(HTTPException):
                read_completion(connection, actor, project, person, report.id)
    client, headers = http_session(data)
    path = f"/api/v1/projects/{p}/patients/{u}/simulation-completions/{report.id}"
    with client:
        assert client.get(path).status_code == 401
        assert client.get(path, headers=headers).status_code == 200
        response = client.post(
            path + "/publications",
            json=publication_value(run).model_dump(mode="json"),
            headers={**headers, "Idempotency-Key": "http-complete-publish"},
        )
        assert response.status_code == 201, response.text
        assert client.get(response.headers["Location"], headers=headers).json()[
            "current_use_allowed"
        ]


@pytest.mark.parametrize(
    "stage,function",
    [
        ("eligibility", "evaluate_config"),
        ("sampling", "read_run_sampling"),
        ("clinical", "materialize_clinical"),
        ("geometry", "generate_geometry"),
        ("states", "build_state"),
        ("validation", "validate_complete_run"),
    ],
)
def test_failure_at_each_stage_retains_previous_complete_publication(
    imaging_db, monkeypatch, stage, function
):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    measurement, origin, _ = setup_simulation_baseline(imaging_db)
    branch, draft, run = freeze(imaging_db, measurement, origin, "SC-02", geometry=False)
    previous = complete_run(c, i, p, u, command(run), storage, "previous", TEST)
    assert previous.status == "ready", previous
    published = publish_completion(
        c, i, p, u, previous.id, publication_value(run), storage, "previous-publish", TEST
    )
    newer = queue_run(c, i, p, u, branch.id, request(draft), storage, "newer-run", TEST)
    # A geometry attempt is required for the injected geometry-stage failure.
    if stage == "geometry":
        raw = draft.config.model_dump(mode="json")
        raw["geometry_policy"] = "isotropic-fixed-grid/1"
        updated = save_config(
            c,
            i,
            p,
            u,
            branch.id,
            SaveConfigInput(expected_draft_revision=1, config=SimulationConfig.model_validate(raw)),
            storage,
            "geometry-draft",
            TEST,
        )
        newer = queue_run(
            c, i, p, u, branch.id, request(updated), storage, "newer-geometry-run", TEST
        )

    def rejected(*args, **kwargs):
        raise HTTPException(409, detail="injected_engineering_failure")

    monkeypatch.setattr(execution, function, rejected)
    failed = complete_run(c, i, p, u, command(newer), storage, "injected-" + stage, TEST)
    assert failed.status == "blocked" and failed.stage == stage
    assert (
        not failed.state_ids and not failed.geometry_result_ids and failed.clinical_batch_id is None
    )
    assert read_completion(c, i, p, u, failed.id) == failed
    assert read_current_run(c, i, p, u, branch.id).publication == published
    with pytest.raises(HTTPException):
        publish_completion(
            c, i, p, u, failed.id, publication_value(newer, run.id), storage, "no-partial", TEST
        )


def test_concurrent_publication_cas_and_withdrawal(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    measurement, origin, _ = setup_simulation_baseline(imaging_db)
    branch, draft, first = freeze(imaging_db, measurement, origin, "SC-02", geometry=False)
    second = queue_run(c, i, p, u, branch.id, request(draft), storage, "second-run", TEST)
    reports = [
        complete_run(c, i, p, u, command(run), storage, "completion-" + str(n), TEST)
        for n, run in enumerate((first, second))
    ]
    assert all(r.status == "ready" for r in reports), reports
    c.commit()

    def publish(pair):
        n, run, report = pair
        try:
            with c.engine.begin() as connection:
                return publish_completion(
                    connection,
                    i,
                    p,
                    u,
                    report.id,
                    publication_value(run),
                    storage,
                    "race-" + str(n),
                    TEST,
                ).run_id
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(publish, [(0, first, reports[0]), (1, second, reports[1])]))
    assert sum(result == 409 for result in results) == 1
    winner = read_current_run(c, i, p, u, branch.id)
    assert winner.publication.run_id in (first.id, second.id)
    assert sum(
        bool(read_state(c, i, p, u, s).publication) for r in reports for s in r.state_ids
    ) == len(reports[0].state_ids)
    withdraw_resource(c, i, p, u, measurement.id, WithdrawalInput(reason_code="rights_withdrawn"))
    with pytest.raises(HTTPException):
        read_completion(c, i, p, u, reports[0].id)
    count = c.execute(
        text(
            "SELECT count(*) FROM imaging.simulation_publications WHERE project_id=:p AND patient_id=:u"
        ),
        {"p": p, "u": u},
    ).scalar_one()
    assert count == 1


def test_publication_transaction_rollback_and_stale_revision_preserve_history(
    imaging_db, monkeypatch
):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    measurement, origin, _ = setup_simulation_baseline(imaging_db)
    branch, _, run = freeze(imaging_db, measurement, origin, "SC-02", geometry=False)
    report = complete_run(c, i, p, u, command(run), storage, "atomic-completion", TEST)
    assert report.status == "ready", report
    original = execution.publish_complete_run_states

    def fail_after_states(*args, **kwargs):
        original(*args, **kwargs)
        raise HTTPException(409, detail="injected_publication_transaction_failure")

    monkeypatch.setattr(execution, "publish_complete_run_states", fail_after_states)
    with pytest.raises(HTTPException), c.begin_nested():
        publish_completion(
            c, i, p, u, report.id, publication_value(run), storage, "atomic-publish", TEST
        )
    assert read_current_run(c, i, p, u, branch.id).publication is None
    assert not any(read_state(c, i, p, u, s).publication for s in report.state_ids)
    monkeypatch.setattr(execution, "publish_complete_run_states", original)
    published = publish_completion(
        c, i, p, u, report.id, publication_value(run), storage, "atomic-publish", TEST
    )
    capture_revision(c, p, u, 2, {"members": [], "fixture_source_correction": True})
    c.execute(
        text("UPDATE source.research_patients SET data_revision=2 WHERE project_id=:p AND id=:u"),
        {"p": p, "u": u},
    )
    current = read_current_run(c, i, p, u, branch.id)
    assert current.publication == published and not current.current_use_allowed
    assert read_completion(c, i, p, u, report.id) == report
    with pytest.raises(HTTPException):
        publish_completion(
            c, i, p, u, report.id, publication_value(run, run.id), storage, "stale-publish", TEST
        )
