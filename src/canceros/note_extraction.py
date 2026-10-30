"""Narrow deterministic symptom assertions, never canonical clinical observations.

The caller owns authorization and note/anchor verification. No network, model,
instruction execution, diagnosis, numerical severity or laboratory extraction.
"""

import hashlib
import re
import unicodedata
from datetime import timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import ConfigDict, Field, model_validator

from canceros.clinical_contracts import ClinicalTime
from canceros.contracts import Context, Contract, Hash, Provenance, derived_origin

NORMALIZATION_VERSION: Literal["unicode-nfc/1"] = "unicode-nfc/1"
EXTRACTOR_VERSION: Literal["scoped-symptom-grammar/1"] = "scoped-symptom-grammar/1"


def normalize_note_text(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    # Reject surrogate code points rather than producing incompatible byte hashes.
    normalized.encode("utf-8", errors="strict")
    return normalized


def note_text_hash(text: str) -> str:
    return hashlib.sha256(normalize_note_text(text).encode("utf-8")).hexdigest()


class TextSpan(Contract):
    start: int = Field(strict=True, ge=0)
    end: int = Field(strict=True, ge=1)

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("Invalid end-exclusive code-point span")
        return self


class NoteInput(Contract):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    project_id: UUID
    patient_id: UUID
    branch_id: UUID | None
    note_id: UUID
    note_version: int = Field(strict=True, ge=1)
    context: Context
    provenance: Provenance
    text: str = Field(min_length=1, max_length=65536, repr=False, exclude=True)
    normalized_text_sha256: Hash
    normalization_version: Literal["unicode-nfc/1"] = NORMALIZATION_VERSION
    anchor: ClinicalTime | None = None

    @model_validator(mode="after")
    def exact_source(self):
        if (
            normalize_note_text(self.text) != self.text
            or note_text_hash(self.text) != self.normalized_text_sha256
        ):
            raise ValueError("Exact normalized source hash required")
        if len(self.text.encode("utf-8")) > 65536:
            raise ValueError("Note exceeds bounded UTF-8 size")
        synthetic = self.provenance == Provenance.SYNTHETIC_GENERATED
        if (self.context == Context.SYNTHETIC) != synthetic:
            raise ValueError("Source context and provenance disagree")
        if self.branch_id is not None and not synthetic:
            raise ValueError("A simulated branch requires synthetic source origin")
        return self


class ExtractedFact(Contract):
    fact_id: UUID
    project_id: UUID
    patient_id: UUID
    branch_id: UUID | None
    note_id: UUID
    note_version: int = Field(strict=True, ge=1)
    normalized_text_sha256: Hash
    concept: Literal["fatigue", "pain", "nausea", "swelling"]
    mention_span: TextSpan
    assertion_span: TextSpan
    certainty: Literal["affirmed", "possible", "not_asserted"]
    negated: bool
    experiencer: Literal["patient", "family"]
    temporality: Literal["current", "historical", "planned", "assessment"]
    temporal_expression: Literal["absent", "today", "yesterday", "days_ago", "last_visit"]
    relative_days: int | None = None
    resolved_time: ClinicalTime | None = None
    time_status: Literal["resolved_from_verified_anchor", "unresolved"]
    context: Context
    provenance: Provenance
    validation_status: Literal["unverified_extracted_assertion"] = "unverified_extracted_assertion"
    extractor_version: Literal["scoped-symptom-grammar/1"] = EXTRACTOR_VERSION


class ExtractionReport(Contract):
    schema_version: Literal["note-extraction/1"] = "note-extraction/1"
    extractor_version: Literal["scoped-symptom-grammar/1"] = EXTRACTOR_VERSION
    normalization_version: Literal["unicode-nfc/1"] = NORMALIZATION_VERSION
    project_id: UUID
    patient_id: UUID
    branch_id: UUID | None
    note_id: UUID
    note_version: int
    normalized_text_sha256: Hash
    facts: tuple[ExtractedFact, ...]
    unsupported_clause_spans: tuple[TextSpan, ...]
    execution_mode: Literal["deterministic_scoped_parser"] = "deterministic_scoped_parser"
    limitations: tuple[str, ...] = (
        "Four symptom concepts and explicit clause templates only; no general clinical NLP.",
        "No numerical severity, laboratory, receptor, diagnosis or therapy extraction.",
        "Assertions require source review and never replace canonical observations.",
    )


# Each complete clause matches exactly one supported reporting frame.
_PREFIX = {
    "patient reports": ("affirmed", False, "patient", "current"),
    "patient reports no": ("affirmed", True, "patient", "current"),
    "patient denies": ("affirmed", True, "patient", "current"),
    "no": ("affirmed", True, "patient", "current"),
    "no evidence of": ("affirmed", True, "patient", "current"),
    "possible": ("possible", False, "patient", "current"),
    "patient reports possible": ("possible", False, "patient", "current"),
    "patient reported": ("affirmed", False, "patient", "historical"),
    "history of": ("affirmed", False, "patient", "historical"),
    "family history of": ("affirmed", False, "family", "historical"),
    "plan to assess": ("not_asserted", False, "patient", "planned"),
    "assess for": ("not_asserted", False, "patient", "assessment"),
}
_CLAUSE = re.compile(
    r"(?P<prefix>"
    + "|".join(re.escape(p) for p in sorted(_PREFIX, key=len, reverse=True))
    + r") (?P<concept>fatigue|pain|nausea|swelling)"
    + r"(?: (?P<time>today|yesterday|[1-9][0-9]{0,2} days ago|at last visit))?",
    re.IGNORECASE,
)


def _resolve(anchor: ClinicalTime | None, days: int | None) -> ClinicalTime | None:
    if anchor is None or days is None or anchor.reference.basis == "unknown":
        return None
    reference = anchor.reference
    try:
        value: Any
        if reference.basis == "relative_day":
            value = format(Decimal(reference.value) + days, "f")
        else:
            value = reference.value + timedelta(days=days)
        changed = reference.model_dump()
        changed["value"] = value
        return ClinicalTime.model_validate({**anchor.model_dump(), "reference": changed})
    except (ValueError, OverflowError):
        return None


def extract_note(note: NoteInput) -> ExtractionReport:
    note = NoteInput.model_validate({**note.model_dump(), "text": note.text})
    facts = []
    unsupported = []
    # Period/newline/semicolon delimit only complete standalone clauses. Quoted,
    # compound, numerical and instructional clauses abstain rather than guessing.
    for clause in re.finditer(r"[^.;\n]+", note.text):
        raw = clause.group()
        text = raw.strip()
        if not text:
            continue
        start = clause.start() + len(raw) - len(raw.lstrip())
        span = TextSpan(start=start, end=start + len(text))
        match = _CLAUSE.fullmatch(text)
        if match is None:
            unsupported.append(span)
            continue
        certainty, negated, experiencer, temporality = _PREFIX[match["prefix"].lower()]
        time = (match["time"] or "").lower()
        expression = "absent"
        days = None
        if time == "today":
            expression, days = "today", 0
        elif time == "yesterday":
            expression, days = "yesterday", -1
        elif time.endswith("days ago"):
            expression, days = "days_ago", -int(time.split()[0])
        elif time == "at last visit":
            expression = "last_visit"
        if (
            expression == "last_visit" or (days is not None and days < 0)
        ) and temporality == "current":
            temporality = "historical"
        resolved = _resolve(note.anchor, days)
        facts.append(
            ExtractedFact.model_validate(
                dict(
                    fact_id=uuid5(
                        NAMESPACE_URL,
                        f"canceros-note-fact:{note.note_id}:{note.normalized_text_sha256}:{span.start}:{span.end}:{EXTRACTOR_VERSION}",
                    ),
                    project_id=note.project_id,
                    patient_id=note.patient_id,
                    branch_id=note.branch_id,
                    note_id=note.note_id,
                    note_version=note.note_version,
                    normalized_text_sha256=note.normalized_text_sha256,
                    concept=match["concept"].lower(),
                    mention_span=TextSpan(
                        start=start + match.start("concept"), end=start + match.end("concept")
                    ),
                    assertion_span=span,
                    certainty=certainty,
                    negated=negated,
                    experiencer=experiencer,
                    temporality=temporality,
                    temporal_expression=expression,
                    relative_days=days,
                    resolved_time=resolved,
                    time_status="resolved_from_verified_anchor" if resolved else "unresolved",
                    context=note.context,
                    provenance=derived_origin(note.provenance),
                )
            )
        )
    return ExtractionReport(
        project_id=note.project_id,
        patient_id=note.patient_id,
        branch_id=note.branch_id,
        note_id=note.note_id,
        note_version=note.note_version,
        normalized_text_sha256=note.normalized_text_sha256,
        facts=tuple(facts),
        unsupported_clause_spans=tuple(unsupported),
    )


def protected_fact_text(note: NoteInput, fact: ExtractedFact) -> tuple[str, str]:
    """Return exact protected mention/assertion after caller authorizes note access.

    Replaying the bounded grammar verifies qualifiers and identity as well as spans;
    merely pointing at a matching symptom substring is not sufficient validation.
    """
    if (
        fact
        not in extract_note(
            NoteInput.model_validate({**note.model_dump(), "text": note.text})
        ).facts
    ):
        raise ValueError("Fact does not belong to the exact note context")
    mention, assertion = fact.mention_span, fact.assertion_span
    return note.text[mention.start : mention.end], note.text[assertion.start : assertion.end]


def codepoint_to_utf16(text: str, offset: int) -> int:
    if type(offset) is not int or not 0 <= offset <= len(text):
        raise ValueError("Invalid Unicode code-point offset")
    return len(text[:offset].encode("utf-16-le", errors="strict")) // 2


def utf16_to_codepoint(text: str, offset: int) -> int:
    if type(offset) is not int or offset < 0:
        raise ValueError("Invalid UTF-16 offset")
    consumed = 0
    for index, char in enumerate(text):
        if consumed == offset:
            return index
        consumed += 2 if ord(char) > 0xFFFF else 1
        if consumed > offset:
            raise ValueError("UTF-16 offset splits a surrogate pair")
    if consumed == offset:
        return len(text)
    raise ValueError("UTF-16 offset outside note")
