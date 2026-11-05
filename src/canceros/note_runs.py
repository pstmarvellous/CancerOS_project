"""Private immutable note versions; extraction never mutates accepted observations."""

import hashlib
import json
from typing import Literal
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import Field
from sqlalchemy import text

from canceros.clinical_contracts import ClinicalTime
from canceros.clinical_ingestion import check_time
from canceros.contracts import Context, Contract, Hash, Provenance
from canceros.identity import authorize_project
from canceros.lineage import (
    derive_resource,
    get_resource,
    lock_lineage,
    processing_spec,
    require_resource_action,
)
from canceros.note_extraction import (
    ExtractionReport,
    NoteInput,
    extract_note,
    normalize_note_text,
    protected_fact_text,
)
from canceros.patient_linkage import audit, authorize_patient
from canceros.persistence import science_hash
from canceros.source_registry import SourceAction, require_source_action
from canceros.storage import StoredObject
from canceros.twin_states import read_branch


class NoteRegistration(Contract):
    artifact_id: UUID
    branch_id: UUID | None = None
    anchor: ClinicalTime | None = None
    supersedes_id: UUID | None = None


class NoteDocument(Contract):
    note_id: UUID
    project_id: UUID
    patient_id: UUID
    artifact_id: UUID
    branch_id: UUID | None
    version: int = Field(strict=True, ge=1)
    supersedes_id: UUID | None
    normalized_text_sha256: Hash
    source_sha256: Hash
    normalization_version: Literal["unicode-nfc/1"] = "unicode-nfc/1"
    provenance: Provenance
    context: Context
    anchor: ClinicalTime | None
    language: Literal["en"] = "en"


def _authorize(c, i, p, u, edit=False):
    # Viewing a research state alone never grants original note/span access.
    authorize_project(i, p, "admin" if edit else "editor")
    authorize_patient(c, i, p, u, edit=edit)
    lock_lineage(c, p, u)


def _artifact(c, p, u, artifact_id, storage):
    row = (
        c.execute(
            text("SELECT * FROM ops.artifacts WHERE project_id=:p AND patient_id=:u AND id=:id"),
            {"p": p, "u": u, "id": artifact_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(404)
    if row["availability"] != "verified" or row["byte_size"] > 65536:
        raise HTTPException(409)
    try:
        raw = storage.read(
            StoredObject(
                p, row["object_key"], row["object_version"], row["sha256"], row["byte_size"]
            ),
            p,
        )
        return raw.decode("utf-8"), row["sha256"]
    except (ValueError, UnicodeError):
        raise HTTPException(409) from None


def read_note(c, i, p, u, note_id) -> NoteDocument:
    _authorize(c, i, p, u)
    row = c.execute(
        text(
            "SELECT payload,content_hash FROM intelligence.note_documents WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": p, "u": u, "id": note_id},
    ).first()
    if row is None:
        raise HTTPException(404)
    if science_hash(row.payload) != row.content_hash:
        raise HTTPException(409)
    require_resource_action(c, i, p, u, note_id, SourceAction.INTERNAL)
    document = NoteDocument.model_validate(row.payload)
    if document.branch_id:
        read_branch(c, i, p, u, document.branch_id)
        require_resource_action(c, i, p, u, document.branch_id, SourceAction.INTERNAL)
    return document


def register_note(c, i, p, u, value: NoteRegistration, storage) -> NoteDocument:
    _authorize(c, i, p, u, edit=True)
    resource = get_resource(c, i, p, u, value.artifact_id)
    if resource["kind"] != "note_source_artifact":
        raise HTTPException(422)
    require_resource_action(c, i, p, u, value.artifact_id, SourceAction.INTERNAL)
    require_resource_action(c, i, p, u, value.artifact_id, SourceAction.DERIVATIVE)
    synthetic = resource["origin"] == Provenance.SYNTHETIC_GENERATED
    if not synthetic:
        if resource["source_version_id"] is None or value.branch_id is not None:
            raise HTTPException(409)
        require_source_action(
            c, i, p, resource["source_version_id"], SourceAction.PATIENT, real_data=True
        )
    if value.branch_id:
        read_branch(c, i, p, u, value.branch_id)
        require_resource_action(c, i, p, u, value.branch_id, SourceAction.DERIVATIVE)
    if value.anchor:
        check_time(c, p, u, value.anchor)
        if synthetic and value.anchor.reference.time_domain != "simulation":
            raise HTTPException(422)
        if not synthetic and value.anchor.reference.time_domain == "simulation":
            raise HTTPException(422)
    previous = read_note(c, i, p, u, value.supersedes_id) if value.supersedes_id else None
    if previous and previous.branch_id != value.branch_id:
        raise HTTPException(422)
    original, digest = _artifact(c, p, u, value.artifact_id, storage)
    if digest != resource["content_hash"]:
        raise HTTPException(409)
    try:
        normalized = normalize_note_text(original)
        if not normalized:
            raise ValueError()
    except (ValueError, UnicodeError):
        raise HTTPException(422) from None
    document = NoteDocument(
        note_id=uuid4(),
        project_id=p,
        patient_id=u,
        artifact_id=value.artifact_id,
        branch_id=value.branch_id,
        version=previous.version + 1 if previous else 1,
        supersedes_id=value.supersedes_id,
        source_sha256=digest,
        normalized_text_sha256=hashlib.sha256(normalized.encode()).hexdigest(),
        provenance=Provenance.SYNTHETIC_GENERATED if synthetic else Provenance.REAL_DERIVED,
        context=Context.SYNTHETIC if synthetic else Context.OBSERVED,
        anchor=value.anchor,
    )
    payload = document.model_dump(mode="json")
    c.execute(
        text(
            "INSERT INTO intelligence.note_documents(id,project_id,patient_id,artifact_id,branch_id,version,supersedes_id,payload,content_hash) VALUES(:id,:p,:u,:a,:b,:v,:s,CAST(:payload AS jsonb),:hash)"
        ),
        {
            "id": document.note_id,
            "p": p,
            "u": u,
            "a": value.artifact_id,
            "b": value.branch_id,
            "v": document.version,
            "s": value.supersedes_id,
            "payload": json.dumps(payload),
            "hash": science_hash(payload),
        },
    )
    parents = [value.artifact_id] + ([value.branch_id] if value.branch_id else [])
    if previous:
        parents.append(previous.note_id)
    derive_resource(
        c,
        i,
        p,
        u,
        document.note_id,
        "note_document",
        science_hash(payload),
        parents,
        processing_spec(
            __file__, "private-note-registration", "unicode-nfc/1", value.model_dump(mode="json")
        ),
        expected_origin=document.provenance,
    )
    audit(c, p, document.note_id, "NOTE_VERSION_REGISTERED")
    return document


class NoteExtractionView(Contract):
    extraction_id: UUID
    report: ExtractionReport
    publication_status: Literal["unpromoted_assertions"] = "unpromoted_assertions"


class NoteExtractionCommand(Contract):
    note_id: UUID


class ProtectedSpan(Contract):
    note_id: UUID
    normalized_text_sha256: Hash
    mention: str
    assertion: str
    access_scope: Literal["authorized_note_source"] = "authorized_note_source"


def _load_input(c, i, p, u, note_id, storage):
    document = read_note(c, i, p, u, note_id)
    original, digest = _artifact(c, p, u, document.artifact_id, storage)
    if digest != document.source_sha256:
        raise HTTPException(409)
    try:
        return NoteInput(
            project_id=p,
            patient_id=u,
            branch_id=document.branch_id,
            note_id=note_id,
            note_version=document.version,
            context=document.context,
            provenance=document.provenance,
            text=normalize_note_text(original),
            normalized_text_sha256=document.normalized_text_sha256,
            anchor=document.anchor,
        )
    except ValueError:
        raise HTTPException(409) from None


def extract_document(c, i, p, u, value: NoteExtractionCommand, storage) -> NoteExtractionView:
    _authorize(c, i, p, u, edit=True)
    note = _load_input(c, i, p, u, value.note_id, storage)
    require_resource_action(c, i, p, u, value.note_id, SourceAction.DERIVATIVE)
    report = extract_note(note)
    payload = report.model_dump(mode="json")
    digest = science_hash(payload)
    prior = c.execute(
        text(
            "SELECT id FROM intelligence.note_extractions WHERE project_id=:p AND patient_id=:u AND note_id=:n AND content_hash=:h"
        ),
        {"p": p, "u": u, "n": note.note_id, "h": digest},
    ).first()
    if prior:
        return read_extraction(c, i, p, u, prior.id)
    identifier = uuid4()
    c.execute(
        text(
            "INSERT INTO intelligence.note_extractions(id,project_id,patient_id,note_id,report,content_hash) VALUES(:id,:p,:u,:n,CAST(:report AS jsonb),:h)"
        ),
        {
            "id": identifier,
            "p": p,
            "u": u,
            "n": note.note_id,
            "report": json.dumps(payload),
            "h": digest,
        },
    )
    derive_resource(
        c,
        i,
        p,
        u,
        identifier,
        "note_extraction",
        digest,
        [note.note_id],
        processing_spec(
            __file__,
            "scoped-note-extraction",
            report.extractor_version,
            {"normalization_version": report.normalization_version},
        ),
        expected_origin=note.provenance,
    )
    audit(c, p, identifier, "NOTE_ASSERTIONS_EXTRACTED")
    return NoteExtractionView(extraction_id=identifier, report=report)


def read_extraction(c, i, p, u, identifier) -> NoteExtractionView:
    _authorize(c, i, p, u)
    row = c.execute(
        text(
            "SELECT note_id,report,content_hash FROM intelligence.note_extractions WHERE project_id=:p AND patient_id=:u AND id=:id"
        ),
        {"p": p, "u": u, "id": identifier},
    ).first()
    if row is None:
        raise HTTPException(404)
    read_note(c, i, p, u, row.note_id)
    require_resource_action(c, i, p, u, identifier, SourceAction.INTERNAL)
    if science_hash(row.report) != row.content_hash:
        raise HTTPException(409)
    return NoteExtractionView(
        extraction_id=identifier, report=ExtractionReport.model_validate(row.report)
    )


def read_protected_span(c, i, p, u, identifier, fact_index: int, storage) -> ProtectedSpan:
    view = read_extraction(c, i, p, u, identifier)
    if type(fact_index) is not int or not 0 <= fact_index < len(view.report.facts):
        raise HTTPException(404)
    note = _load_input(c, i, p, u, view.report.note_id, storage)
    try:
        mention, assertion = protected_fact_text(note, view.report.facts[fact_index])
    except ValueError:
        raise HTTPException(409) from None
    audit(c, p, identifier, "NOTE_SUPPORTING_SPAN_READ")
    return ProtectedSpan(
        note_id=note.note_id,
        normalized_text_sha256=note.normalized_text_sha256,
        mention=mention,
        assertion=assertion,
    )
