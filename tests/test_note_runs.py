"""Private S3 and disposable SQL tests with wholly artificial note content."""

import hashlib
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from test_clinical_ingestion import clinical_db
from test_imaging_ingestion import http_session
from test_patient_linkage import keys
from test_source_registry import example, registry_db, review

from canceros.clinical_contracts import ClinicalTime
from canceros.identity import Identity
from canceros.lineage import WithdrawalInput, register_root, withdraw_resource
from canceros.note_extraction import note_text_hash
from canceros.note_runs import (
    NoteExtractionCommand,
    NoteRegistration,
    extract_document,
    read_extraction,
    read_note,
    read_protected_span,
    register_note,
)
from canceros.persistence import load_revision
from canceros.source_registry import add_review, add_source

__all__ = ["clinical_db", "registry_db"]


def stage_note(data, source_text="Patient reports pain yesterday.", *, kind="note_source_artifact"):
    c, i, p, patient, _, component, storage = data
    raw = source_text.encode("utf-8") if isinstance(source_text, str) else source_text
    digest = hashlib.sha256(raw).hexdigest()
    source = add_source(
        c,
        i,
        p,
        example(kind="artifact_source", parent_version_id=component, manifest_sha256=digest),
    )
    stored = storage.write_verified(p, raw, cleanup_scope="engineering_fixture")
    identifier = uuid4()
    c.execute(
        text(
            "INSERT INTO ops.artifacts(id,project_id,patient_id,object_key,object_version,"
            "byte_size,sha256,provenance,availability) VALUES(:id,:p,:u,:key,:version,"
            ":size,:hash,'SYNTHETIC_GENERATED','verified')"
        ),
        {
            "id": identifier,
            "p": p,
            "u": patient.patient_id,
            "key": stored.key,
            "version": stored.version,
            "size": stored.byte_size,
            "hash": digest,
        },
    )
    register_root(c, i, p, patient.patient_id, identifier, kind, digest, source.id)
    return identifier


def note_anchor(origin):
    return ClinicalTime.model_validate(
        {
            "reference": {
                "basis": "relative_day",
                "value": "10",
                "time_domain": "simulation",
                "timeline_origin_id": origin,
            },
            "precision": "relative_day",
        }
    )


def make_extraction(data, source_text="Patient reports pain yesterday."):
    c, i, p, patient, origin, _, storage = data
    artifact = stage_note(data, source_text)
    document = register_note(
        c,
        i,
        p,
        patient.patient_id,
        NoteRegistration(artifact_id=artifact, anchor=note_anchor(origin)),
        storage,
    )
    extracted = extract_document(
        c, i, p, patient.patient_id, NoteExtractionCommand(note_id=document.note_id), storage
    )
    return document, extracted


def test_private_exact_note_source_extraction_replay_and_no_observation_promotion(clinical_db):
    c, i, p, patient, _, _, storage = clinical_db
    revision = load_revision(c, p, patient.patient_id, 1)
    original = "👩🏽‍⚕️ Cafe\u0301; Patient reports pain yesterday."
    document, extracted = make_extraction(clinical_db, original)
    assert document.source_sha256 == hashlib.sha256(original.encode()).hexdigest()
    assert document.normalized_text_sha256 == note_text_hash(original)
    assert document.source_sha256 != document.normalized_text_sha256
    assert read_note(c, i, p, patient.patient_id, document.note_id) == document
    assert read_extraction(c, i, p, patient.patient_id, extracted.extraction_id) == extracted
    assert (
        extract_document(
            c, i, p, patient.patient_id, NoteExtractionCommand(note_id=document.note_id), storage
        )
        == extracted
    )
    assert original not in extracted.model_dump_json()
    assert "Patient reports pain" not in extracted.model_dump_json()
    assert extracted.publication_status == "unpromoted_assertions"
    assert extracted.report.facts[0].provenance == "SYNTHETIC_GENERATED"
    assert extracted.report.facts[0].resolved_time.reference.value == "9"
    span = read_protected_span(c, i, p, patient.patient_id, extracted.extraction_id, 0, storage)
    assert span.mention == "pain" and span.assertion == "Patient reports pain yesterday"
    assert load_revision(c, p, patient.patient_id, 1) == revision
    assert (
        c.execute(
            text(
                "SELECT data_revision FROM source.research_patients WHERE project_id=:p AND id=:u"
            ),
            {"p": p, "u": patient.patient_id},
        ).scalar_one()
        == 1
    )
    assert (
        c.execute(
            text("SELECT count(*) FROM clinical.observations WHERE patient_id=:u"),
            {"u": patient.patient_id},
        ).scalar_one()
        == 0
    )
    c.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))


@pytest.mark.parametrize("table", ["note_documents", "note_extractions"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_note_records_and_extractions_are_sql_append_only(clinical_db, table, operation):
    c, _, _, _, _, _, _ = clinical_db
    document, result = make_extraction(clinical_db)
    identifier = document.note_id if table == "note_documents" else result.extraction_id
    statement = (
        f"UPDATE intelligence.{table} SET content_hash=content_hash WHERE id=:id"
        if operation == "UPDATE"
        else f"DELETE FROM intelligence.{table} WHERE id=:id"
    )
    with pytest.raises(DBAPIError), c.begin_nested():
        c.execute(text(statement), {"id": identifier})


def test_correction_appends_version_and_preserves_old_spans_and_assertions(clinical_db):
    c, i, p, patient, origin, _, storage = clinical_db
    first, positive = make_extraction(clinical_db)
    artifact = stage_note(clinical_db, "Patient denies pain yesterday.")
    corrected = register_note(
        c,
        i,
        p,
        patient.patient_id,
        NoteRegistration(
            artifact_id=artifact, supersedes_id=first.note_id, anchor=note_anchor(origin)
        ),
        storage,
    )
    negative = extract_document(
        c, i, p, patient.patient_id, NoteExtractionCommand(note_id=corrected.note_id), storage
    )
    assert corrected.note_id != first.note_id and corrected.version == 2
    assert corrected.supersedes_id == first.note_id
    assert not positive.report.facts[0].negated and negative.report.facts[0].negated
    assert read_note(c, i, p, patient.patient_id, first.note_id) == first
    assert (
        read_protected_span(
            c, i, p, patient.patient_id, positive.extraction_id, 0, storage
        ).assertion
        == "Patient reports pain yesterday"
    )
    assert (
        read_protected_span(
            c, i, p, patient.patient_id, negative.extraction_id, 0, storage
        ).assertion
        == "Patient denies pain yesterday"
    )


@pytest.mark.parametrize("role", ["viewer", "editor"])
def test_note_mutations_require_admin_and_viewer_cannot_read_notes(clinical_db, role):
    c, i, p, patient, _, _, storage = clinical_db
    document, result = make_extraction(clinical_db)
    restricted = Identity(i.user_id, {p: role})
    c.execute(
        text("INSERT INTO access.memberships(project_id,user_id,role) VALUES(:p,:u,:role)"),
        {"p": p, "u": i.user_id, "role": role},
    )
    c.execute(
        text(
            "INSERT INTO access.patient_grants(project_id,patient_id,user_id,permission) "
            "VALUES(:p,:u,:actor,'view')"
        ),
        {"p": p, "u": patient.patient_id, "actor": i.user_id},
    )
    operations = [
        lambda: register_note(
            c,
            restricted,
            p,
            patient.patient_id,
            NoteRegistration(artifact_id=document.artifact_id),
            storage,
        ),
        lambda: extract_document(
            c,
            restricted,
            p,
            patient.patient_id,
            NoteExtractionCommand(note_id=document.note_id),
            storage,
        ),
    ]
    if role == "viewer":
        operations += [
            lambda: read_note(c, restricted, p, patient.patient_id, document.note_id),
            lambda: read_extraction(c, restricted, p, patient.patient_id, result.extraction_id),
            lambda: read_protected_span(
                c, restricted, p, patient.patient_id, result.extraction_id, 0, storage
            ),
        ]
    else:
        assert read_extraction(c, restricted, p, patient.patient_id, result.extraction_id) == result
    for operation in operations:
        with pytest.raises(HTTPException) as error:
            operation()
        assert error.value.status_code == 403


@pytest.mark.parametrize("wrong_scope", ["patient", "project", "branch", "artifact_kind", "anchor"])
def test_independent_scope_ids_are_not_interchangeable(clinical_db, wrong_scope):
    c, i, p, patient, origin, _, storage = clinical_db
    document, result = make_extraction(clinical_db)
    if wrong_scope in ("patient", "project"):
        project = uuid4() if wrong_scope == "project" else p
        subject = uuid4() if wrong_scope == "patient" else patient.patient_id
        for operation in (
            lambda: read_note(c, i, project, subject, document.note_id),
            lambda: read_extraction(c, i, project, subject, result.extraction_id),
            lambda: read_protected_span(c, i, project, subject, result.extraction_id, 0, storage),
        ):
            with pytest.raises(HTTPException) as error:
                operation()
            assert error.value.status_code == 404
        return
    artifact = stage_note(
        clinical_db, kind="wrong_kind" if wrong_scope == "artifact_kind" else "note_source_artifact"
    )
    value = NoteRegistration(
        artifact_id=artifact,
        branch_id=uuid4() if wrong_scope == "branch" else None,
        anchor=note_anchor(uuid4() if wrong_scope == "anchor" else origin),
    )
    with pytest.raises(HTTPException):
        register_note(c, i, p, patient.patient_id, value, storage)


@pytest.mark.parametrize("change", ["internal", "derivative", "withdrawal"])
def test_current_rights_and_withdrawal_block_new_use_and_replay(clinical_db, change):
    c, i, p, patient, _, component, storage = clinical_db
    document, result = make_extraction(clinical_db)
    if change == "withdrawal":
        withdraw_resource(
            c,
            i,
            p,
            patient.patient_id,
            document.artifact_id,
            WithdrawalInput(reason_code="rights_withdrawn"),
        )
    else:
        action = "internal_processing" if change == "internal" else "derivative_creation"
        add_review(c, i, p, component, review(action=action, decision="denied"))
    with pytest.raises(HTTPException) as error:
        extract_document(
            c, i, p, patient.patient_id, NoteExtractionCommand(note_id=document.note_id), storage
        )
    assert error.value.status_code == 409
    if change != "derivative":
        with pytest.raises(HTTPException):
            read_extraction(c, i, p, patient.patient_id, result.extraction_id)
        with pytest.raises(HTTPException):
            read_protected_span(c, i, p, patient.patient_id, result.extraction_id, 0, storage)
    assert (
        c.execute(
            text("SELECT count(*) FROM intelligence.note_extractions WHERE id=:id"),
            {"id": result.extraction_id},
        ).scalar_one()
        == 1
    )


def test_internal_processing_denial_blocks_note_registration_before_source_read(clinical_db):
    c, i, p, patient, _, component, storage = clinical_db
    artifact = stage_note(clinical_db)
    add_review(c, i, p, component, review(action="internal_processing", decision="denied"))
    with pytest.raises(HTTPException) as error:
        register_note(c, i, p, patient.patient_id, NoteRegistration(artifact_id=artifact), storage)
    assert error.value.status_code == 409


@pytest.mark.parametrize("index", [-1, 1, True])
def test_protected_span_bounds_fail_without_source_disclosure(clinical_db, index):
    c, i, p, patient, _, _, storage = clinical_db
    _, result = make_extraction(clinical_db)
    with pytest.raises(HTTPException) as error:
        read_protected_span(c, i, p, patient.patient_id, result.extraction_id, index, storage)
    assert error.value.status_code == 404


@pytest.mark.parametrize(
    "raw,expected",
    [(b"", 422), (b"\xff", 409), (b"x" * 65537, 409)],
    ids=["empty", "invalid_utf8", "oversized"],
)
def test_note_registration_rejects_invalid_bounded_text(clinical_db, raw, expected):
    c, i, p, patient, _, _, storage = clinical_db
    artifact = stage_note(clinical_db, raw)
    with pytest.raises(HTTPException) as error:
        register_note(c, i, p, patient.patient_id, NoteRegistration(artifact_id=artifact), storage)
    assert error.value.status_code == expected


def test_protected_span_rechecks_private_object_integrity(clinical_db, monkeypatch):
    c, i, p, patient, _, _, storage = clinical_db
    _, result = make_extraction(clinical_db)

    def rejected_read(*args):
        raise ValueError("ARTIFACT_INTEGRITY_FAILURE")

    monkeypatch.setattr(storage, "read", rejected_read)
    with pytest.raises(HTTPException) as error:
        read_protected_span(c, i, p, patient.patient_id, result.extraction_id, 0, storage)
    assert error.value.status_code == 409


def test_note_http_commands_replay_scope_and_private_span_reads(clinical_db):
    c, i, p, patient, origin, component, storage = clinical_db
    artifact = stage_note(clinical_db, "Patient denies nausea.")
    client, headers = http_session((c, i, p, patient, component, storage, keys()))
    root = f"/api/v1/projects/{p}/patients/{patient.patient_id}"
    body = {"artifact_id": str(artifact), "anchor": note_anchor(origin).model_dump(mode="json")}
    with client:
        assert (
            client.post(
                root + "/note-documents",
                json=body,
                headers={"Idempotency-Key": "artificial-unauthenticated"},
            ).status_code
            == 401
        )
        command_headers = {**headers, "Idempotency-Key": "artificial-note-register"}
        response = client.post(root + "/note-documents", json=body, headers=command_headers)
        assert response.status_code == 201, response.text
        assert response.headers["location"].startswith(root + "/note-documents/")
        document = response.json()
        assert (
            client.post(root + "/note-documents", json=body, headers=command_headers).json()
            == document
        )
        extraction_body = {"note_id": document["note_id"]}
        extraction_headers = {**headers, "Idempotency-Key": "artificial-note-extract"}
        response = client.post(
            root + "/note-extractions", json=extraction_body, headers=extraction_headers
        )
        assert response.status_code == 201, response.text
        assert response.headers["cache-control"] == "private, no-store"
        extracted = response.json()
        assert extracted["report"]["facts"][0]["negated"] is True
        assert "Patient denies nausea" not in response.text
        assert (
            client.post(
                root + "/note-extractions", json=extraction_body, headers=extraction_headers
            ).json()
            == extracted
        )
        span_url = response.headers["location"] + "/facts/0/source-span"
        assert client.get(span_url).status_code == 401
        assert client.get(span_url, headers=headers).json()["assertion"] == "Patient denies nausea"
        assert (
            client.get(
                span_url.replace(str(patient.patient_id), str(uuid4())), headers=headers
            ).status_code
            == 404
        )
        assert (
            client.post(
                root + "/note-extractions",
                json={**extraction_body, "publication": "published"},
                headers=extraction_headers,
            ).status_code
            == 422
        )
        withdraw_resource(
            c, i, p, patient.patient_id, artifact, WithdrawalInput(reason_code="rights_withdrawn")
        )
        c.commit()
        assert (
            client.post(
                root + "/note-extractions", json=extraction_body, headers=extraction_headers
            ).status_code
            == 409
        )
        assert client.get(span_url, headers=headers).status_code == 409
