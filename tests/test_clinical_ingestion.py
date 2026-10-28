"""Real SQL/private S3 integration with wholly synthetic clinical source manifests."""

import base64
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_clinical_contracts import clinical_item
from test_patient_linkage import keys, setup_mapping
from test_source_registry import example, registry_db, review

from canceros.clinical_ingestion import (
    BatchCommand,
    ClinicalSourceUpload,
    RetractionInput,
    accept_batch,
    read_record,
    retract_record,
    upload_source,
    validate_batch,
)
from canceros.identity import Identity
from canceros.patient_linkage import resolve_mapping
from canceros.persistence import load_revision
from canceros.settings import Settings
from canceros.source_registry import add_review, add_source
from canceros.storage import PrivateStorage

__all__ = ["registry_db"]


@pytest.fixture
def clinical_db(registry_db):
    connection, identity, project, mapping_input = setup_mapping(registry_db)
    patient = resolve_mapping(connection, identity, project, mapping_input, keys())
    origin = uuid4()
    connection.execute(
        text(
            "INSERT INTO source.timeline_origins(id,project_id,patient_id,reference_meaning,time_domain) VALUES(:id,:p,:u,'Synthetic fixture relative zero','simulation')"
        ),
        {"id": origin, "p": project, "u": patient.patient_id},
    )
    component = connection.execute(
        text("SELECT parent_version_id FROM source.registry_versions WHERE id=:id"),
        {"id": mapping_input.source_version_id},
    ).scalar_one()
    add_review(connection, identity, project, component, review(action="derivative_creation"))
    storage = PrivateStorage(Settings(mode="test"))
    return connection, identity, project, patient, origin, component, storage


def row(origin, **changes):
    value = clinical_item(
        time={
            "reference": {
                "basis": "relative_day",
                "value": "0",
                "time_domain": "simulation",
                "timeline_origin_id": str(origin),
            },
            "precision": "relative_day",
        },
        **changes,
    )
    value.pop("source_locator_id")
    return value


def stage(data, rows):
    connection, identity, project, patient, _, component, storage = data
    raw = json.dumps(
        {
            "schema_version": "clinical-source/1",
            "fixture_origin": "SYNTHETIC_ENGINEERING_FIXTURE",
            "records": rows,
        },
        separators=(",", ":"),
    ).encode()
    digest = hashlib.sha256(raw).hexdigest()
    source = add_source(
        connection,
        identity,
        project,
        example(kind="artifact_source", parent_version_id=component, manifest_sha256=digest),
    )
    value = ClinicalSourceUpload(
        source_version_id=source.id,
        mapping_id=patient.mapping_id,
        sha256=digest,
        content_base64=base64.b64encode(raw).decode(),
    )
    result = upload_source(connection, identity, project, patient.patient_id, value, storage)
    assert (
        upload_source(connection, identity, project, patient.patient_id, value, storage) == result
    )
    return result


def test_validate_accept_retry_and_original_source_values(clinical_db):
    connection, identity, project, patient, origin, _, storage = clinical_db
    receipt = stage(clinical_db, [row(origin)])
    command = BatchCommand(source_artifact_id=receipt.artifact_id, expected_revision=1)
    report, _ = validate_batch(connection, identity, project, patient.patient_id, command, storage)
    assert report.status == "valid" and report.accepted_count == 0
    assert load_revision(connection, project, patient.patient_id, 1)["members"] == []
    accepted = accept_batch(
        connection, identity, project, patient.patient_id, command, "delivery-1", storage
    )
    assert accepted.status == "accepted" and accepted.accepted_count == 1
    assert accepted.publication == "draft" and accepted.result_revision == 2
    assert (
        accept_batch(
            connection, identity, project, patient.patient_id, command, "delivery-1", storage
        )
        == accepted
    )
    with pytest.raises(HTTPException) as collision:
        accept_batch(
            connection,
            identity,
            project,
            patient.patient_id,
            command.model_copy(update={"expected_revision": 2}),
            "delivery-1",
            storage,
        )
    assert collision.value.status_code == 409
    record = read_record(connection, identity, project, patient.patient_id, accepted.record_ids[0])
    assert record.item.original_value == "12.5" and record.item.original_unit == "g/dL"
    assert record.origin == "SYNTHETIC_GENERATED"
    assert (
        connection.execute(
            text("SELECT count(*) FROM clinical.numeric_results WHERE observation_id=:id"),
            {"id": record.id},
        ).scalar_one()
        == 1
    )
    connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert (
        connection.execute(
            text("SELECT count(*) FROM ops.domain_outbox WHERE patient_id=:u"),
            {"u": patient.patient_id},
        ).scalar_one()
        == 1
    )


def test_correction_retraction_preserve_old_revision_and_append_only(clinical_db):
    connection, identity, project, patient, origin, _, storage = clinical_db
    first = stage(clinical_db, [row(origin)])
    accepted = accept_batch(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(source_artifact_id=first.artifact_id, expected_revision=1),
        "original",
        storage,
    )
    second = stage(
        clinical_db,
        [
            row(
                origin,
                original_value="13.5",
                result={"form": "exact", "quantity": {"value": "13.5", "unit": "g/dL"}},
            )
        ],
    )
    corrected = accept_batch(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(
            source_artifact_id=second.artifact_id,
            expected_revision=2,
            corrects_record_id=accepted.record_ids[0],
        ),
        "correction",
        storage,
    )
    assert load_revision(connection, project, patient.patient_id, 2)["members"] == [
        str(accepted.record_ids[0])
    ]
    assert load_revision(connection, project, patient.patient_id, 3)["members"] == [
        str(corrected.record_ids[0])
    ]
    assert (
        read_record(
            connection, identity, project, patient.patient_id, accepted.record_ids[0]
        ).item.original_value
        == "12.5"
    )
    result = retract_record(
        connection,
        identity,
        project,
        patient.patient_id,
        corrected.record_ids[0],
        RetractionInput(expected_revision=3, reason_code="entered_in_error"),
    )
    assert result.revision == 4
    assert load_revision(connection, project, patient.patient_id, 4)["members"] == []
    assert load_revision(connection, project, patient.patient_id, 3)["members"] == [
        str(corrected.record_ids[0])
    ]
    with pytest.raises(DBAPIError), connection.begin_nested():
        connection.execute(
            text("DELETE FROM clinical.observations WHERE id=:id"), {"id": accepted.record_ids[0]}
        )


def test_mixed_validity_quarantines_whole_batch_without_revision(clinical_db):
    connection, identity, project, patient, origin, _, storage = clinical_db
    receipt = stage(
        clinical_db,
        [
            row(origin),
            row(
                origin,
                client_record_key="bad-row",
                result={"form": "exact", "quantity": {"value": "1", "unit": "kg"}},
            ),
        ],
    )
    command = BatchCommand(source_artifact_id=receipt.artifact_id, expected_revision=1)
    result = accept_batch(
        connection, identity, project, patient.patient_id, command, "mixed", storage
    )
    assert result.status == "quarantined" and result.accepted_count == 0
    assert result.rejected_count == 1 and result.quarantined_count == 2
    assert result.issues[0].path.startswith("/records/1/")
    assert load_revision(connection, project, patient.patient_id, 1)["members"] == []
    assert (
        connection.execute(
            text("SELECT count(*) FROM clinical.observations WHERE patient_id=:u"),
            {"u": patient.patient_id},
        ).scalar_one()
        == 0
    )


def test_late_failure_rolls_back_partial_batch(clinical_db):
    connection, identity, project, patient, origin, _, storage = clinical_db
    receipt = stage(clinical_db, [row(origin)])
    accept_batch(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(source_artifact_id=receipt.artifact_id, expected_revision=1),
        "initial",
        storage,
    )
    invalid = stage(clinical_db, [row(origin, client_record_key="would-be-new"), row(origin)])
    with pytest.raises(HTTPException), connection.begin_nested():
        accept_batch(
            connection,
            identity,
            project,
            patient.patient_id,
            BatchCommand(source_artifact_id=invalid.artifact_id, expected_revision=2),
            "rollback",
            storage,
        )
    assert (
        connection.execute(
            text("SELECT count(*) FROM clinical.observations WHERE patient_id=:u"),
            {"u": patient.patient_id},
        ).scalar_one()
        == 1
    )
    assert (
        connection.execute(
            text("SELECT data_revision FROM source.research_patients WHERE id=:u"),
            {"u": patient.patient_id},
        ).scalar_one()
        == 2
    )


def test_patient_grants_and_current_rights_apply_even_to_replay(clinical_db):
    connection, identity, project, patient, origin, component, storage = clinical_db
    receipt = stage(clinical_db, [row(origin)])
    command = BatchCommand(source_artifact_id=receipt.artifact_id, expected_revision=1)
    accept_batch(connection, identity, project, patient.patient_id, command, "original", storage)
    with pytest.raises(HTTPException) as denied:
        validate_batch(
            connection,
            Identity(identity.user_id, {project: "editor"}),
            project,
            patient.patient_id,
            command,
            storage,
        )
    assert denied.value.status_code == 404
    with pytest.raises(HTTPException):
        validate_batch(connection, identity, project, uuid4(), command, storage)
    add_review(connection, identity, project, component, review(decision="denied"))
    with pytest.raises(HTTPException):
        accept_batch(
            connection, identity, project, patient.patient_id, command, "original", storage
        )


def test_concurrent_corrections_only_one_revision_wins(clinical_db):
    connection, identity, project, patient, origin, _, storage = clinical_db
    first = stage(clinical_db, [row(origin)])
    accepted = accept_batch(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(source_artifact_id=first.artifact_id, expected_revision=1),
        "original",
        storage,
    )
    a = stage(
        clinical_db,
        [
            row(
                origin,
                original_value="13",
                result={"form": "exact", "quantity": {"value": "13", "unit": "g/dL"}},
            )
        ],
    )
    b = stage(
        clinical_db,
        [
            row(
                origin,
                original_value="14",
                result={"form": "exact", "quantity": {"value": "14", "unit": "g/dL"}},
            )
        ],
    )
    connection.commit()

    def perform(pair):
        artifact, key = pair
        try:
            with connection.engine.begin() as worker:
                return accept_batch(
                    worker,
                    identity,
                    project,
                    patient.patient_id,
                    BatchCommand(
                        source_artifact_id=artifact.artifact_id,
                        expected_revision=2,
                        corrects_record_id=accepted.record_ids[0],
                    ),
                    key,
                    storage,
                ).status
        except HTTPException as error:
            return error.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(perform, [(a, "correction-a"), (b, "correction-b")]))
    assert sorted(results, key=str) == [409, "accepted"]
    assert len(load_revision(connection, project, patient.patient_id, 3)["members"]) == 1
