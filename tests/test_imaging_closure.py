"""COS-067 closure: study/acquisition discovery, segmentation discovery, grants."""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from test_alignment_runs import aligned
from test_annotation_import import command_for
from test_imaging_ingestion import http_session, imaging_db, nifti_bytes, preview_command, stage
from test_imaging_storage import registry_db as _registry_db  # noqa: F401  (fixture chain)
from test_patient_linkage import keys
from test_source_registry import registry_db

from canceros.annotation_import import import_annotations
from canceros.imaging_discovery import (
    discovery_segmentations,
    list_imports,
    list_studies,
    read_acquisition,
)
from canceros.imaging_storage import AssetGrantInput, grant_asset

__all__ = ["imaging_db", "registry_db"]


def previewed(imaging_data):
    c, i, p, patient, _, storage, config = imaging_data
    receipt, _staged = stage(imaging_data, nifti_bytes())
    from canceros.imaging_ingestion import preview_imaging
    from canceros.settings import Settings
    from canceros.storage import PrivateStorage

    report = preview_imaging(
        c,
        i,
        p,
        patient.patient_id,
        preview_command(patient, receipt),
        PrivateStorage(Settings(mode="test")),
        config,
    )
    return c, i, p, patient, report


def test_study_and_acquisition_discovery_are_owned_and_stable(imaging_db):
    c, i, p, patient, report = previewed(imaging_db)
    studies = list_studies(c, i, p, patient.patient_id)
    assert len(studies.items) == 1
    assert studies.items[0].import_count >= 1 and studies.items[0].series_count >= 1
    acquired = read_acquisition(c, i, p, patient.patient_id, report.id)
    assert acquired.import_id == report.id
    assert acquired.file_count == len(report.file_ids)
    assert acquired.frame_shape == list(report.dimensions or [])
    assert acquired.study_id == report.study_id
    again = list_studies(c, i, p, patient.patient_id)
    assert [s.study_id for s in again.items] == [s.study_id for s in studies.items]
    with pytest.raises(HTTPException) as unknown:
        read_acquisition(c, i, p, patient.patient_id, uuid4())
    assert unknown.value.status_code == 404
    with pytest.raises(HTTPException) as stranger:
        list_studies(c, i, p, uuid4())
    assert stranger.value.status_code == 404


def test_segmentation_discovery_requires_qc_visible_state(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    _, alignment = aligned(imaging_db)
    batch = import_annotations(c, i, p, patient.patient_id, command_for(alignment), storage)
    assert batch.segmentation_ids
    found = discovery_segmentations(c, i, p, patient.patient_id)
    assert {f.segmentation_id for f in found} == set(batch.segmentation_ids)
    assert all(f.mask_type for f in found)
    assert all(f.qc_status in ("pending", "pass", "fail") for f in found)
    with pytest.raises(HTTPException) as stranger:
        discovery_segmentations(c, i, p, uuid4())
    assert stranger.value.status_code == 404


def test_grant_expiry_and_withdrawal_warning_are_honest(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    receipt, _ = stage(imaging_db)
    grant = grant_asset(
        c, i, p, patient.patient_id, receipt.artifact_id, AssetGrantInput(), storage
    )
    assert grant.expires_at is not None
    assert "until expiry" in grant.warning
    assert grant.artifact_id == receipt.artifact_id
    with pytest.raises(HTTPException):
        grant_asset(c, i, p, uuid4(), receipt.artifact_id, AssetGrantInput(), storage)


def test_closure_http_study_acquisition_and_discovery_paths(imaging_db):
    c, i, p, patient, report = previewed(imaging_db)
    client, headers = http_session((c, i, p, patient, None, None, keys()))
    root = f"/api/v1/projects/{p}/patients/{patient.patient_id}"
    with client:
        assert client.get(root + "/studies").status_code == 401
        studies = client.get(root + "/studies", headers=headers)
        assert studies.status_code == 200, studies.text
        assert studies.json()["items"]
        acquired = client.get(root + f"/acquisitions/{report.id}", headers=headers)
        assert acquired.status_code == 200, acquired.text
        assert acquired.json()["frame_shape"] == list(report.dimensions or [])
        assert acquired.headers["cache-control"] == "private, no-store"
        assert "signed" not in acquired.text and "credential" not in acquired.text.lower()
        discovered = client.get(root + "/segmentation-discoveries", headers=headers)
        assert discovered.status_code in (200, 404)
        listed = client.get(root + "/imaging-imports", headers=headers)
        assert listed.status_code == 200, listed.text
        assert [item["import_id"] for item in listed.json()["items"]] == [str(report.id)]
        assert listed.json()["items"][0]["study_id"] == str(report.study_id)
        assert "credential" not in listed.text.lower()
        assert client.get(root + "/imaging-imports").status_code == 401
        with pytest.raises(HTTPException) as stranger:
            list_imports(c, i, p, uuid4())
        assert stranger.value.status_code == 404
        missing = client.get(root + f"/acquisitions/{uuid4()}", headers=headers)
        assert missing.status_code in (404, 409)
        denied = client.get(root + "/studies", headers={"Authorization": "Bearer invalid"})
        assert denied.status_code in (401, 403, 404, 422)


def test_lesion_geometry_resolves_actual_reports_with_scope_and_withdrawal(imaging_db):
    from test_mesh_quality_runs import mesh_source

    from canceros.imaging_discovery import lesion_geometry
    from canceros.lesion_tracking import LesionInput, create_lesion
    from canceros.lineage import WithdrawalInput, withdraw_resource
    from canceros.mesh_quality_runs import MeshQCInput, create_mesh_qc

    c, i, p, patient, _, storage, _ = imaging_db
    measured, mesh = mesh_source(imaging_db)
    qc = create_mesh_qc(
        c, i, p, patient.patient_id, MeshQCInput(mesh_run_id=mesh.id), storage, "lookup-qc"
    )
    lesion = create_lesion(
        c,
        i,
        p,
        patient.patient_id,
        LesionInput(
            baseline_segmentation_id=measured.selections[0].segmentation_id,
            evidence_sha256="a" * 64,
            expected_revision=1,
        ),
        storage,
        "lookup-lesion",
    )
    assert qc.id not in (lesion.id, lesion.baseline_segmentation_id)
    assert lesion_geometry(c, i, p, patient.patient_id, lesion.id).id == qc.id
    client, headers = http_session(imaging_db)
    path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/lesions/{lesion.id}/geometry"
    with client:
        assert client.get(path).status_code == 401
        result = client.get(path, headers=headers)
        assert result.status_code == 200, result.text
        assert result.json()["id"] == str(qc.id)
        assert (
            client.get(
                path.replace(str(patient.patient_id), str(uuid4())), headers=headers
            ).status_code
            == 404
        )
    withdraw_resource(
        c, i, p, patient.patient_id, qc.id, WithdrawalInput(reason_code="scientific_review")
    )
    with pytest.raises(HTTPException) as withdrawn:
        lesion_geometry(c, i, p, patient.patient_id, lesion.id)
    assert withdrawn.value.status_code == 409
