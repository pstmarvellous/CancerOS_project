"""Typed descriptive relationships; SQL services own resolution, rights and history.

These links never establish causation, accept observations, select treatment or
modify the separate acyclic provenance graph. Concept cycles are permitted.
"""

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from canceros.clinical_contracts import ClinicalTime
from canceros.contracts import Contract, Provenance

EntityKind = Literal[
    "patient",
    "lesion_identity",
    "clinical_observation",
    "physical_measurement",
    "twin_branch",
    "twin_snapshot",
    "note_document",
    "note_extraction",
    "clinical_concept",
    "publication",
    "evidence_statement",
    "outcome",
]
RelationKind = Literal[
    "HAS_OBSERVATION",
    "HAS_LESION",
    "HAS_MEASUREMENT",
    "ABOUT_CONCEPT",
    "RELATED_TO",
    "ASSOCIATED_WITH",
    "GENERATED_FROM_BASELINE",
    "SUPPORTED_BY_PUBLICATION",
    "EXPOSED_TO_TREATMENT",
]
AssertionKind = Literal[
    "recorded_association",
    "extracted_assertion",
    "hypothetical_simulation",
    "general_research",
    "model_proposal",
]
ValidationStatus = Literal[
    "unverified_extracted_assertion",
    "unverified_proposal",
    "hypothetical",
    "source_linked_unreviewed",
]


class EntityRef(Contract):
    kind: EntityKind
    id: UUID


class ResolvedEntity(Contract):
    """Server-owned result of canonical row/registry and access verification."""

    ref: EntityRef
    project_id: UUID
    patient_id: UUID | None
    branch_id: UUID | None
    provenance: Provenance | None


class RelationshipInput(Contract):
    relation: RelationKind
    source: EntityRef
    target: EntityRef
    assertion_kind: AssertionKind
    supporting_resource_ids: tuple[UUID, ...] = Field(default=(), max_length=20)
    extraction_id: UUID | None = None
    fact_id: UUID | None = None
    supersedes_id: UUID | None = None
    time: ClinicalTime | None = None

    @model_validator(mode="after")
    def traceable_assertion(self):
        if len(self.supporting_resource_ids) != len(set(self.supporting_resource_ids)):
            raise ValueError("Duplicate supporting resources")
        extracted = self.assertion_kind == "extracted_assertion"
        if extracted:
            if (
                self.source.kind != "note_extraction"
                or self.extraction_id != self.source.id
                or self.fact_id is None
                or self.extraction_id not in self.supporting_resource_ids
            ):
                raise ValueError("Exact extraction and fact support required")
        elif self.extraction_id is not None or self.fact_id is not None:
            raise ValueError("Extraction references require extracted assertion semantics")
        if not self.supporting_resource_ids and self.assertion_kind != "model_proposal":
            raise ValueError("Supporting source records required")
        return self


class TraversalQuery(Contract):
    start: EntityRef
    depth: int = Field(default=1, strict=True, ge=1, le=3)
    limit: int = Field(default=25, strict=True, ge=1, le=100)
    offset: int = Field(default=0, strict=True, ge=0, le=10000)
    relation_kinds: tuple[RelationKind, ...] = Field(default=(), max_length=9)

    @model_validator(mode="after")
    def unique_kinds(self):
        if len(self.relation_kinds) != len(set(self.relation_kinds)):
            raise ValueError("Duplicate relation filters")
        return self


def relationship_validation_status(kind: AssertionKind) -> ValidationStatus:
    if kind == "extracted_assertion":
        return "unverified_extracted_assertion"
    if kind == "model_proposal":
        return "unverified_proposal"
    if kind == "hypothetical_simulation":
        return "hypothetical"
    if kind in ("recorded_association", "general_research"):
        return "source_linked_unreviewed"
    raise ValueError("Unknown assertion semantics")


_PAIRS: dict[str, set[tuple[str, str]]] = {
    "HAS_OBSERVATION": {("patient", "clinical_observation")},
    "HAS_LESION": {("patient", "lesion_identity")},
    "HAS_MEASUREMENT": {("lesion_identity", "physical_measurement")},
    "ABOUT_CONCEPT": {("note_extraction", "clinical_concept")},
    "RELATED_TO": {("clinical_concept", "clinical_concept")},
    "ASSOCIATED_WITH": {
        (a, b)
        for a in ("clinical_observation", "physical_measurement", "note_extraction")
        for b in ("clinical_observation", "physical_measurement", "note_extraction")
    },
    "GENERATED_FROM_BASELINE": {
        (kind, kind) for kind in ("physical_measurement", "clinical_observation", "twin_snapshot")
    }
    | {("twin_branch", "physical_measurement")},
}
_RESERVED = {"publication", "evidence_statement", "outcome"}


def validate_relationship(
    value: RelationshipInput,
    source: ResolvedEntity,
    target: ResolvedEntity,
    *,
    project_id: UUID,
    patient_id: UUID | None,
    branch_id: UUID | None,
    baseline_link_verified: bool = False,
) -> None:
    """Validate typed scope after independent canonical resolution and current rights.

    Source support, fact membership/qualifiers, true baseline membership, temporal
    anchors and correction identity require backing SQL checks by the caller.
    This pure function cannot turn a caller-supplied UUID into an owned resource.
    """
    if value.source != source.ref or value.target != target.ref:
        raise ValueError("Resolved endpoints do not match requested references")
    if source.project_id != project_id or target.project_id != project_id:
        raise ValueError("Cross-project relationship rejected")
    if (
        source.ref.kind in _RESERVED
        or target.ref.kind in _RESERVED
        or value.relation in ("SUPPORTED_BY_PUBLICATION", "EXPOSED_TO_TREATMENT")
    ):
        raise ValueError("Canonical evidence or treatment support is not enabled")
    if (source.ref.kind, target.ref.kind) not in _PAIRS.get(value.relation, set()):
        raise ValueError("Unsupported relationship endpoint kinds")
    for entity in (source, target):
        if entity.ref.kind == "clinical_concept":
            if entity.patient_id is not None or entity.branch_id is not None:
                raise ValueError("Shared concepts cannot carry patient or branch ownership")
        elif entity.patient_id != patient_id or patient_id is None:
            raise ValueError("Cross-patient relationship rejected")
        if entity.ref.kind == "patient" and entity.ref.id != patient_id:
            raise ValueError("Patient reference must match route owner")
        if entity.ref.kind == "patient" and entity.branch_id is not None:
            raise ValueError("Patient identity is not a branch member")
        if entity.branch_id is not None and entity.provenance != Provenance.SYNTHETIC_GENERATED:
            raise ValueError("Branch descendants retain synthetic origin")
    if value.relation == "RELATED_TO":
        if patient_id is not None or branch_id is not None:
            raise ValueError("General concept links require project-only context")
        if value.assertion_kind not in ("general_research", "model_proposal"):
            raise ValueError("General concept association cannot establish patient facts")
        return
    if patient_id is None or value.assertion_kind == "general_research":
        raise ValueError("General research cannot establish a patient fact")
    if value.relation == "ABOUT_CONCEPT" and value.assertion_kind not in (
        "extracted_assertion",
        "model_proposal",
    ):
        raise ValueError("A note extraction remains an assertion")
    if source.ref.kind == "note_extraction" and value.assertion_kind not in (
        "extracted_assertion",
        "model_proposal",
    ):
        raise ValueError("An extracted assertion cannot become an accepted observation")
    if value.relation == "GENERATED_FROM_BASELINE":
        if (
            not baseline_link_verified
            or branch_id is None
            or source.branch_id != branch_id
            or target.branch_id is not None
            or value.assertion_kind != "hypothetical_simulation"
            or source.provenance != Provenance.SYNTHETIC_GENERATED
        ):
            raise ValueError("Explicit owned observed-baseline link required")
    else:
        for entity in (source, target):
            # The patient identity owns all its branches; shared concepts are not
            # branch members. Every ordinary resource endpoint matches exactly.
            if (
                entity.ref.kind not in ("patient", "clinical_concept")
                and entity.branch_id != branch_id
            ):
                raise ValueError("Cross-branch relationship rejected")
    if any(entity.provenance == Provenance.SYNTHETIC_GENERATED for entity in (source, target)):
        if value.assertion_kind not in (
            "hypothetical_simulation",
            "extracted_assertion",
            "model_proposal",
        ):
            raise ValueError("Synthetic association cannot acquire real-source semantics")
