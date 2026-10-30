"""Versioned PostgreSQL keyword retrieval and offline citation resolution.

Lexical matches remain unreviewed candidates. This service neither establishes
patient findings nor adjudicates contradictory literature or treatment effects.
"""

import unicodedata
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from fastapi import HTTPException
from pydantic import AwareDatetime, Field, field_validator, model_validator
from sqlalchemy import bindparam, text

from canceros.contracts import Contract, Hash
from canceros.evidence_contracts import Code, EvidenceManifest
from canceros.evidence_runs import (
    EvidencePassageView,
    read_corpus,
    read_current_corpus,
    read_document,
    read_passage,
)

SETTINGS_VERSION: Literal["postgres-curated-retrieval/1"] = "postgres-curated-retrieval/1"


class EvidenceRetrievalQuery(Contract):
    corpus_id: UUID
    expected_active_activation_id: UUID | None = None
    query: str = Field(strict=True, min_length=1, max_length=256)
    concepts: tuple[Code, ...] = Field(default=(), max_length=10)
    topics: tuple[Code, ...] = Field(default=(), max_length=10)
    subtype: Code | None = None
    setting: Code | None = None
    publication_not_before: date | None = None
    updated_not_before: date | None = None
    top_k: int = Field(default=5, strict=True, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def normalized_query(cls, value):
        value = " ".join(unicodedata.normalize("NFC", value).split())
        if not value or "\x00" in value:
            raise ValueError("Nonblank bounded research query required")
        value.encode("utf-8", errors="strict")
        return value

    @field_validator("publication_not_before", "updated_not_before", mode="before")
    @classmethod
    def exact_calendar_date(cls, value):
        if value is not None and (
            isinstance(value, datetime)
            or not isinstance(value, (str, date))
            or (isinstance(value, str) and len(value) != 10)
        ):
            raise ValueError("Calendar date required")
        return value

    @model_validator(mode="after")
    def unique_filters(self):
        if len(self.concepts) != len(set(self.concepts)) or len(self.topics) != len(
            set(self.topics)
        ):
            raise ValueError("Duplicate research filters")
        return self


class EvidenceSourceMetadata(Contract):
    title: str
    publisher: str
    authors: tuple[str, ...] | None
    canonical_url: str
    doi: str | None
    publication_date: date | None
    update_date: date | None
    retrieved_at: AwareDatetime
    document_version: str
    topics: tuple[Code, ...]
    subtypes: tuple[Code, ...]
    settings: tuple[Code, ...]
    attribution: str
    review_basis: Literal["synthetic_fixture", "documented_review"]
    retraction_status: Literal["clear", "unknown", "retracted"]


def public_source_metadata(manifest: EvidenceManifest) -> EvidenceSourceMetadata:
    """Expose citation metadata without private registry or review-evidence locators."""
    return EvidenceSourceMetadata.model_validate(
        manifest.model_dump(include=set(EvidenceSourceMetadata.model_fields))
    )


class RetrievalHit(Contract):
    rank: int = Field(strict=True, ge=1, le=10)
    passage: EvidencePassageView
    source: EvidenceSourceMetadata
    rationales: tuple[str, ...]
    semantic_support: Literal["unreviewed_general_research"] = "unreviewed_general_research"
    patient_fact_support: Literal[False] = False
    individual_treatment_effect_support: Literal[False] = False


class EvidenceRetrievalReport(Contract):
    corpus_id: UUID
    activation_id: UUID
    settings_version: Literal["postgres-curated-retrieval/1"] = SETTINGS_VERSION
    items: tuple[RetrievalHit, ...]
    status: Literal["matched", "no_suitable_evidence"]
    next_action: Literal["review_candidate_passages", "narrow_question_or_request_curator_review"]
    limitations: tuple[str, ...] = (
        "Keyword rank measures lexical relevance, not clinical confidence or claim support.",
        "Conflicting passages remain candidates; no semantic conflict adjudication is performed.",
        "Unknown subtype and setting use only generic context evidence.",
    )


class CitationCheck(Contract):
    corpus_id: UUID
    passage_id: UUID
    expected_text_sha256: Hash | None = None
    intended_use: Literal["general_background", "patient_fact", "individual_treatment_effect"] = (
        "general_background"
    )


class CitationReport(Contract):
    passage: EvidencePassageView
    source: EvidenceSourceMetadata
    corpus_status: Literal["active", "historical"]
    citation_status: Literal["verified_offline_manifest"] = "verified_offline_manifest"
    live_url_status: Literal["not_checked"] = "not_checked"
    meaningful_support: Literal["unreviewed", "not_supported"]
    next_action: Literal["review_passage_to_claim_support", "use_verified_patient_observations"]
    limitations: tuple[str, ...] = (
        "A permitted exact passage and valid locator do not prove a clinical claim.",
        "No external URL, DOI resolver or provider was contacted.",
    )


def _compatible(manifest: EvidenceManifest, query: EvidenceRetrievalQuery) -> bool:
    if not set(query.topics).issubset(manifest.topics):
        return False
    for requested, supplied in (
        (query.subtype, manifest.subtypes),
        (query.setting, manifest.settings),
    ):
        if supplied and (requested is None or requested not in supplied):
            return False
    if query.publication_not_before and (
        manifest.publication_date is None
        or manifest.publication_date < query.publication_not_before
    ):
        return False
    if query.updated_not_before and (
        manifest.update_date is None or manifest.update_date < query.updated_not_before
    ):
        return False
    return True


def retrieve_evidence(c, i, p, value: EvidenceRetrievalQuery) -> EvidenceRetrievalReport:
    head = read_current_corpus(c, i, p)
    if head.status != "active" or head.corpus_id != value.corpus_id or head.activation_id is None:
        raise HTTPException(409)
    if (
        value.expected_active_activation_id is not None
        and value.expected_active_activation_id != head.activation_id
    ):
        raise HTTPException(409)
    corpus = read_corpus(c, i, p, value.corpus_id)
    documents = {
        identifier: read_document(c, i, p, identifier) for identifier in corpus.document_ids
    }
    eligible = {
        identifier
        for identifier, document in documents.items()
        if _compatible(document.manifest, value)
    }
    if not eligible:
        return EvidenceRetrievalReport(
            corpus_id=corpus.id,
            activation_id=head.activation_id,
            items=(),
            status="no_suitable_evidence",
            next_action="narrow_question_or_request_curator_review",
        )
    # Every token is a parameter to PostgreSQL's plain parser; no operators,
    # instructions, URLs or executable text are interpreted by this application.
    search = " ".join((value.query, *(concept.replace("_", " ") for concept in value.concepts)))
    rows = c.execute(
        text("""SELECT t.document_id,t.passage_id,
      ts_rank(t.search_vector,plainto_tsquery('english',:query)) AS lexical_rank
      FROM intelligence.evidence_passage_content t
      JOIN intelligence.evidence_corpus_members m ON(m.project_id,m.document_id)=(t.project_id,t.document_id)
      WHERE t.project_id=:p AND m.corpus_id=:corpus
      AND t.document_id IN :eligible
      AND t.search_vector @@ plainto_tsquery('english',:query)
      ORDER BY lexical_rank DESC,t.document_id,t.passage_id LIMIT :top_k""").bindparams(
            bindparam("eligible", expanding=True)
        ),
        {
            "p": p,
            "corpus": value.corpus_id,
            "query": search,
            "eligible": sorted(eligible, key=str),
            "top_k": value.top_k,
        },
    ).all()
    hits: list[RetrievalHit] = []
    for row in rows:
        if row.document_id not in eligible:
            continue
        passage = read_passage(c, i, p, value.corpus_id, row.passage_id)
        hits.append(
            RetrievalHit(
                rank=len(hits) + 1,
                passage=passage,
                source=public_source_metadata(documents[row.document_id].manifest),
                rationales=(
                    "keyword_match",
                    "compatible_declared_context",
                    "current_source_rights_checked",
                ),
            )
        )
        if len(hits) == value.top_k:
            break
    return EvidenceRetrievalReport(
        corpus_id=corpus.id,
        activation_id=head.activation_id,
        items=tuple(hits),
        status="matched" if hits else "no_suitable_evidence",
        next_action="review_candidate_passages"
        if hits
        else "narrow_question_or_request_curator_review",
    )


def verify_citation(c, i, p, value: CitationCheck) -> CitationReport:
    passage = read_passage(c, i, p, value.corpus_id, value.passage_id)
    if (
        value.expected_text_sha256 is not None
        and value.expected_text_sha256 != passage.descriptor.text_sha256
    ):
        raise HTTPException(409)
    source = read_document(c, i, p, passage.document_id).manifest
    head = read_current_corpus(c, i, p)
    active = head.status == "active" and head.corpus_id == value.corpus_id
    return CitationReport(
        passage=passage,
        source=public_source_metadata(source),
        corpus_status="active" if active else "historical",
        meaningful_support="unreviewed"
        if value.intended_use == "general_background"
        else "not_supported",
        next_action="review_passage_to_claim_support"
        if value.intended_use == "general_background"
        else "use_verified_patient_observations",
    )
