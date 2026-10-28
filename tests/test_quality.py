from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_clinical_ingestion import clinical_db, row, stage
from test_source_registry import registry_db

from canceros.clinical_ingestion import BatchCommand, accept_batch
from canceros.identity import Identity
from canceros.lineage import derive_resource, processing_spec
from canceros.quality import (
    create_quality_report,
    read_quality_report,
    record_technical_validation,
    revalidate_source,
)

__all__ = ["clinical_db", "registry_db"]


def test_missing_zero_and_failed_mask_do_not_disable_clinical_display(clinical_db):
    connection, identity, project, patient, origin, _, storage = clinical_db
    receipt = stage(
        clinical_db,
        [
            row(
                origin,
                original_value="0",
                result={"form": "exact", "quantity": {"value": "0", "unit": "g/dL"}},
            )
        ],
    )
    result = accept_batch(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(source_artifact_id=receipt.artifact_id, expected_revision=1),
        "zero",
        storage,
    )
    mask_id = uuid4()
    derive_resource(
        connection,
        identity,
        project,
        patient.patient_id,
        mask_id,
        "segmentation",
        "a" * 64,
        [receipt.artifact_id],
        processing_spec(__file__, "deliberately-invalid-mask-fixture/1", "fixture/1", {}),
    )
    record_technical_validation(
        connection,
        identity,
        project,
        patient.patient_id,
        mask_id,
        "fail",
        "invalid-mask-fixture/1",
        {"status": "fail", "reason": "Engineering fixture — no real mask"},
    )
    reference = create_quality_report(connection, identity, project, patient.patient_id, 2)
    view = read_quality_report(connection, identity, project, patient.patient_id, reference.id)
    capabilities = {c.capability: c for c in view.report.capabilities}
    assert not view.stale and view.report.missing_numeric_results == 0
    assert capabilities["clinical_display"].status == "usable"
    assert capabilities["physical_measurement"].status == "invalid"
    assert capabilities["real_temporal_comparison"].status == "missing"
    assert result.record_ids[0] in capabilities["clinical_display"].resource_ids


def test_quarantine_revalidation_append_and_staleness_after_correction(clinical_db):
    connection, identity, project, patient, origin, _, storage = clinical_db
    bad = stage(clinical_db, [row(origin, original_value="not-a-number")])
    rejected = accept_batch(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(source_artifact_id=bad.artifact_id, expected_revision=1),
        "bad",
        storage,
    )
    assert rejected.status == "quarantined"
    first = revalidate_source(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(source_artifact_id=bad.artifact_id, expected_revision=1),
        storage,
    )
    second = revalidate_source(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(source_artifact_id=bad.artifact_id, expected_revision=1),
        storage,
    )
    assert first.id != second.id
    old = read_quality_report(connection, identity, project, patient.patient_id, first.id)
    assert (
        old.report.source_revalidation.status == "quarantined"
        and bad.artifact_id in old.report.quarantined_artifact_ids
    )
    good = stage(clinical_db, [row(origin)])
    accept_batch(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(source_artifact_id=good.artifact_id, expected_revision=1),
        "fixed-source",
        storage,
    )
    assert read_quality_report(connection, identity, project, patient.patient_id, first.id).stale
    with pytest.raises(HTTPException):
        read_quality_report(
            connection,
            Identity(identity.user_id, {project: "editor"}),
            project,
            patient.patient_id,
            first.id,
        )
    with pytest.raises(HTTPException):
        read_quality_report(connection, identity, project, uuid4(), first.id)
