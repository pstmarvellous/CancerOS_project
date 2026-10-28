"""Synthetic fixture identity and scalar history against actual PostgreSQL/private S3."""

from uuid import uuid4

import nibabel as nib
import numpy as np
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_annotation_import import command_for
from test_imaging_ingestion import http_session, imaging_db, stage
from test_registration_runs import registration_source
from test_source_registry import registry_db

from canceros.alignment_runs import AlignmentInput, read_alignment, run_alignment
from canceros.annotation_import import import_annotations, read_annotation
from canceros.contracts import RelativeTime, UnknownTime
from canceros.identity import Identity
from canceros.lesion_tracking import (
    AssociationInput,
    LesionInput,
    SeriesInput,
    append_association,
    create_lesion,
    create_series,
    list_associations,
    list_lesions,
    load_usable_series,
    read_series,
)
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.mask_alignment import AlignmentConfig
from canceros.mask_associations import MaskAssociationInput, bind_mask
from canceros.measurement_runs import MeasurementInput, create_measurement
from canceros.persistence import capture_revision, load_revision
from canceros.segmentation_reviews import SegmentationQCInput, run_segmentation_qc

__all__ = ["imaging_db", "registry_db"]


def source(data):
    c, i, p, patient, _, storage, _ = data
    registration, union = registration_source(data)
    original = read_annotation(c, i, p, patient.patient_id, union.selections[0].segmentation_id)
    alignment = read_alignment(c, i, p, patient.patient_id, original.alignment_run_id)
    array = np.zeros((3, 4, 2), dtype=np.uint16)
    array[1, 1, 0] = 1
    array[1, 2, 1] = 2
    affine = np.diag([2.0, 3.0, 4.0, 1.0])
    affine[0, 3] = 2
    mask = nib.Nifti1Image(array, affine)
    mask.header.set_xyzt_units("mm")
    staged, _ = stage(data, mask.to_bytes())
    binding = bind_mask(
        c,
        i,
        p,
        patient.patient_id,
        MaskAssociationInput(
            mask_file_id=staged.artifact_id,
            target_image_id=registration.fixed_image_id,
            expected_study_id=c.execute(
                text(
                    "SELECT i.association->>'study_id' FROM imaging.volume_validations v JOIN imaging.imports i ON i.id=v.import_id WHERE v.project_id=:p AND v.patient_id=:u AND v.artifact_id=:id"
                ),
                {"p": p, "u": patient.patient_id, "id": registration.fixed_image_id},
            ).scalar_one(),
            evidence_sha256="a" * 64,
        ),
        storage,
    )
    fixed = run_alignment(
        c,
        i,
        p,
        patient.patient_id,
        AlignmentInput(
            association_id=binding.id,
            mask_file_id=staged.artifact_id,
            target_image_id=registration.fixed_image_id,
            mask_study_id=binding.study_id,
            association_evidence_sha256="a" * 64,
            config=AlignmentConfig(expected_labels=(1, 2), mode="exact_grid"),
        ),
        storage,
    )
    annotations, measurements = [], []
    for n, aligned in enumerate((alignment, fixed)):
        batch = import_annotations(
            c,
            i,
            p,
            patient.patient_id,
            command_for(aligned).model_copy(
                update={"method_reference": "engineering_fixture_mask"}
            ),
            storage,
        )
        annotations.append(batch.segmentation_ids)
        for j, seg in enumerate(batch.segmentation_ids):
            run_segmentation_qc(
                c,
                i,
                p,
                patient.patient_id,
                SegmentationQCInput(segmentation_id=seg),
                storage,
                f"tracking-qc-{n}-{j}",
            )
        measurements.append(
            create_measurement(
                c,
                i,
                p,
                patient.patient_id,
                MeasurementInput(segmentation_ids=[batch.segmentation_ids[0]], expected_revision=1),
                storage,
                f"tracking-measure-{n}",
            )
        )
    origin = uuid4()
    c.execute(
        text(
            "INSERT INTO source.timeline_origins(id,project_id,patient_id,reference_meaning,time_domain) VALUES(:id,:p,:u,'Artificial tracking day zero','simulation')"
        ),
        {"id": origin, "p": p, "u": patient.patient_id},
    )
    return annotations, measurements, origin, union


def lesion(data, segmentation, key="lesion"):
    c, i, p, patient, _, storage, _ = data
    return create_lesion(
        c,
        i,
        p,
        patient.patient_id,
        LesionInput(
            baseline_segmentation_id=segmentation, evidence_sha256="b" * 64, expected_revision=1
        ),
        storage,
        key,
    )


def event(data, identity, segmentation, measurement, origin, day, key, **changes):
    c, i, p, patient, _, storage, _ = data
    value = AssociationInput(
        lesion_id=identity.id,
        segmentation_id=segmentation,
        measurement_id=measurement.id if measurement else None,
        status="matched",
        time=RelativeTime(
            basis="relative_day",
            value=str(day),
            time_domain="simulation",
            timeline_origin_id=origin,
        ),
        evidence_sha256="c" * 64,
        expected_revision=1,
    )
    return append_association(
        c, i, p, patient.patient_id, value.model_copy(update=changes), storage, key
    )


def test_owned_identity_corrected_mapping_and_immutable_series(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    annotations, measures, origin, _ = source(imaging_db)
    first = lesion(imaging_db, annotations[0][0])
    assert first.id != annotations[0][0] and first.scientific_review == "pending"
    assert lesion(imaging_db, annotations[0][0]) == first
    left = event(imaging_db, first, annotations[0][0], measures[0], origin, 0, "first")
    right = event(imaging_db, first, annotations[1][0], measures[1], origin, 10, "second")
    value = SeriesInput(lesion_id=first.id, expected_revision=1)
    series = create_series(c, i, p, patient.patient_id, value, storage, "series")
    assert len(series.points) == 2 and series.changes[0].eligibility
    assert series.changes[0].absolute_mm3 == "0" and series.changes[0].percent_change == "0"
    assert series.origin == "SYNTHETIC_GENERATED" and series.clinical_response == "not_assessed"
    assert load_usable_series(c, i, p, patient.patient_id, series.id) == series
    second = lesion(imaging_db, annotations[0][1], "second-lesion")
    corrected = event(
        imaging_db,
        second,
        annotations[1][0],
        measures[1],
        origin,
        10,
        "correction",
        supersedes_event_id=right.id,
    )
    assert corrected.version == 2
    view = read_series(c, i, p, patient.patient_id, series.id)
    assert view.stale and not view.current_use_allowed and view.report == series
    assert "association_history_changed" in view.restrictions
    rebuilt = create_series(c, i, p, patient.patient_id, value, storage, "rebuilt")
    assert [point.association.id for point in rebuilt.points] == [left.id]
    assert create_series(c, i, p, patient.patient_id, value, storage, "series") == series
    with pytest.raises(HTTPException):
        event(
            imaging_db,
            first,
            annotations[1][0],
            measures[1],
            origin,
            20,
            "old-correction",
            supersedes_event_id=right.id,
        )
    assert len(list_associations(c, i, p, patient.patient_id)) == 3
    assert len(list_lesions(c, i, p, patient.patient_id)) == 2
    for table, identifier in (
        ("lesion_identities", first.id),
        ("lesion_association_events", left.id),
        ("lesion_measurement_series", series.id),
    ):
        with pytest.raises(DBAPIError), c.begin_nested():
            c.execute(
                text(f"UPDATE imaging.{table} SET report='{{}}'::jsonb WHERE id=:id"),
                {"id": identifier},
            )
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    capture_revision(c, p, patient.patient_id, 2, load_revision(c, p, patient.patient_id, 1))
    c.execute(
        text("UPDATE source.research_patients SET data_revision=2 WHERE project_id=:p AND id=:u"),
        {"p": p, "u": patient.patient_id},
    )
    assert create_series(c, i, p, patient.patient_id, value, storage, "series") == series
    assert (
        "patient_revision_changed"
        in read_series(c, i, p, patient.patient_id, series.id).restrictions
    )


def test_ambiguous_split_merge_missing_time_and_measurement_stay_gaps(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    annotations, measures, origin, union = source(imaging_db)
    first = lesion(imaging_db, annotations[0][0])
    second = lesion(imaging_db, annotations[0][1], "multifocal")
    a = event(
        imaging_db,
        first,
        annotations[0][0],
        measures[0],
        origin,
        0,
        "candidate",
        status="candidate",
    )
    b = event(
        imaging_db,
        first,
        annotations[1][0],
        None,
        origin,
        10,
        "unresolved",
        status="unresolved",
        time=UnknownTime(basis="unknown", missing_reason="not_recorded", time_domain="simulation"),
    )
    series = create_series(
        c,
        i,
        p,
        patient.patient_id,
        SeriesInput(lesion_id=first.id, expected_revision=1),
        storage,
        "gap-series",
    )
    assert series.points[1].scalar.volume_mm3 is None
    assert (
        "measurement_not_recorded" in series.points[1].gaps
        and "source_time_unknown" in series.points[1].gaps
    )
    assert not series.changes[0].eligibility
    split = event(
        imaging_db,
        first,
        annotations[0][0],
        measures[0],
        origin,
        0,
        "split",
        supersedes_event_id=a.id,
        relation="split",
        related_lesion_ids=[second.id],
    )
    merge = event(
        imaging_db,
        first,
        annotations[1][0],
        measures[1],
        origin,
        10,
        "merge",
        supersedes_event_id=b.id,
        relation="merge",
        related_lesion_ids=[second.id],
    )
    assert split.input.related_lesion_ids == [second.id] and merge.input.relation == "merge"
    revised = create_series(
        c,
        i,
        p,
        patient.patient_id,
        SeriesInput(lesion_id=first.id, expected_revision=1),
        storage,
        "split-series",
    )
    assert not revised.changes[0].eligibility
    assert all(
        "split_merge_requires_qualified_identity_review" in point.gaps for point in revised.points
    )
    with pytest.raises(HTTPException) as wrong_union:
        event(
            imaging_db,
            first,
            annotations[0][0],
            union,
            origin,
            0,
            "union",
            supersedes_event_id=split.id,
        )
    assert wrong_union.value.status_code == 409
    with pytest.raises(ValidationError):
        AssociationInput(
            lesion_id=first.id,
            segmentation_id=annotations[0][0],
            status="matched",
            relation="split",
            time=UnknownTime(basis="unknown", missing_reason="unknown", time_domain="simulation"),
            evidence_sha256="a" * 64,
            expected_revision=1,
        )


def test_authorization_ownership_retry_qc_withdrawal(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    annotations, measures, origin, _ = source(imaging_db)
    value = LesionInput(
        baseline_segmentation_id=annotations[0][0], evidence_sha256="a" * 64, expected_revision=1
    )
    with pytest.raises(HTTPException) as editor:
        create_lesion(
            c, Identity(i.user_id, {p: "editor"}), p, patient.patient_id, value, storage, "editor"
        )
    assert editor.value.status_code == 403
    with pytest.raises(HTTPException):
        create_lesion(c, i, p, uuid4(), value, storage, "other-patient")
    first = create_lesion(c, i, p, patient.patient_id, value, storage, "owned")
    with pytest.raises(HTTPException):
        create_lesion(
            c,
            i,
            p,
            patient.patient_id,
            value.model_copy(update={"evidence_sha256": "b" * 64}),
            storage,
            "owned",
        )
    with pytest.raises(HTTPException):
        event(imaging_db, first, annotations[0][0], measures[0], uuid4(), 0, "wrong-origin")
    association = event(imaging_db, first, annotations[0][0], measures[0], origin, 0, "owned-event")
    series = create_series(
        c,
        i,
        p,
        patient.patient_id,
        SeriesInput(lesion_id=first.id, expected_revision=1),
        storage,
        "owned-series",
    )
    assert not read_series(c, i, p, patient.patient_id, series.id).stale
    qc = measures[0].selections[0].qc_report_id
    withdraw_resource(
        c, i, p, patient.patient_id, qc, WithdrawalInput(reason_code="scientific_review")
    )
    view = read_series(c, i, p, patient.patient_id, series.id)
    assert view.stale and view.report == series
    assert "current_annotation_measurement_or_qc_unavailable" in view.restrictions
    with pytest.raises(HTTPException):
        load_usable_series(c, i, p, patient.patient_id, series.id)
    with pytest.raises(HTTPException):
        event(imaging_db, first, annotations[0][0], measures[0], origin, 0, "owned-event")
    assert association.scientific_review == "pending"


def test_private_lesion_association_and_series_http_receipts(imaging_db):
    _, _, p, patient, _, _, _ = imaging_db
    annotations, measures, origin, _ = source(imaging_db)
    client, headers = http_session(imaging_db)
    root = f"/api/v1/projects/{p}/patients/{patient.patient_id}"
    command = LesionInput(
        baseline_segmentation_id=annotations[0][0], evidence_sha256="a" * 64, expected_revision=1
    )
    with client:
        response = client.post(
            root + "/lesions",
            json=command.model_dump(mode="json"),
            headers={**headers, "Idempotency-Key": "http-lesion"},
        )
        assert response.status_code == 201
        identity = response.json()["id"]
        assert client.get(response.headers["Location"], headers=headers).json()["id"] == identity
        assert client.get(response.headers["Location"]).status_code == 401
        assert (
            client.post(
                root + "/lesions",
                json=command.model_dump(mode="json"),
                headers={**headers, "Idempotency-Key": "http-lesion"},
            ).json()["id"]
            == identity
        )
        value = AssociationInput(
            lesion_id=identity,
            segmentation_id=annotations[0][0],
            measurement_id=measures[0].id,
            status="matched",
            time=RelativeTime(
                basis="relative_day", value="0", time_domain="simulation", timeline_origin_id=origin
            ),
            evidence_sha256="b" * 64,
            expected_revision=1,
        )
        response = client.post(
            root + "/lesion-associations",
            json=value.model_dump(mode="json"),
            headers={**headers, "Idempotency-Key": "http-association"},
        )
        assert response.status_code == 201
        assert (
            client.get(response.headers["Location"], headers=headers).json()["id"]
            == response.json()["id"]
        )
        response = client.post(
            root + "/measurement-series",
            json={"lesion_id": identity, "expected_revision": 1},
            headers={**headers, "Idempotency-Key": "http-series"},
        )
        assert response.status_code == 201
        view = client.get(response.headers["Location"], headers=headers)
        assert view.status_code == 200 and not view.json()["stale"]
        assert view.json()["report"]["points"][0]["scalar"]["relative_day"] == "0"
