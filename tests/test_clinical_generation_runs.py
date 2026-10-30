"""Real private SQL/shared worker; generated values never correct source history."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_imaging_ingestion import http_session, imaging_db
from test_imaging_jobs import runtime
from test_scenario_geometry import queued
from test_simulation_runs import TEST
from test_source_registry import registry_db

from canceros.clinical_generation_runs import (
    ClinicalGenerationInput,
    materialize_clinical,
    read_clinical_batch,
)
from canceros.identity import Identity
from canceros.imaging_jobs import (
    ClinicalGenerationCommand,
    ImagingJobInput,
    dispatch_imaging,
    enqueue_imaging,
    process_imaging_one,
    read_imaging_job,
)
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.settings import Settings
from canceros.twin_states import create_branch, read_branch

__all__ = ["imaging_db", "registry_db", "runtime"]


def counts(c, p, u):
    return tuple(
        c.execute(
            text(f"SELECT count(*) FROM {table} WHERE project_id=:p AND patient_id=:u"),
            {"p": p, "u": u},
        ).scalar_one()
        for table in ("source.patient_revisions", "clinical.observations")
    )


def test_private_batch_idempotence_integrity_ownership_and_source_preservation(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    u = patient.patient_id
    branch, _, run = queued(imaging_db, mode="near_stable", deterioration="stable")
    value = ClinicalGenerationInput(run_id=run.id, expected_config_hash=run.config_hash)
    before = counts(c, p, u)
    report = materialize_clinical(c, i, p, u, value, storage, "clinical", TEST)
    assert report.batch.run_id == run.id and report.batch.branch_id == branch.id
    assert all(e.origin.value == "SYNTHETIC_GENERATED" for e in report.batch.events)
    assert report.publication == "draft" and report.scientific_review == "pending"
    assert report.batch.notes and all(
        "simulated" in note.text.lower() for note in report.batch.notes
    )
    assert any(e.modality == "symptom" for e in report.batch.events)
    assert materialize_clinical(c, i, p, u, value, storage, "clinical", TEST) == report
    assert materialize_clinical(c, i, p, u, value, storage, "clinical-retry", TEST) == report
    assert read_clinical_batch(c, i, p, u, report.id) == report
    assert counts(c, p, u) == before and read_branch(c, i, p, u, branch.id) == branch
    with pytest.raises(DBAPIError), c.begin_nested():
        c.execute(
            text("UPDATE imaging.generated_clinical_batches SET report='{}' WHERE id=:id"),
            {"id": report.id},
        )
    other_branch = create_branch(c, i, p, u, branch.input, storage, "another-branch")
    with pytest.raises(DBAPIError), c.begin_nested():
        c.execute(
            text(
                "INSERT INTO imaging.generated_clinical_batches SELECT :new_id,project_id,patient_id,:branch,run_id,actor_id,'wrong-branch',input_hash,report,report_hash FROM imaging.generated_clinical_batches WHERE id=:id"
            ),
            {"new_id": uuid4(), "branch": other_branch.id, "id": report.id},
        )
    for action in (
        lambda: read_clinical_batch(c, i, p, uuid4(), report.id),
        lambda: read_clinical_batch(c, Identity(i.user_id, {p: "viewer"}), p, u, report.id),
        lambda: materialize_clinical(
            c, i, p, u, value, storage, "production", Settings(mode="development", _env_file=None)
        ),
        lambda: materialize_clinical(
            c,
            i,
            p,
            u,
            value.model_copy(update={"expected_config_hash": "f" * 64}),
            storage,
            "bad-hash",
            TEST,
        ),
        lambda: materialize_clinical(
            c, i, p, u, value.model_copy(update={"run_id": uuid4()}), storage, "clinical", TEST
        ),
    ):
        with pytest.raises(HTTPException):
            action()
    withdraw_resource(c, i, p, u, run.id, WithdrawalInput(reason_code="scientific_review"))
    with pytest.raises(HTTPException):
        read_clinical_batch(c, i, p, u, report.id)
    with pytest.raises(HTTPException):
        materialize_clinical(c, i, p, u, value, storage, "clinical", TEST)


def test_shared_worker_and_authenticated_batch_http(runtime):
    data, queue, settings = runtime
    c, i, p, patient, _, storage, _ = data
    u = patient.patient_id
    _, _, run = queued(data)
    value = ImagingJobInput(
        expected_revision=run.input_revision,
        command=ClinicalGenerationCommand(
            operation="clinical_generation",
            input=ClinicalGenerationInput(run_id=run.id, expected_config_hash=run.config_hash),
        ),
    )
    before = counts(c, p, u)
    job = enqueue_imaging(c, i, p, u, value, "clinical-job", storage)
    c.commit()
    assert dispatch_imaging(c.engine, queue, p) == 1
    assert process_imaging_one(c.engine, queue, storage, settings) == job.id
    with c.engine.begin() as connection:
        completed = read_imaging_job(connection, i, p, u, job.id)
        assert completed.status == "succeeded" and completed.result_report_id
        report = read_clinical_batch(connection, i, p, u, completed.result_report_id)
        assert report.run_id == run.id and counts(connection, p, u) == before
    client, headers = http_session(data)
    path = f"/api/v1/projects/{p}/patients/{u}/generated-clinical-batches/{report.id}"
    with client:
        assert client.get(path).status_code == 401
        response = client.get(path, headers=headers)
        assert response.status_code == 200 and response.json()["run_id"] == str(run.id)
        assert client.get(path.replace(str(u), str(uuid4())), headers=headers).status_code == 404
