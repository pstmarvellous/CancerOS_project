"""Real SQL/private S3/Redis reconstruction, distinct objects and private HTTP output."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_imaging_ingestion import http_session, imaging_db
from test_imaging_jobs import runtime
from test_measurement_runs import measurement_sources
from test_source_registry import registry_db

from canceros.identity import Identity
from canceros.imaging_jobs import (
    ImagingJobInput,
    MeshCommand,
    dispatch_imaging,
    enqueue_imaging,
    process_imaging_one,
    read_imaging_job,
)
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.measurement_runs import create_measurement, read_measurement
from canceros.mesh_runs import MeshInput, create_mesh, load_mesh, read_mesh

__all__ = ["imaging_db", "registry_db", "runtime"]


def test_mesh_private_idempotent_objects_http_ownership_and_withdrawal(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    measurement = create_measurement(
        c, i, p, patient.patient_id, measurement_sources(imaging_db), storage, "mesh-source"
    )
    value = MeshInput(measurement_id=measurement.id)
    report = create_mesh(c, i, p, patient.patient_id, value, storage, "mesh-once")
    assert create_mesh(c, i, p, patient.patient_id, value, storage, "mesh-once") == report
    assert read_measurement(c, i, p, patient.patient_id, measurement.id) == measurement
    _, asset = load_mesh(c, i, p, patient.patient_id, report.id, storage)
    assert len(asset.objects) == 2 and {o.label for o in asset.objects} == {1, 2}
    assert all(o.surface.unit == "mm" for o in asset.objects)
    assert report.triangle_count == 16 and report.vertex_count == 12
    with pytest.raises(HTTPException):
        read_mesh(c, i, p, uuid4(), report.id)
    with pytest.raises(HTTPException):
        read_mesh(c, Identity(i.user_id, {p: "viewer"}), p, patient.patient_id, report.id)
    with pytest.raises(HTTPException):
        read_mesh(c, i, uuid4(), patient.patient_id, report.id)
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/mesh-runs/{report.id}"
    with client:
        assert client.get(path, headers=headers).status_code == 200
        response = client.get(path + "/asset", headers=headers)
        assert response.status_code == 200 and "no-store" in response.headers["Cache-Control"]
        assert response.json()["anatomical_review"] == "not_established"
        assert client.get(path + "/asset").status_code == 401
    withdraw_resource(
        c,
        i,
        p,
        patient.patient_id,
        measurement.selections[0].qc_report_id,
        WithdrawalInput(reason_code="scientific_review"),
    )
    with pytest.raises(HTTPException):
        load_mesh(c, i, p, patient.patient_id, report.id, storage)
    assert read_mesh(c, i, p, patient.patient_id, report.id) == report


def test_shared_worker_mesh_operation_and_replay(runtime):
    data, queue, settings = runtime
    c, i, p, patient, _, storage, _ = data
    measurement = create_measurement(
        c, i, p, patient.patient_id, measurement_sources(data), storage, "job-mesh-source"
    )
    request = ImagingJobInput(
        expected_revision=1,
        command=MeshCommand(operation="mesh", input=MeshInput(measurement_id=measurement.id)),
    )
    job = enqueue_imaging(c, i, p, patient.patient_id, request, "mesh-worker-once", storage)
    c.commit()
    assert dispatch_imaging(c.engine, queue, p) == 1
    assert process_imaging_one(c.engine, queue, storage, settings) == job.id
    with c.engine.begin() as connection:
        result = read_imaging_job(connection, i, p, patient.patient_id, job.id)
        assert result.status == "succeeded" and result.result_report_id
        assert (
            enqueue_imaging(
                connection, i, p, patient.patient_id, request, "mesh-worker-once", storage
            ).id
            == job.id
        )
        report, asset = load_mesh(
            connection, i, p, patient.patient_id, result.result_report_id, storage
        )
        assert len(asset.objects) == 2 and report.status == "generated_pending_mesh_qc"
