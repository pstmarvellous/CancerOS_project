"""Artificial imaging only; real PostgreSQL/private versioned S3 and HTTP identity."""

import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import nibabel as nib
import numpy as np
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_imaging_formats import dicom_bytes
from test_patient_linkage import keys, setup_mapping
from test_source_registry import example, registry_db, review

from canceros.api import create_app
from canceros.identity import Identity
from canceros.imaging_ingestion import (
    ImagingAssociation,
    ImagingPreviewInput,
    ImagingStageInput,
    confirm_import,
    preview_imaging,
    read_import,
    read_staged,
    stage_imaging,
    store_artifact,
)
from canceros.lineage import WithdrawalInput, withdraw_resource
from canceros.patient_linkage import LinkageInput, resolve_mapping
from canceros.settings import Settings
from canceros.source_registry import add_review, add_source
from canceros.storage import PrivateStorage

__all__ = ["registry_db"]


def http_session(data):
    """Actual SQL identity boundary shared by imaging adapter tests; no injected auth."""
    c, i, p, _, _, _, config = data
    c.execute(
        text(
            "INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:u,'admin') ON CONFLICT DO NOTHING"
        ),
        {"p": p, "u": i.user_id},
    )
    c.commit()
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        private.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    service = Settings(
        mode="test",
        identity_issuer="engineering",
        identity_public_key=public,
        database_url=c.engine.url.render_as_string(hide_password=False),
        linkage_active_key="k1",
        linkage_keys=config.linkage_keys,
    )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(i.user_id),
            "iss": service.identity_issuer,
            "aud": service.identity_audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=5),
        },
        private,
        algorithm="RS256",
    )
    return TestClient(create_app(service)), {"Authorization": "Bearer " + token}


@pytest.fixture
def imaging_db(registry_db):
    connection, identity, project, mapping_input = setup_mapping(registry_db)
    config = keys()
    patient = resolve_mapping(connection, identity, project, mapping_input, config)
    component = connection.execute(
        text("SELECT parent_version_id FROM source.registry_versions WHERE id=:id"),
        {"id": mapping_input.source_version_id},
    ).scalar_one()
    add_review(connection, identity, project, component, review(action="derivative_creation"))
    storage = PrivateStorage(Settings(mode="test"))
    return connection, identity, project, patient, component, storage, config


def nifti_bytes(shape=(3, 4, 2)):
    image = nib.Nifti1Image(
        np.arange(np.prod(shape), dtype=np.int16).reshape(shape), np.diag([2.0, 3.0, 4.0, 1.0])
    )
    image.header.set_xyzt_units("mm")
    image.header["descrip"] = b"ARTIFICIAL PRIVATE HEADER DO NOT EXPOSE"
    return image.to_bytes()


def stage(data, raw=None, format="nifti"):
    connection, identity, project, patient, component, storage, _ = data
    raw = nifti_bytes() if raw is None else raw
    digest = hashlib.sha256(raw).hexdigest()
    source = add_source(
        connection,
        identity,
        project,
        example(kind="artifact_source", parent_version_id=component, manifest_sha256=digest),
    )
    value = ImagingStageInput(
        source_version_id=source.id,
        mapping_id=patient.mapping_id,
        format=format,
        sha256=digest,
        content_base64=base64.b64encode(raw).decode(),
    )
    receipt = stage_imaging(connection, identity, project, patient.patient_id, value, storage)
    assert (
        stage_imaging(connection, identity, project, patient.patient_id, value, storage) == receipt
    )
    return receipt, value


def preview_command(patient, receipt, **changes):
    return ImagingPreviewInput(
        file_ids=[receipt.artifact_id],
        association=ImagingAssociation(
            mapping_id=patient.mapping_id,
            study_id=uuid4(),
            series_id=uuid4(),
            source_study_key="ARTIFICIAL-STUDY",
            source_series_key="ARTIFICIAL-SERIES",
            sequence="t1",
            acquisition_time_status="not_recorded",
            association_basis="administrator_manifest_attestation",
            evidence_sha256="e" * 64,
            **changes,
        ),
    )


def test_private_stage_preview_confirm_retry_and_immutable_report(imaging_db):
    c, i, p, patient, _, storage, config = imaging_db
    receipt, _ = stage(imaging_db)
    command = preview_command(patient, receipt)
    report = preview_imaging(c, i, p, patient.patient_id, command, storage, config)
    assert report.status == "awaiting_confirmation" and report.dimensions == [3, 4, 2]
    assert report.publication == "draft" and report.scientific_review == "pending"
    assert report.privacy_review == "required_before_sharing"
    assert preview_imaging(c, i, p, patient.patient_id, command, storage, config) == report
    rotated = keys("k2", {**config.linkage_keys, "k2": keys().linkage_keys["k1"]})
    assert preview_imaging(c, i, p, patient.patient_id, command, storage, rotated).id == report.id
    private_markers = [
        "ARTIFICIAL-STUDY",
        "ARTIFICIAL-SERIES",
        "PRIVATE HEADER",
        "object_key",
        "ciphertext",
    ]
    assert not any(marker in report.model_dump_json() for marker in private_markers)
    confirmed = confirm_import(c, i, p, patient.patient_id, report.id)
    assert confirmed.status == "staged_pending_geometry"
    assert confirm_import(c, i, p, patient.patient_id, report.id) == confirmed
    original = c.execute(
        text("SELECT report FROM imaging.imports WHERE id=:id"), {"id": report.id}
    ).scalar_one()
    assert original["status"] == "awaiting_confirmation"
    assert (
        read_staged(c, i, p, patient.patient_id, receipt.artifact_id, storage)[1] == nifti_bytes()
    )
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


def test_corrupt_archive_and_ambiguous_dce_inputs_quarantine(imaging_db):
    c, i, p, patient, _, storage, config = imaging_db
    for raw in (
        b"PK\x03\x04../../escape",
        b"not an imaging file",
        nifti_bytes()[:360],
        nifti_bytes((2, 2, 2, 3)),
    ):
        receipt, _ = stage(imaging_db, raw)
        report = preview_imaging(
            c, i, p, patient.patient_id, preview_command(patient, receipt), storage, config
        )
        assert report.status == "quarantined" and report.dimensions is None
        with pytest.raises(HTTPException) as error:
            confirm_import(c, i, p, patient.patient_id, report.id)
        assert error.value.status_code == 409
    receipt, _ = stage(imaging_db, nifti_bytes((2, 2, 2, 3)))
    command = preview_command(patient, receipt, fourth_axis="dce_phase")
    command = command.model_copy(
        update={"association": command.association.model_copy(update={"sequence": "dce"})}
    )
    report = preview_imaging(c, i, p, patient.patient_id, command, storage, config)
    assert report.dimensions == [2, 2, 2, 3]
    assert (
        c.execute(
            text("SELECT count(*) FROM clinical.observations WHERE patient_id=:u"),
            {"u": patient.patient_id},
        ).scalar_one()
        == 0
    )


def test_ownership_current_rights_and_conflicting_association(imaging_db):
    c, i, p, patient, component, storage, config = imaging_db
    receipt, _ = stage(imaging_db)
    command = preview_command(patient, receipt)
    report = preview_imaging(c, i, p, patient.patient_id, command, storage, config)
    with pytest.raises(HTTPException) as mismatch:
        preview_imaging(
            c,
            i,
            p,
            patient.patient_id,
            command.model_copy(
                update={
                    "association": command.association.model_copy(
                        update={"study_id": uuid4(), "series_id": uuid4()}
                    )
                }
            ),
            storage,
            config,
        )
    assert mismatch.value.status_code == 409
    for principal, patient_id, status in (
        (Identity(i.user_id, {p: "editor"}), patient.patient_id, 403),
        (i, uuid4(), 404),
        (Identity(i.user_id, {}), patient.patient_id, 404),
    ):
        with pytest.raises(HTTPException) as denied:
            preview_imaging(c, principal, p, patient_id, command, storage, config)
        assert denied.value.status_code == status
    add_review(c, i, p, component, review(action="derivative_creation", decision="denied"))
    with pytest.raises(HTTPException) as denied:
        confirm_import(c, i, p, patient.patient_id, report.id)
    assert denied.value.status_code == 409
    # Historical report remains readable, but confirmation/new use is blocked.
    assert read_import(c, i, p, patient.patient_id, report.id).status == "awaiting_confirmation"
    add_review(c, i, p, component, review(action="derivative_creation"))
    withdraw_resource(
        c,
        i,
        p,
        patient.patient_id,
        receipt.artifact_id,
        WithdrawalInput(reason_code="privacy_review"),
    )
    with pytest.raises(HTTPException):
        preview_imaging(c, i, p, patient.patient_id, command, storage, config)


def test_dicom_private_patient_and_study_binding_physical_order(imaging_db):
    c, i, p, patient, _, storage, config = imaging_db
    files = [
        stage(imaging_db, dicom_bytes(z, PatientID="ARTIFICIAL-SOURCE-KEY-NO-PATIENT"), "dicom")[
            0
        ].artifact_id
        for z in (2, 0, 1)
    ]
    association = ImagingAssociation(
        mapping_id=patient.mapping_id,
        study_id=uuid4(),
        series_id=uuid4(),
        source_study_key="1.2.826.0.1.1",
        source_series_key="1.2.826.0.1.2",
        sequence="t1",
        acquisition_time_status="source_private",
        association_basis="administrator_manifest_attestation",
        evidence_sha256="e" * 64,
    )
    command = ImagingPreviewInput(file_ids=files, association=association)
    report = preview_imaging(c, i, p, patient.patient_id, command, storage, config)
    assert report.status == "awaiting_confirmation" and report.dimensions == [3, 2, 3]
    assert (
        preview_imaging(
            c,
            i,
            p,
            patient.patient_id,
            command.model_copy(update={"file_ids": list(reversed(files))}),
            storage,
            config,
        ).id
        == report.id
    )
    assert "1.2.826" not in report.model_dump_json()
    bad_files = [stage(imaging_db, dicom_bytes(z), "dicom")[0].artifact_id for z in (0, 1)]
    command = ImagingPreviewInput(
        file_ids=bad_files,
        association=association.model_copy(
            update={
                "study_id": uuid4(),
                "series_id": uuid4(),
                "source_study_key": SecretStr("wrong-study"),
            }
        ),
    )
    # An explicit source key mismatch never becomes a confirmable association.
    assert (
        preview_imaging(c, i, p, patient.patient_id, command, storage, config).status
        == "quarantined"
    )


def test_dicom_wrong_patient_is_quarantined_before_confirmation(imaging_db):
    c, i, p, patient, _, storage, config = imaging_db
    files = [stage(imaging_db, dicom_bytes(z), "dicom")[0].artifact_id for z in (0, 1)]
    command = ImagingPreviewInput(
        file_ids=files,
        association=ImagingAssociation(
            mapping_id=patient.mapping_id,
            study_id=uuid4(),
            series_id=uuid4(),
            source_study_key="1.2.826.0.1.1",
            source_series_key="1.2.826.0.1.2",
            sequence="t1",
            acquisition_time_status="source_private",
            association_basis="administrator_manifest_attestation",
            evidence_sha256="e" * 64,
        ),
    )
    report = preview_imaging(c, i, p, patient.patient_id, command, storage, config)
    assert report.status == "quarantined"
    assert "ARTIFICIAL-PARSER-ONLY" not in report.model_dump_json()


def test_http_imaging_does_not_echo_header_source_keys_or_bytes(imaging_db, caplog):
    c, i, p, patient, _, storage, config = imaging_db
    receipt, _ = stage(imaging_db)
    c.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:u,'admin')"),
        {"p": p, "u": i.user_id},
    )
    c.commit()
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = (
        private.public_key()
        .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        .decode()
    )
    service = Settings(
        mode="test",
        identity_issuer="engineering",
        identity_public_key=public,
        database_url=c.engine.url.render_as_string(hide_password=False),
        linkage_active_key="k1",
        linkage_keys=config.linkage_keys,
    )
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(i.user_id),
            "iss": service.identity_issuer,
            "aud": service.identity_audience,
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=5),
        },
        private,
        algorithm="RS256",
    )
    headers = {"Authorization": "Bearer " + token}
    command = preview_command(patient, receipt)
    payload = command.model_dump(mode="json")
    payload["association"].update(
        source_study_key="ARTIFICIAL-STUDY", source_series_key="ARTIFICIAL-SERIES"
    )
    path = f"/api/v1/projects/{p}/patients/{patient.patient_id}/imaging-import-previews"
    with TestClient(create_app(service)) as client:
        assert client.post(path, json=payload).status_code == 401
        result = client.post(path, json=payload, headers=headers)
        assert result.status_code == 201, result.text
        assert client.get(result.headers["Location"], headers=headers).json() == result.json()
        assert (
            client.post(result.headers["Location"] + "/confirmations", headers=headers).json()[
                "status"
            ]
            == "staged_pending_geometry"
        )
        geometry = client.post(
            f"/api/v1/projects/{p}/patients/{patient.patient_id}/geometry-validations",
            json={"import_id": result.json()["id"]},
            headers=headers,
        )
        assert geometry.status_code == 201, geometry.text
        assert geometry.json()["geometry"]["voxel_volume_mm3"] == "24"
        assert client.get(geometry.headers["Location"], headers=headers).json() == geometry.json()
        processed = client.post(
            f"/api/v1/projects/{p}/patients/{patient.patient_id}/preprocessing-runs",
            json={
                "volume_artifact_id": geometry.json()["volume_artifact_id"],
                "config": {"expected_sequence": "t1", "method": "identity"},
            },
            headers=headers,
        )
        assert processed.status_code == 201, processed.text
        assert processed.json()["status"] == "processed"
        assert client.get(processed.headers["Location"], headers=headers).json() == processed.json()
        assert "ARTIFICIAL-STUDY" not in result.text + caplog.text
        assert "PRIVATE HEADER" not in result.text + caplog.text


def test_database_patient_constraints_and_cross_patient_study_race(imaging_db):
    c, i, p, first, component, storage, config = imaging_db
    source_id = c.execute(
        text("SELECT source_version_id FROM source.patient_mappings WHERE id=:id"),
        {"id": first.mapping_id},
    ).scalar_one()
    second = resolve_mapping(
        c,
        i,
        p,
        LinkageInput(source_version_id=source_id, source_patient_key="ARTIFICIAL-SECOND-PATIENT"),
        config,
    )
    first_file, _ = stage(imaging_db)
    second_data = (c, i, p, second, component, storage, config)
    second_file, _ = stage(second_data)
    extra_artifact, _ = store_artifact(c, p, first.patient_id, nifti_bytes(), storage)
    with pytest.raises(DBAPIError) as violation, c.begin_nested():
        c.execute(
            text(
                "INSERT INTO imaging.staged_files(id,project_id,patient_id,mapping_id,source_version_id,format,input_hash) VALUES(:id,:p,:u,:m,:s,'dicom',:hash)"
            ),
            {
                "id": extra_artifact,
                "p": p,
                "u": second.patient_id,
                "m": first.mapping_id,
                "s": source_id,
                "hash": "d" * 64,
            },
        )
    assert violation.value.orig.sqlstate == "23503"
    study_id = uuid4()
    commands = [
        (first, preview_command(first, first_file)),
        (second, preview_command(second, second_file)),
    ]
    commands = [
        (
            patient,
            command.model_copy(
                update={
                    "association": command.association.model_copy(update={"study_id": study_id})
                }
            ),
        )
        for patient, command in commands
    ]
    c.commit()

    def run(item):
        patient, command = item
        try:
            with c.engine.begin() as connection:
                return preview_imaging(
                    connection, i, p, patient.patient_id, command, storage, config
                ).status
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, commands))
    assert sorted(results, key=str) == [409, "awaiting_confirmation"]
    assert (
        c.execute(
            text("SELECT count(*) FROM imaging.studies WHERE project_id=:p AND study_id=:study"),
            {"p": p, "study": study_id},
        ).scalar_one()
        == 1
    )
