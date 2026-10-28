"""Source-preserving CPU preprocessing in real PostgreSQL/private S3 fixtures."""

import io
from uuid import uuid4

import numpy as np
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from test_imaging_ingestion import imaging_db
from test_imaging_volumes import confirmed
from test_source_registry import registry_db, review

from canceros.imaging_preprocessing import PreprocessingConfig
from canceros.imaging_volumes import GeometryValidationInput, load_volume, validate_volume
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.preprocessing_runs import PreprocessInput, read_preprocessing, run_preprocessing
from canceros.source_registry import add_review
from canceros.storage import StoredObject

__all__ = ["imaging_db", "registry_db"]


def test_preprocessing_deterministic_private_derivative_and_source_unchanged(imaging_db):
    c, i, p, patient, _, storage, _ = imaging_db
    imported = confirmed(imaging_db)
    source = validate_volume(
        c, i, p, patient.patient_id, GeometryValidationInput(import_id=imported.id), storage
    )
    command = PreprocessInput(
        volume_artifact_id=source.volume_artifact_id,
        config=PreprocessingConfig(expected_sequence="t1", method="per_volume_zscore"),
    )
    report = run_preprocessing(c, i, p, patient.patient_id, command, storage)
    assert report.status == "processed" and report.publication == "draft"
    assert report.geometry == source.geometry and report.output_sha256 != report.input_sha256
    assert run_preprocessing(c, i, p, patient.patient_id, command, storage) == report
    assert read_preprocessing(c, i, p, patient.patient_id, report.id) == report
    original = load_volume(c, i, p, patient.patient_id, source.volume_artifact_id, storage)[1]
    np.testing.assert_array_equal(original, np.arange(24).reshape(3, 4, 2))
    stored = (
        c.execute(
            text("SELECT * FROM ops.artifacts WHERE id=:id"), {"id": report.output_artifact_id}
        )
        .mappings()
        .one()
    )
    normalized = np.load(
        io.BytesIO(
            storage.read(
                StoredObject(
                    p,
                    stored["object_key"],
                    stored["object_version"],
                    stored["sha256"],
                    stored["byte_size"],
                ),
                p,
            )
        ),
        allow_pickle=False,
    )
    expected_std = (
        575 / 12
    ) ** 0.5  # Independent population variance of consecutive integers 0..23.
    np.testing.assert_allclose(
        normalized, (np.arange(24).reshape(3, 4, 2) - 11.5) / expected_std, atol=1e-12
    )
    identity = run_preprocessing(
        c,
        i,
        p,
        patient.patient_id,
        command.model_copy(update={"config": PreprocessingConfig(expected_sequence="t1")}),
        storage,
    )
    # NPY layout metadata may change Fortran/C order while identity pixels stay exact.
    assert identity.processing is not None
    assert identity.processing.source_array_sha256 == identity.processing.output_array_sha256
    assert "object_key" not in report.model_dump_json()
    withdraw_resource(
        c,
        i,
        p,
        patient.patient_id,
        report.output_artifact_id,
        WithdrawalInput(reason_code="scientific_review"),
    )
    with pytest.raises(HTTPException):
        run_preprocessing(c, i, p, patient.patient_id, command, storage)


def test_missing_sequence_blocked_and_rights_rechecked_on_replay(imaging_db):
    c, i, p, patient, component, storage, _ = imaging_db
    imported = confirmed(imaging_db)
    source = validate_volume(
        c, i, p, patient.patient_id, GeometryValidationInput(import_id=imported.id), storage
    )
    command = PreprocessInput(
        volume_artifact_id=source.volume_artifact_id,
        config=PreprocessingConfig(expected_sequence="t2"),
    )
    report = run_preprocessing(c, i, p, patient.patient_id, command, storage)
    assert report.status == "blocked" and report.output_artifact_id is None
    assert report.geometry is None
    with pytest.raises(HTTPException) as denied:
        read_preprocessing(c, i, p, uuid4(), report.id)
    assert denied.value.status_code == 404
    add_review(c, i, p, component, review(action="derivative_creation", decision="denied"))
    with pytest.raises(HTTPException):
        run_preprocessing(c, i, p, patient.patient_id, command, storage)
    assert read_preprocessing(c, i, p, patient.patient_id, report.id) == report
