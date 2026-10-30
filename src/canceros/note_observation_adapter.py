"""Explicit source-note pointers; extracted assertions never become observations."""

from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import text

from canceros.clinical_contracts import NoteInput
from canceros.contracts import Context, Provenance
from canceros.lineage import require_resource_action
from canceros.source_registry import SourceAction

if TYPE_CHECKING:
    from canceros.note_runs import NoteDocument


def validate_note_pointer(c, i, p, u, item: NoteInput) -> "NoteDocument":
    # note_runs depends on ingestion.check_time; importing it only at invocation
    # keeps the canonical ingestion service free of a module initialization cycle.
    from canceros.note_runs import read_note

    if item.note_document_id is None:
        raise HTTPException(422)
    document = read_note(c, i, p, u, item.note_document_id)
    for action in (SourceAction.INTERNAL, SourceAction.DERIVATIVE):
        require_resource_action(c, i, p, u, document.note_id, action)
    if (
        document.branch_id is not None
        or document.context != Context.SYNTHETIC
        or document.provenance != Provenance.SYNTHETIC_GENERATED
        or item.artifact_id != document.artifact_id
        or item.content_sha256 != document.source_sha256
        or item.language != "en"
        or item.language != document.language
    ):
        raise HTTPException(422)
    if document.anchor is None:
        if item.time.reference.basis != "unknown":
            raise HTTPException(422)
    elif document.anchor != item.time:
        raise HTTPException(422)
    return document


def persist_note_pointer(c, p, u, observation_id, item: NoteInput) -> None:
    if item.note_document_id is None:
        raise HTTPException(409)
    c.execute(
        text(
            "INSERT INTO clinical.note_documents(observation_id,project_id,patient_id,"
            "note_document_id,artifact_id,language,content_sha256) "
            "VALUES(:id,:p,:u,:note,:artifact,:language,:hash)"
        ),
        {
            "id": observation_id,
            "p": p,
            "u": u,
            "note": item.note_document_id,
            "artifact": item.artifact_id,
            "language": item.language,
            "hash": item.content_sha256,
        },
    )
