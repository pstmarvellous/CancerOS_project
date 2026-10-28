"""Private per-label annotation import; no scientific-review assertions from clients."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_alignment_runs import aligned
from test_imaging_ingestion import http_session, imaging_db
from test_source_registry import registry_db, review

from canceros.annotation_contracts import AnnotationInput, LabelDefinition
from canceros.annotation_import import import_annotations, load_annotation_mask, read_annotation
from canceros.source_registry import add_review

__all__ = ["imaging_db", "registry_db"]


def command_for(report, annotation_class="anatomical_tumor_contour", meaning="tumor_region"):
    return AnnotationInput(
        alignment_run_id=report.id,
        annotation_class=annotation_class,
        authorship="unknown",
        labels=(
            LabelDefinition(label=1, meaning=meaning),
            LabelDefinition(label=2, meaning=meaning),
        ),
        source_annotation_evidence_sha256="c" * 64,
    )


def test_distinct_annotations_each_label_immutable_source_and_pending_review(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    _, alignment = aligned(imaging_db)
    command = command_for(alignment)
    batch = import_annotations(c, i, p, patient.patient_id, command, storage)
    assert batch.labels == [1, 2] and len(set(batch.segmentation_ids)) == 2
    assert batch.publication == "draft" and batch.scientific_review == "pending"
    assert import_annotations(c, i, p, patient.patient_id, command, storage) == batch
    assert (
        import_annotations(
            c,
            i,
            p,
            patient.patient_id,
            command.model_copy(update={"labels": tuple(reversed(command.labels))}),
            storage,
        )
        == batch
    )
    for annotation_id, label in zip(batch.segmentation_ids, (1, 2)):
        annotation, selected = load_annotation_mask(
            c, i, p, patient.patient_id, annotation_id, storage
        )
        assert annotation.label == label and selected.sum() == 1
        assert not selected.flags.writeable
        assert annotation.annotation.authorship == "unknown"
        assert annotation.capabilities.technical_qc_allowed
        assert not annotation.capabilities.anatomical_volume_allowed
        assert not annotation.capabilities.publication_allowed
        assert annotation.origin == "SYNTHETIC_GENERATED"
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(
                text("UPDATE imaging.segmentations SET label_value=9 WHERE id=:id"),
                {"id": annotation_id},
            )
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_annotation_meaning_versions_and_restrictions_remain_separate(imaging_db):
    c, i, p, patient, component, storage, _ = imaging_db
    _, alignment = aligned(imaging_db)
    original = import_annotations(c, i, p, patient.patient_id, command_for(alignment), storage)
    for annotation_class, meaning in (
        ("functional_enhancement_region", "functional_region"),
        ("bounding_box", "bounding_region"),
    ):
        batch = import_annotations(
            c, i, p, patient.patient_id, command_for(alignment, annotation_class, meaning), storage
        )
        assert batch.id != original.id
        annotation = read_annotation(c, i, p, patient.patient_id, batch.segmentation_ids[0])
        assert not annotation.capabilities.anatomical_volume_allowed
        assert not annotation.capabilities.anatomical_mesh_allowed
    assert (
        read_annotation(
            c, i, p, patient.patient_id, original.segmentation_ids[0]
        ).annotation.annotation_class
        == "anatomical_tumor_contour"
    )
    add_review(c, i, p, component, review(action="derivative_creation", decision="denied"))
    restricted = read_annotation(c, i, p, patient.patient_id, original.segmentation_ids[0])
    assert not restricted.capabilities.numerical_region_preview_allowed
    assert not restricted.capabilities.technical_qc_allowed
    with pytest.raises(HTTPException):
        import_annotations(c, i, p, patient.patient_id, command_for(alignment), storage)
    add_review(c, i, p, component, review(decision="denied"))
    with pytest.raises(HTTPException):
        load_annotation_mask(c, i, p, patient.patient_id, original.segmentation_ids[0], storage)


def test_invalid_label_dictionary_failed_alignment_and_patient_boundary(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    _, alignment = aligned(imaging_db)
    command = command_for(alignment)
    command = command.model_copy(
        update={"labels": (LabelDefinition(label=1, meaning="tumor_region"),)}
    )
    with pytest.raises(HTTPException) as mismatch:
        import_annotations(c, i, p, patient.patient_id, command, storage)
    assert mismatch.value.status_code == 422
    with pytest.raises(HTTPException) as ownership:
        import_annotations(c, i, p, uuid4(), command, storage)
    assert ownership.value.status_code == 404


def test_annotation_http_rejects_scientific_review_claims_and_reads_each_label(imaging_db):
    _, _, p, patient, _, _, _ = imaging_db
    _, alignment = aligned(imaging_db)
    command = command_for(alignment)
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/annotation-batches"
    with client:
        assert client.post(path, json=command.model_dump(mode="json")).status_code == 401
        payload = command.model_dump(mode="json")
        assert (
            client.post(
                path, json={**payload, "scientific_review": "qualified_reviewed"}, headers=headers
            ).status_code
            == 422
        )
        result = client.post(path, json=payload, headers=headers)
        assert result.status_code == 201, result.text
        assert client.get(result.headers["Location"], headers=headers).json() == result.json()
        for identity in result.json()["segmentation_ids"]:
            annotation = client.get(
                f"/api/v1/projects/{p}/patients/{patient.patient_id}/segmentations/{identity}",
                headers=headers,
            )
            assert (
                annotation.status_code == 200
                and annotation.json()["scientific_review"] == "pending"
            )
            assert not annotation.json()["capabilities"]["anatomical_volume_allowed"]


def test_quarantined_alignment_cannot_import_annotation(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    _, alignment = aligned(imaging_db, shift=30)
    assert alignment.status == "quarantined"
    with pytest.raises(HTTPException) as denied:
        import_annotations(c, i, p, patient.patient_id, command_for(alignment), storage)
    assert denied.value.status_code == 409
