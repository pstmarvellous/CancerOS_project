"""Provider-boundary/1 internal contracts; not a patient-data proxy API."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from canceros.contracts import Contract, DecimalString, Hash, Provenance

Code = Annotated[str, Field(strict=True, pattern=r"^[a-zA-Z0-9_.-]{1,64}$")]


class ExportMeasurement(Contract):
    reference_id: UUID
    metric_code: Code
    value: DecimalString
    unit: Code
    provenance: Provenance


class ProviderInput(Contract):
    schema_version: Literal["provider-input/1"] = "provider-input/1"
    purpose: Literal["research_summary", "fact_extraction"]
    input_snapshot_hash: Hash
    measurements: tuple[ExportMeasurement, ...] = Field(max_length=100)
    missingness: tuple[Code, ...] = Field(max_length=100)
    evidence_ids: tuple[UUID, ...] = Field(max_length=20)

    @model_validator(mode="after")
    def unique_references(self):
        ids = [m.reference_id for m in self.measurements]
        if len(ids) != len(set(ids)) or len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("Duplicate input references")
        return self


class CandidateFinding(Contract):
    text: str = Field(strict=True, min_length=1, max_length=1000)
    measurement_refs: tuple[UUID, ...] = Field(max_length=20)
    passage_refs: tuple[UUID, ...] = Field(max_length=20)


class ProviderCandidate(Contract):
    schema_version: Literal["provider-candidate/1"]
    input_snapshot_hash: Hash
    findings: tuple[CandidateFinding, ...] = Field(max_length=20)


class ProviderCapabilities(Contract):
    schema_version: Literal["provider-capabilities/1"] = "provider-capabilities/1"
    local_summary_available: Literal[True] = True
    external_model_available: Literal[False] = False
    external_status: Literal["policy_access_and_grounding_review_required"] = (
        "policy_access_and_grounding_review_required"
    )
    candidate_publication_available: Literal[False] = False
    note_extraction_available: Literal[False] = False
    local_note_extraction_available: Literal[True] = True
    local_note_extraction_scope: Literal["four_symptom_templates_synthetic_fixture_only"] = (
        "four_symptom_templates_synthetic_fixture_only"
    )
    next_action: Literal["use_local_mode"] = "use_local_mode"


class LocalSummary(Contract):
    execution_mode: Literal["local_template"] = "local_template"
    input_snapshot_hash: Hash
    status: Literal["source_inventory", "insufficient_evidence"]
    summary: str
    measurement_refs: tuple[UUID, ...]
    limitations: tuple[str, ...] = (
        "Source inventory only; no clinical interpretation or provider inference.",
    )


def local_summary(context: ProviderInput) -> LocalSummary:
    """Called only with an already-authorized projection, never a raw HTTP body."""
    count = len(context.measurements)
    return LocalSummary(
        input_snapshot_hash=context.input_snapshot_hash,
        status="source_inventory" if count else "insufficient_evidence",
        summary=f"Selected input contains {count} supplied measurements and "
        f"{len(context.missingness)} missing-data categories.",
        measurement_refs=tuple(m.reference_id for m in context.measurements),
    )
