"""Technical QC with no actual independent reference; current permitted-use checks."""

from uuid import uuid4

import numpy as np
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from test_alignment_runs import aligned
from test_annotation_import import command_for
from test_imaging_ingestion import http_session, imaging_db
from test_source_registry import registry_db, review

from canceros import segmentation_reviews
from canceros.annotation_import import import_annotations, read_annotation
from canceros.segmentation_reviews import (
    SegmentationQCInput,
    read_segmentation_qc,
    run_segmentation_qc,
)
from canceros.source_registry import add_review

__all__ = ["imaging_db", "registry_db"]


def qc_input(data):
    c, i, p, patient, _, storage, _ = data
    _, alignment = aligned(data)
    batch = import_annotations(c, i, p, patient.patient_id, command_for(alignment), storage)
    return SegmentationQCInput(segmentation_id=batch.segmentation_ids[0])


def test_qc_pass_is_not_independent_accuracy_or_anatomical_review(imaging_db):
    c, i, p, patient, component, storage, _ = imaging_db
    value = qc_input(imaging_db)
    report = run_segmentation_qc(c, i, p, patient.patient_id, value, storage, "qc-first")
    assert report.technical.technical_status == "pass"
    assert report.independent_accuracy.status == "not_evaluated"
    assert report.independent_accuracy.dice is None and report.independent_accuracy.hd95_mm is None
    assert report.case_attempt_number == 1
    assert run_segmentation_qc(c, i, p, patient.patient_id, value, storage, "qc-first") == report
    later = run_segmentation_qc(c, i, p, patient.patient_id, value, storage, "qc-second")
    assert later.id != report.id and later.case_attempt_number == 2
    annotation = read_annotation(c, i, p, patient.patient_id, value.segmentation_id)
    assert annotation.technical_qc == "pass"
    assert annotation.capabilities.numerical_region_volume_allowed
    assert not annotation.capabilities.anatomical_volume_allowed
    assert annotation.scientific_review == "pending" and annotation.publication == "draft"
    comparison = run_segmentation_qc(
        c,
        i,
        p,
        patient.patient_id,
        value.model_copy(update={"reference_segmentation_id": value.segmentation_id}),
        storage,
        "qc-self",
    )
    assert comparison.reference_eligibility_reason == "self_or_shared_mask"
    assert comparison.independent_accuracy.status == "not_evaluated"
    assert comparison.independent_accuracy.scored_cases == 0
    add_review(c, i, p, component, review(decision="denied"))
    with pytest.raises(HTTPException):
        run_segmentation_qc(c, i, p, patient.patient_id, value, storage, "qc-first")
    assert read_segmentation_qc(c, i, p, patient.patient_id, report.id) == report
    assert not read_annotation(
        c, i, p, patient.patient_id, value.segmentation_id
    ).capabilities.numerical_region_volume_allowed
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_qc_http_idempotency_ownership_and_no_accuracy_claim(imaging_db):
    c, i, p, patient, _, _, _ = imaging_db
    value = qc_input(imaging_db)
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/segmentation-qc-reports"
    headers = {**headers, "Idempotency-Key": "http-qc-1"}
    with client:
        result = client.post(path, json=value.model_dump(mode="json"), headers=headers)
        assert result.status_code == 201, result.text
        assert result.json()["technical"]["technical_status"] == "pass"
        assert result.json()["independent_accuracy"]["status"] == "not_evaluated"
        assert client.get(result.headers["Location"], headers=headers).json() == result.json()
        assert (
            client.post(path, json=value.model_dump(mode="json"), headers=headers).json()
            == result.json()
        )
        altered = {
            **value.model_dump(mode="json"),
            "reference_segmentation_id": str(value.segmentation_id),
        }
        assert client.post(path, json=altered, headers=headers).status_code == 409
        assert (
            client.get(
                result.headers["Location"].replace(str(patient.patient_id), str(uuid4())),
                headers=headers,
            ).status_code
            == 404
        )


def test_injected_failed_qc_attempt_is_retained_after_success(imaging_db, monkeypatch):
    c, i, p, patient, _, storage, _ = imaging_db
    value = qc_input(imaging_db)
    original = segmentation_reviews.inspect_mask
    # Explicit engineering fault injection; source bytes are not modified.
    monkeypatch.setattr(
        segmentation_reviews,
        "inspect_mask",
        lambda mask, geometry: original(np.zeros_like(mask), geometry),
    )
    failed = run_segmentation_qc(
        c, i, p, patient.patient_id, value, storage, "fault-injected-empty"
    )
    assert failed.technical.technical_status == "fail" and failed.technical_failed_attempts == 1
    assert not read_annotation(
        c, i, p, patient.patient_id, value.segmentation_id
    ).capabilities.numerical_region_volume_allowed
    monkeypatch.setattr(segmentation_reviews, "inspect_mask", original)
    recovered = run_segmentation_qc(
        c, i, p, patient.patient_id, value, storage, "after-injected-failure"
    )
    assert recovered.technical.technical_status == "pass" and recovered.case_attempt_number == 2
    assert recovered.technical_failed_attempts == 1
    assert read_segmentation_qc(c, i, p, patient.patient_id, failed.id) == failed
