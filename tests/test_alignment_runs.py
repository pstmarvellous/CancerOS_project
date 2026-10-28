"""Owned image/mask association with actual private SQL/S3; no anatomical acceptance."""

from uuid import uuid4

import nibabel as nib
import numpy as np
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from test_imaging_ingestion import http_session, imaging_db, stage
from test_imaging_volumes import confirmed
from test_source_registry import registry_db, review

from canceros.alignment_runs import AlignmentInput, load_aligned_mask, read_overlay, run_alignment
from canceros.imaging_volumes import GeometryValidationInput, validate_volume
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.mask_alignment import AlignmentConfig
from canceros.mask_associations import MaskAssociationInput, bind_mask
from canceros.source_registry import add_review

__all__ = ["imaging_db", "registry_db"]


def aligned(data, *, shift=0, invalid=False, cuboid=False):
    c, i, p, patient, _, storage, _ = data
    imported = confirmed(data)
    volume = validate_volume(
        c, i, p, patient.patient_id, GeometryValidationInput(import_id=imported.id), storage
    )
    array = np.zeros((3, 4, 2), dtype=np.float32 if invalid else np.uint16)
    array[1, 1, 0] = 0.5 if invalid else 1
    array[1, 2, 1] = 2
    if cuboid:
        array[:1] = 1
        array[1:] = 2
    affine = np.diag([2.0, 3.0, 4.0, 1.0])
    affine[0, 3] = shift
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
            target_image_id=volume.volume_artifact_id,
            expected_study_id=imported.study_id,
            evidence_sha256="a" * 64,
        ),
        storage,
    )
    command = AlignmentInput(
        association_id=binding.id,
        mask_file_id=staged.artifact_id,
        target_image_id=volume.volume_artifact_id,
        mask_study_id=imported.study_id,
        association_evidence_sha256="a" * 64,
        config=AlignmentConfig(
            expected_labels=(1, 2), mode="nearest_neighbor" if shift else "exact_grid"
        ),
    )
    report = run_alignment(c, i, p, patient.patient_id, command, storage)
    return command, report


def test_alignment_immutable_multilabel_output_overlay_and_rights(imaging_db):
    c, i, p, patient, component, storage, _ = imaging_db
    command, report = aligned(imaging_db)
    assert report.status == "aligned_pending_review" and report.publication == "draft"
    assert report.reviewer_acceptance == "pending"
    assert report.output_artifact_id and report.preview_artifact_id
    assert run_alignment(c, i, p, patient.patient_id, command, storage) == report
    loaded, array = load_aligned_mask(c, i, p, patient.patient_id, report.id, storage)
    assert loaded == report and not array.flags.writeable
    assert set(np.unique(array)) == {0, 1, 2}
    preview = read_overlay(c, i, p, patient.patient_id, report.id, storage)
    assert preview.target_shape_xyz == (3, 4, 2)
    assert len(preview.intensity_rows) == 4 and len(preview.label_rows[0]) == 3
    assert max(v for row in preview.label_rows for v in row) > 0
    assert "object_key" not in preview.model_dump_json()
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    with pytest.raises(HTTPException) as wrong_study:
        run_alignment(
            c,
            i,
            p,
            patient.patient_id,
            command.model_copy(update={"mask_study_id": uuid4()}),
            storage,
        )
    assert wrong_study.value.status_code == 409
    with pytest.raises(HTTPException) as wrong_patient:
        run_alignment(c, i, p, uuid4(), command, storage)
    assert wrong_patient.value.status_code == 404
    add_review(c, i, p, component, review(decision="denied"))
    with pytest.raises(HTTPException):
        read_overlay(c, i, p, patient.patient_id, report.id, storage)
    with pytest.raises(HTTPException):
        run_alignment(c, i, p, patient.patient_id, command, storage)


@pytest.mark.parametrize("changes", [{"shift": 30}, {"invalid": True}])
def test_failed_alignment_has_no_ready_mask_or_preview(imaging_db, changes):
    c, i, p, patient, _, storage, _ = imaging_db
    _, report = aligned(imaging_db, **changes)
    assert report.status == "quarantined" and report.output_artifact_id is None
    assert report.preview_artifact_id is None and report.geometry is None
    with pytest.raises(HTTPException):
        load_aligned_mask(c, i, p, patient.patient_id, report.id, storage)
    with pytest.raises(HTTPException):
        read_overlay(c, i, p, patient.patient_id, report.id, storage)


def test_alignment_http_role_and_private_overlay(imaging_db, caplog):
    c, i, p, patient, _, _, _ = imaging_db
    command, report = aligned(imaging_db)
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/mask-alignments"
    with client:
        binding_path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/mask-associations"
        bound = client.post(
            binding_path,
            json={
                "mask_file_id": str(command.mask_file_id),
                "target_image_id": str(command.target_image_id),
                "expected_study_id": str(command.mask_study_id),
                "evidence_sha256": command.association_evidence_sha256,
            },
            headers=headers,
        )
        assert bound.status_code == 201 and bound.json()["id"] == str(command.association_id)
        assert client.get(bound.headers["Location"], headers=headers).json() == bound.json()
        assert client.post(path, json=command.model_dump(mode="json")).status_code == 401
        result = client.post(path, json=command.model_dump(mode="json"), headers=headers)
        assert result.status_code == 201, result.text
        assert result.json()["id"] == str(report.id)
        assert client.get(result.headers["Location"], headers=headers).json() == result.json()
        preview = client.get(result.headers["Location"] + "/overlay", headers=headers)
        assert preview.status_code == 200
        assert preview.json()["kind"] == "SYNTHETIC_ENGINEERING_FIXTURE_OVERLAY"
        assert "ARTIFICIAL-STUDY" not in preview.text + result.text + caplog.text
        with c.engine.begin() as writer:
            writer.execute(
                text(
                    "UPDATE access.memberships SET role='viewer' WHERE project_id=:p AND user_id=:u"
                ),
                {"p": p, "u": i.user_id},
            )
        assert (
            client.post(path, json=command.model_dump(mode="json"), headers=headers).status_code
            == 403
        )


def test_withdrawn_alignment_output_cannot_replay_success(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    command, report = aligned(imaging_db)
    withdraw_resource(
        c,
        i,
        p,
        patient.patient_id,
        report.output_artifact_id,
        WithdrawalInput(reason_code="scientific_review"),
    )
    with pytest.raises(HTTPException) as denied:
        run_alignment(c, i, p, patient.patient_id, command, storage)
    assert denied.value.status_code == 409
