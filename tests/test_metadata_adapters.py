import base64
import csv
import hashlib
import io
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from test_clinical_ingestion import clinical_db
from test_source_registry import example, registry_db, review

from canceros.clinical_ingestion import BatchCommand, accept_batch
from canceros.identity import Identity
from canceros.metadata_adapters import COLUMNS, AdapterInput, parse_fixture_csv, run_adapter
from canceros.source_registry import SourceAction, add_review, add_source

__all__ = ["clinical_db", "registry_db"]


def csv_bytes(rows=None, headers=None):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers or COLUMNS)
    writer.writerows(
        rows
        or [
            ["fixture-hgb", "laboratory", "hemoglobin", "0", "125", "g/L", "", "", "Artificial HGB"]
        ]
    )
    return stream.getvalue().encode()


def test_deterministic_fixture_dictionary_and_missingness():
    raw = csv_bytes()
    origin = uuid4()
    first = parse_fixture_csv(raw, origin)
    assert first == parse_fixture_csv(raw, origin)
    assert first[1] == 1 and first[3] == []
    assert first[2][0]["original_value"] == "125"
    missing = csv_bytes(
        [["missing-row", "laboratory", "wbc", "", "", "", "", "not_collected", "Artificial WBC"]]
    )
    output = parse_fixture_csv(missing, origin)
    assert output[2][0]["time"]["reference"]["basis"] == "unknown"
    assert output[2][0]["result"]["form"] == "missing"


@pytest.mark.parametrize(
    "raw",
    [
        csv_bytes(headers=["unsupported-header"]),
        b"\xff\xfe",
        csv_bytes([["short"]]),
        csv_bytes(
            [["duplicate", "laboratory", "wbc", "0", "1", "10[9]/L", "", "", "Artificial"]] * 2
        ),
        csv_bytes([["bad", "laboratory", "wbc", "0", "1", "kg", "", "", "Artificial"]]),
    ],
)
def test_corrupt_schema_rows_and_ambiguous_record_identity_quarantine(raw):
    assert parse_fixture_csv(raw, uuid4())[3]


def test_adapter_private_source_parent_repeat_and_clinical_acceptance(clinical_db):
    connection, identity, project, patient, origin, component, storage = clinical_db
    raw = csv_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    source = add_source(
        connection,
        identity,
        project,
        example(kind="artifact_source", parent_version_id=component, manifest_sha256=digest),
    )
    add_review(connection, identity, project, component, review(action=SourceAction.DERIVATIVE))
    value = AdapterInput(
        adapter_version="engineering-clinical-csv/1",
        source_version_id=source.id,
        mapping_id=patient.mapping_id,
        timeline_origin_id=origin,
        sha256=digest,
        content_base64=base64.b64encode(raw).decode(),
    )
    result = run_adapter(connection, identity, project, patient.patient_id, value, storage)
    assert result.status == "staged" and result.output_artifact_id
    rebuilt = parse_fixture_csv(raw, origin)[0]
    assert hashlib.sha256(rebuilt).hexdigest() == result.output_sha256
    assert run_adapter(connection, identity, project, patient.patient_id, value, storage) == result
    row = connection.execute(
        text(
            "SELECT source_version_id,input_artifact_id,output_artifact_id FROM source.adapter_runs WHERE id=:id"
        ),
        {"id": result.id},
    ).one()
    assert row.source_version_id == source.id and row.input_artifact_id == result.input_artifact_id
    accepted = accept_batch(
        connection,
        identity,
        project,
        patient.patient_id,
        BatchCommand(source_artifact_id=result.output_artifact_id, expected_revision=1),
        "adapter-accept",
        storage,
    )
    assert accepted.accepted_count == 1
    with pytest.raises(HTTPException):
        run_adapter(
            connection,
            Identity(identity.user_id, {project: "editor"}),
            project,
            patient.patient_id,
            value,
            storage,
        )
    with pytest.raises(HTTPException):
        run_adapter(connection, identity, project, uuid4(), value, storage)


def test_derivative_permission_required_and_invalid_rows_retained_in_private_quarantine(
    clinical_db,
):
    connection, identity, project, patient, origin, component, storage = clinical_db
    raw = csv_bytes(headers=["wrong-version"])
    digest = hashlib.sha256(raw).hexdigest()
    source = add_source(
        connection,
        identity,
        project,
        example(kind="artifact_source", parent_version_id=component, manifest_sha256=digest),
    )
    value = AdapterInput(
        adapter_version="engineering-clinical-csv/1",
        source_version_id=source.id,
        mapping_id=patient.mapping_id,
        timeline_origin_id=origin,
        sha256=digest,
        content_base64=base64.b64encode(raw).decode(),
    )
    add_review(
        connection,
        identity,
        project,
        component,
        review(action=SourceAction.DERIVATIVE, decision="unknown"),
    )
    with pytest.raises(HTTPException):
        run_adapter(connection, identity, project, patient.patient_id, value, storage)
    add_review(connection, identity, project, component, review(action=SourceAction.DERIVATIVE))
    report = run_adapter(connection, identity, project, patient.patient_id, value, storage)
    assert report.status == "quarantined" and report.output_artifact_id is None
    assert report.input_artifact_id and report.issues
