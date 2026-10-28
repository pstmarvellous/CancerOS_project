"""Artificial distinct examinations, real private worker and no genuine-pair acceptance."""

from uuid import uuid4

import nibabel as nib
import numpy as np
import pytest
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import text
from test_alignment_runs import aligned
from test_annotation_import import command_for
from test_imaging_ingestion import http_session, imaging_db, preview_command, stage
from test_imaging_jobs import runtime
from test_source_registry import registry_db

from canceros.annotation_import import import_annotations
from canceros.identity import Identity
from canceros.imaging_ingestion import confirm_import, preview_imaging
from canceros.imaging_jobs import (
    ImagingJobInput,
    RegistrationCommand,
    dispatch_imaging,
    enqueue_imaging,
    process_imaging_one,
    read_imaging_job,
)
from canceros.imaging_preprocessing import PreprocessingConfig
from canceros.imaging_volumes import GeometryValidationInput, validate_volume
from canceros.lineage import (
    WithdrawalInput,
    lineage_detail,
    require_resource_action,
    withdraw_resource,
)
from canceros.measurement_runs import MeasurementInput, create_measurement, read_measurement
from canceros.preprocessing_runs import PreprocessInput, run_preprocessing
from canceros.registration_runs import RegistrationInput, read_registration, run_registration
from canceros.segmentation_reviews import SegmentationQCInput, run_segmentation_qc
from canceros.source_registry import SourceAction

__all__ = ["imaging_db", "registry_db", "runtime"]


def registration_source(data):
    c, i, p, patient, _, storage, config = data
    _, alignment = aligned(data)
    batch = import_annotations(c, i, p, patient.patient_id, command_for(alignment), storage)
    for index, segmentation in enumerate(batch.segmentation_ids):
        run_segmentation_qc(
            c,
            i,
            p,
            patient.patient_id,
            SegmentationQCInput(segmentation_id=segmentation),
            storage,
            f"registration-source-qc-{index}",
        )
    measurement = create_measurement(
        c,
        i,
        p,
        patient.patient_id,
        MeasurementInput(segmentation_ids=batch.segmentation_ids, expected_revision=1),
        storage,
        "registration-measure-source",
    )
    affine = np.diag([2.0, 3.0, 4.0, 1.0])
    affine[0, 3] = 2
    image = nib.Nifti1Image(np.arange(24, dtype=np.int16).reshape(3, 4, 2) + 1, affine)
    image.header.set_xyzt_units("mm")
    receipt, _ = stage(data, image.to_bytes())
    command = preview_command(patient, receipt)
    command = command.model_copy(
        update={
            "association": command.association.model_copy(
                update={
                    "source_study_key": SecretStr("ARTIFICIAL-FIXED-SECOND-EXAM"),
                    "source_series_key": SecretStr("ARTIFICIAL-FIXED-SECOND-SERIES"),
                }
            )
        }
    )
    imported = preview_imaging(c, i, p, patient.patient_id, command, storage, config)
    confirm_import(c, i, p, patient.patient_id, imported.id)
    volume = validate_volume(
        c, i, p, patient.patient_id, GeometryValidationInput(import_id=imported.id), storage
    )
    moving = np.array([[0.0, 0, 0], [4, 0, 0], [0, 9, 0], [0, 0, 4]])
    fixed = moving + [2, 0, 0]
    value = RegistrationInput(
        fixed_image_id=volume.volume_artifact_id,
        moving_image_id=alignment.target_image_id,
        moving_segmentation_id=batch.segmentation_ids[0],
        moving_qc_report_id=next(
            s.qc_report_id
            for s in measurement.selections
            if s.segmentation_id == batch.segmentation_ids[0]
        ),
        fixed_relative_day=0,
        moving_relative_day=10,
        time_association_evidence_sha256="b" * 64,
        moving_landmarks=moving.tolist(),
        fixed_landmarks=fixed.tolist(),
        moving_holdout_landmarks=[[2, 3, 0]],
        fixed_holdout_landmarks=[[4, 3, 0]],
    )
    return value, measurement


def test_fixture_registration_preserves_scalar_history_and_requires_real_review(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    value, measurement = registration_source(imaging_db)
    with pytest.raises(HTTPException) as editor:
        run_registration(
            c,
            Identity(i.user_id, {p: "editor"}),
            p,
            patient.patient_id,
            value,
            storage,
            "editor-cannot-attest-exams",
            1,
        )
    assert editor.value.status_code == 403
    report = run_registration(c, i, p, patient.patient_id, value, storage, "register-once", 1)
    assert report.status == "fixture_aligned_pending_review" and report.output_artifact_id
    assert not report.genuine_exam_pair_verified and not report.overlay_allowed
    np.testing.assert_allclose(
        np.array(report.numerical.moving_to_fixed_world)[:3, 3], [2, 0, 0], atol=1e-8
    )
    assert (
        report.mask_alignment.status == "pass"
        and report.bounds_overlap_fraction == pytest.approx(1)
    )
    detail = lineage_detail(c, i, p, patient.patient_id, report.id).model_dump_json()
    assert all(
        name not in detail
        for name in (
            "moving_landmarks",
            "fixed_landmarks",
            "moving_holdout_landmarks",
            "fixed_holdout_landmarks",
        )
    )
    assert read_measurement(c, i, p, patient.patient_id, measurement.id) == measurement
    selected = run_preprocessing(
        c,
        i,
        p,
        patient.patient_id,
        PreprocessInput(
            volume_artifact_id=value.moving_image_id,
            config=PreprocessingConfig(expected_sequence="t1", method="identity"),
        ),
        storage,
    )
    assert selected.output_artifact_id != value.moving_image_id
    with pytest.raises(HTTPException) as same_study:
        run_registration(
            c,
            i,
            p,
            patient.patient_id,
            value.model_copy(update={"fixed_image_id": selected.output_artifact_id}),
            storage,
            "same-study-distinct-derived-images",
            1,
        )
    assert same_study.value.status_code == 409
    assert (
        run_registration(c, i, p, patient.patient_id, value, storage, "register-once", 1) == report
    )
    with pytest.raises(HTTPException):
        run_registration(c, i, p, uuid4(), value, storage, "other-patient", 1)
    with pytest.raises(HTTPException):
        run_registration(
            c,
            i,
            p,
            patient.patient_id,
            value.model_copy(update={"fixed_image_id": value.moving_image_id}),
            storage,
            "same-exam",
            1,
        )
    with pytest.raises(HTTPException):
        run_registration(
            c,
            i,
            p,
            patient.patient_id,
            value.model_copy(update={"moving_relative_day": 0}),
            storage,
            "no-time-order",
            1,
        )
    failed = run_registration(
        c,
        i,
        p,
        patient.patient_id,
        value.model_copy(update={"fixed_holdout_landmarks": [(7.0, 9.0, 4.0)]}),
        storage,
        "poor-fit",
        1,
    )
    assert failed.status == "blocked" and not failed.output_artifact_id
    assert read_measurement(c, i, p, patient.patient_id, measurement.id) == measurement
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    client, headers = http_session(imaging_db)
    with client:
        path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/registrations/{report.id}"
        assert client.get(path, headers=headers).status_code == 200
        assert client.get(path).status_code == 401
    withdraw_resource(
        c,
        i,
        p,
        patient.patient_id,
        value.moving_qc_report_id,
        WithdrawalInput(reason_code="scientific_review"),
    )
    with pytest.raises(HTTPException):
        require_resource_action(c, i, p, patient.patient_id, report.id, SourceAction.INTERNAL)
    assert read_registration(c, i, p, patient.patient_id, report.id) == report


def test_registration_shared_job_pins_inputs_and_returns_pending_review(runtime):
    data, queue, config = runtime
    c, i, p, patient, _, storage, _ = data
    value, _ = registration_source(data)
    request = ImagingJobInput(
        expected_revision=1, command=RegistrationCommand(operation="registration", input=value)
    )
    job = enqueue_imaging(c, i, p, patient.patient_id, request, "registration-worker", storage)
    c.commit()
    assert dispatch_imaging(c.engine, queue, p) == 1
    assert process_imaging_one(c.engine, queue, storage, config) == job.id
    with c.engine.begin() as connection:
        result = read_imaging_job(connection, i, p, patient.patient_id, job.id)
        assert result.status == "succeeded" and result.result_report_id
        report = read_registration(connection, i, p, patient.patient_id, result.result_report_id)
        assert report.numerical.status == "pass" and not report.overlay_allowed
    changed = enqueue_imaging(
        c, i, p, patient.patient_id, request, "registration-before-new-qc", storage
    )
    c.commit()
    run_segmentation_qc(
        c,
        i,
        p,
        patient.patient_id,
        SegmentationQCInput(segmentation_id=value.moving_segmentation_id),
        storage,
        "new-qc-after-registration-enqueue",
    )
    c.commit()
    assert dispatch_imaging(c.engine, queue, p) == 1
    assert process_imaging_one(c.engine, queue, storage, config) == changed.id
    with c.engine.begin() as connection:
        assert read_imaging_job(connection, i, p, patient.patient_id, changed.id).status == "failed"
