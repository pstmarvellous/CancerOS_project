"""Actual private fixtures: immutable selection, limits, HTTP and withdrawal."""

import pytest
from fastapi import HTTPException
from test_imaging_ingestion import http_session, imaging_db
from test_imaging_jobs import runtime
from test_measurement_runs import measurement_sources
from test_source_registry import registry_db

from canceros.imaging_jobs import (
    ImagingJobInput,
    MeshQCCommand,
    dispatch_imaging,
    enqueue_imaging,
    process_imaging_one,
    read_imaging_job,
)
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.measurement_runs import create_measurement, read_measurement
from canceros.mesh_quality_runs import MeshQCInput, create_mesh_qc, load_display_mesh, read_mesh_qc
from canceros.mesh_runs import MeshInput, create_mesh, read_mesh

__all__ = ["imaging_db", "registry_db", "runtime"]


def mesh_source(data, *, cuboid=False):
    c, i, p, patient, _, storage, _ = data
    measurement = create_measurement(
        c,
        i,
        p,
        patient.patient_id,
        measurement_sources(data, cuboid=cuboid),
        storage,
        "mesh-qc-measure",
    )
    mesh = create_mesh(
        c,
        i,
        p,
        patient.patient_id,
        MeshInput(measurement_id=measurement.id),
        storage,
        "mesh-qc-original",
    )
    return measurement, mesh


def test_selection_budget_guidance_mask_authority_http_and_qc_withdrawal(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    measurement, mesh = mesh_source(imaging_db)
    value = MeshQCInput(mesh_run_id=mesh.id, triangle_budget=4)
    report = create_mesh_qc(c, i, p, patient.patient_id, value, storage, "mesh-qc-once")
    assert create_mesh_qc(c, i, p, patient.patient_id, value, storage, "mesh-qc-once") == report
    assert report.status == "validated" and not report.budget_met
    assert report.selected_triangles == 16 and report.selection == "original"
    assert len(report.objects) == 2 and all(o.original.mesh_volume_mm3 == 4 for o in report.objects)
    assert all(o.mask_volume_mm3 == 24 and o.original_minus_mask_mm3 == -20 for o in report.objects)
    assert read_mesh(c, i, p, patient.patient_id, mesh.id) == mesh
    assert read_measurement(c, i, p, patient.patient_id, measurement.id) == measurement
    _, asset = load_display_mesh(c, i, p, patient.patient_id, report.id, storage)
    assert {o.segmentation_id for o in asset.objects} == set(mesh.object_ids)
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/mesh-qc-reports/{report.id}"
    with client:
        assert client.get(path, headers=headers).status_code == 200
        assert client.get(path + "/asset", headers=headers).status_code == 200
        assert client.get(path + "/asset").status_code == 401
    withdraw_resource(
        c, i, p, patient.patient_id, report.id, WithdrawalInput(reason_code="scientific_review")
    )
    with pytest.raises(HTTPException):
        load_display_mesh(c, i, p, patient.patient_id, report.id, storage)
    assert read_mesh_qc(c, i, p, patient.patient_id, report.id) == report


def test_mesh_qc_shared_worker(runtime):
    data, queue, settings = runtime
    c, i, p, patient, _, storage, _ = data
    _, mesh = mesh_source(data, cuboid=True)
    request = ImagingJobInput(
        expected_revision=1,
        command=MeshQCCommand(operation="mesh_qc", input=MeshQCInput(mesh_run_id=mesh.id)),
    )
    job = enqueue_imaging(c, i, p, patient.patient_id, request, "mesh-qc-job", storage)
    c.commit()
    assert dispatch_imaging(c.engine, queue, p) == 1
    assert process_imaging_one(c.engine, queue, storage, settings) == job.id
    with c.engine.begin() as connection:
        result = read_imaging_job(connection, i, p, patient.patient_id, job.id)
        assert result.status == "succeeded"
        report, _ = load_display_mesh(
            connection, i, p, patient.patient_id, result.result_report_id, storage
        )
        assert report.budget_met
        assert report.selection == "lod" and report.lod_artifact_id != report.original_artifact_id
        assert report.selected_triangles < mesh.triangle_count
