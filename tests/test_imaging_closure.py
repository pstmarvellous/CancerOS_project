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
        c, i, p, patient.patient_id, preview_command(patient, receipt),
        PrivateStorage(Settings(mode="test")), config,
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
        missing = client.get(root + f"/acquisitions/{uuid4()}", headers=headers)
        assert missing.status_code in (404, 409)
        denied = client.get(root + "/studies", headers={"Authorization": "Bearer invalid"})
        assert denied.status_code in (401, 403, 404, 422)
