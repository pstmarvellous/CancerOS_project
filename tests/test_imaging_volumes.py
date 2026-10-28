"""Canonical image persistence; artificial cuboid coordinates independently calculated."""

from uuid import uuid4

import numpy as np
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from test_imaging_ingestion import imaging_db, nifti_bytes, preview_command, stage
from test_source_registry import registry_db, review

from canceros.identity import Identity
from canceros.imaging_ingestion import confirm_import, preview_imaging
from canceros.imaging_volumes import (
    GeometryValidationInput,
    load_volume,
    read_geometry,
    validate_volume,
)
from canceros.source_registry import add_review

__all__ = ["imaging_db", "registry_db"]


def confirmed(data):
    c, i, p, patient, _, storage, config = data
    receipt, _ = stage(data)
    preview = preview_imaging(
        c, i, p, patient.patient_id, preview_command(patient, receipt), storage, config
    )
    confirm_import(c, i, p, patient.patient_id, preview.id)
    return preview


def test_canonical_private_array_exact_source_and_immutable_report(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    preview = confirmed(imaging_db)
    value = GeometryValidationInput(import_id=preview.id)
    report = validate_volume(c, i, p, patient.patient_id, value, storage)
    assert report.status == "valid" and report.geometry is not None
    assert report.geometry.voxel_volume_mm3 == "24"
    assert report.geometry.spacing_mm == ("2", "3", "4")
    assert report.geometry.shape_xyz == (3, 4, 2)
    assert report.geometry.coordinate_frame == "RAS"
    assert report.publication == "draft" and report.longitudinal_alignment == "not_established"
    assert validate_volume(c, i, p, patient.patient_id, value, storage) == report
    assert read_geometry(c, i, p, patient.patient_id, report.id) == report
    loaded, array = load_volume(c, i, p, patient.patient_id, report.volume_artifact_id, storage)
    assert loaded == report
    np.testing.assert_array_equal(array, np.arange(24).reshape(3, 4, 2))
    assert not array.flags.writeable
    source = c.execute(
        text(
            "SELECT a.object_key,a.object_version,a.sha256,a.byte_size FROM ops.artifacts a WHERE id=:id"
        ),
        {"id": preview.file_ids[0]},
    ).one()
    from canceros.storage import StoredObject

    assert (
        storage.read(
            StoredObject(
                p, source.object_key, source.object_version, source.sha256, source.byte_size
            ),
            p,
        )
        == nifti_bytes()
    )
    validation = c.execute(
        text("SELECT status,rule_version FROM source.technical_validations WHERE resource_id=:id"),
        {"id": report.volume_artifact_id},
    ).one()
    assert validation.status == "pass" and validation.rule_version == "geometry/1"
    assert "PRIVATE HEADER" not in report.model_dump_json()
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_geometry_requires_confirmation_patient_access_and_current_rights(imaging_db):
    c, i, p, patient, component, storage, config = imaging_db
    receipt, _ = stage(imaging_db)
    preview = preview_imaging(
        c, i, p, patient.patient_id, preview_command(patient, receipt), storage, config
    )
    value = GeometryValidationInput(import_id=preview.id)
    with pytest.raises(HTTPException) as error:
        validate_volume(c, i, p, patient.patient_id, value, storage)
    assert error.value.status_code == 409
    confirm_import(c, i, p, patient.patient_id, preview.id)
    report = validate_volume(c, i, p, patient.patient_id, value, storage)
    for principal, patient_id in (
        (Identity(i.user_id, {p: "editor"}), patient.patient_id),
        (i, uuid4()),
    ):
        with pytest.raises(HTTPException) as error:
            read_geometry(c, principal, p, patient_id, report.id)
        assert error.value.status_code == 404
    add_review(c, i, p, component, review(decision="denied"))
    with pytest.raises(HTTPException) as error:
        load_volume(c, i, p, patient.patient_id, report.volume_artifact_id, storage)
    assert error.value.status_code == 409
    with pytest.raises(HTTPException):
        validate_volume(c, i, p, patient.patient_id, value, storage)
    assert read_geometry(c, i, p, patient.patient_id, report.id) == report
