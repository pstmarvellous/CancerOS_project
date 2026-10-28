"""Revision-pinned actual SQL/S3 region measurements with restricted clinical meaning."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from test_alignment_runs import aligned
from test_annotation_import import command_for
from test_imaging_ingestion import http_session, imaging_db
from test_source_registry import registry_db, review

from canceros.annotation_import import import_annotations, read_annotation
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.measurement_runs import (
    MeasurementInput,
    create_measurement,
    load_usable_measurement,
    read_measurement,
)
from canceros.persistence import capture_revision
from canceros.quality import create_quality_report, read_quality_report
from canceros.segmentation_reviews import SegmentationQCInput, run_segmentation_qc
from canceros.source_registry import add_review

__all__ = ["imaging_db", "registry_db"]


def measurement_sources(data, *, qc=True, functional=False, cuboid=False):
    c, i, p, patient, _, storage, _ = data
    _, alignment = aligned(data, cuboid=cuboid)
    value = (
        command_for(alignment, "functional_enhancement_region", "functional_region")
        if functional
        else command_for(alignment)
    )
    batch = import_annotations(c, i, p, patient.patient_id, value, storage)
    if qc:
        for index, identity in enumerate(batch.segmentation_ids):
            run_segmentation_qc(
                c,
                i,
                p,
                patient.patient_id,
                SegmentationQCInput(segmentation_id=identity),
                storage,
                "measurement-source-qc-" + str(index),
            )
    return MeasurementInput(segmentation_ids=batch.segmentation_ids, expected_revision=1)


def test_explicit_label_union_exact_volume_revision_and_history(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    value = measurement_sources(imaging_db)
    report = create_measurement(c, i, p, patient.patient_id, value, storage, "measurement-original")
    assert report.values.volume_mm3 == "48" and report.values.exact_volume_cm3 == "0.048"
    assert report.values.voxel_count == 2 and report.values.centroid_ras_mm == ("2", "4.5", "2")
    assert [selection.label for selection in sorted(report.selections, key=lambda s: s.label)] == [
        1,
        2,
    ]
    assert report.input_revision == 1 and report.origin == "SYNTHETIC_GENERATED"
    assert (
        report.source_time_basis == "not_recorded"
        and report.values.uncertainty == "not_established"
    )
    reversed_selection = value.model_copy(
        update={"segmentation_ids": list(reversed(value.segmentation_ids))}
    )
    assert (
        create_measurement(
            c, i, p, patient.patient_id, reversed_selection, storage, "measurement-original"
        )
        == report
    )
    capture_revision(c, p, patient.patient_id, 2, {"members": [], "fixture_revision_change": True})
    c.execute(
        text("UPDATE source.research_patients SET data_revision=2 WHERE project_id=:p AND id=:u"),
        {"p": p, "u": patient.patient_id},
    )
    assert read_measurement(c, i, p, patient.patient_id, report.id) == report
    assert (
        create_measurement(c, i, p, patient.patient_id, value, storage, "measurement-original")
        == report
    )
    with pytest.raises(HTTPException) as stale:
        create_measurement(c, i, p, patient.patient_id, value, storage, "stale-new-command")
    assert stale.value.status_code == 409
    anatomy = value.model_copy(
        update={"definition": "anatomical_tumor_volume", "expected_revision": 2}
    )
    unavailable = create_measurement(
        c, i, p, patient.patient_id, anatomy, storage, "unqualified-anatomy"
    )
    assert (
        unavailable.values.availability == "unavailable" and unavailable.values.volume_mm3 is None
    )
    assert "qualified_authentic_anatomical_review_not_established" in unavailable.eligibility_blocks
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    quality = create_quality_report(c, i, p, patient.patient_id, 2)
    # Withdrawing the QC evidence also blocks downstream use of its measurement.
    withdraw_resource(
        c,
        i,
        p,
        patient.patient_id,
        report.selections[0].qc_report_id,
        WithdrawalInput(reason_code="scientific_review"),
    )
    assert (
        read_annotation(
            c, i, p, patient.patient_id, report.selections[0].segmentation_id
        ).qc_evidence_status
        == "withdrawn_or_unavailable"
    )
    with pytest.raises(HTTPException):
        load_usable_measurement(c, i, p, patient.patient_id, report.id)
    assert read_measurement(c, i, p, patient.patient_id, report.id) == report
    assert read_quality_report(c, i, p, patient.patient_id, quality.id).stale


def test_missing_qc_is_unavailable_and_source_withdrawal_blocks_reuse(imaging_db):
    c, i, p, patient, component, storage, _ = imaging_db
    value = measurement_sources(imaging_db, qc=False)
    report = create_measurement(c, i, p, patient.patient_id, value, storage, "without-qc")
    assert report.values.volume_mm3 is None and report.values.availability == "unavailable"
    assert len(report.selections) == 2 and all(
        s.qc_validation_id is None for s in report.selections
    )
    assert create_measurement(c, i, p, patient.patient_id, value, storage, "without-qc") == report
    add_review(c, i, p, component, review(decision="denied"))
    with pytest.raises(HTTPException):
        create_measurement(c, i, p, patient.patient_id, value, storage, "without-qc")
    assert read_measurement(c, i, p, patient.patient_id, report.id) == report


def test_functional_region_http_is_labeled_and_owned(imaging_db):
    _, _, p, patient, _, _, _ = imaging_db
    value = measurement_sources(imaging_db, functional=True).model_copy(
        update={"definition": "functional_region_volume"}
    )
    client, headers = http_session(imaging_db)
    headers = {**headers, "Idempotency-Key": "http-functional-volume"}
    path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/physical-measurements"
    with client:
        result = client.post(path, json=value.model_dump(mode="json"), headers=headers)
        assert result.status_code == 201, result.text
        assert result.json()["definition"] == "functional_region_volume"
        assert result.json()["values"]["volume_mm3"] == "48"
        assert (
            result.json()["scientific_review"] == "pending"
            and result.json()["publication"] == "draft"
        )
        assert client.get(result.headers["Location"], headers=headers).json() == result.json()
        foreign = result.headers["Location"].replace(str(patient.patient_id), str(uuid4()))
        assert client.get(foreign, headers=headers).status_code == 404
