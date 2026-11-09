"""Bounded interpretation context contracts; assembly lives in context_runs."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from canceros.contracts import Contract, DecimalString, Hash

Code = Annotated[str, Field(strict=True, pattern=r"^[a-zA-Z0-9_.-]{1,64}$")]
MAX_CONTEXT_ITEMS = 200
MAX_TEXT_BYTES = 65536


class ContextMeasurement(Contract):
    reference_id: UUID
    metric_code: Code
    value: DecimalString
    unit: Annotated[str, Field(strict=True, min_length=1, max_length=64)]
    member_time: str
    origin: str
    context: str


class ContextAssertion(Contract):
    reference_id: UUID
    concept: Code
    excerpt: Annotated[str, Field(min_length=1, max_length=1000)]
    certainty: str
    negated: bool
    source_note_id: UUID
    source_hash: Hash
    verification: Literal["unverified_extracted_assertion"] = "unverified_extracted_assertion"


class ContextPassage(Contract):
    passage_id: UUID
    document_id: UUID
    corpus_id: UUID
    excerpt: Annotated[str, Field(min_length=1, max_length=1000)]
    locator: str
    semantic_support: Literal["unreviewed_general_research"] = "unreviewed_general_research"


class ContextBuildInput(Contract):
    patient_id: UUID
    snapshot_id: UUID
    expected_snapshot_hash: Hash | None = None
    purpose: Literal["research_summary", "fact_extraction"] = "research_summary"
    comparison_snapshot_id: UUID | None = None
    retrieval_corpus_id: UUID | None = None
    retrieval_passage_ids: tuple[UUID, ...] = Field(default=(), max_length=20)
    retrieval_query: Annotated[str, Field(min_length=1, max_length=256)] | None = None
    note_extraction_ids: tuple[UUID, ...] = Field(default=(), max_length=20)
    max_items: Annotated[int, Field(strict=True, ge=1, le=MAX_CONTEXT_ITEMS)] = 100


class InterpretationContext(Contract):
    schema_version: Literal["interpretation-context/1"] = "interpretation-context/1"
    patient_id: UUID
    branch_id: UUID
    snapshot_id: UUID
    snapshot_hash: Hash
    purpose: Literal["research_summary", "fact_extraction"]
    stale: bool
    comparison_snapshot_id: UUID | None = None
    comparison_stale: bool | None = None
    measurements: tuple[ContextMeasurement, ...] = ()
    comparison_measurements: tuple[ContextMeasurement, ...] = ()
    assertions: tuple[ContextAssertion, ...] = ()
    passages: tuple[ContextPassage, ...] = ()
    treatment_history: tuple[str, ...] = ()
    missing_modalities: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    limitations: tuple[str, ...] = (
        "Snapshot-bound research context only; no clinical interpretation or advice.",
        "Extracted assertions are unverified; passages are unreviewed general research.",
    )
    omitted: tuple[str, ...] = ()
    context_hash: Hash
    payload_hash: Hash
    exportable: bool
    next_action: str
