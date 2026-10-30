"""Persistence contracts for validated interpretations; no new public exposure."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from canceros.contracts import Contract, Hash

Label = Annotated[str, Field(strict=True, min_length=1, max_length=200)]


class InterpretationPersistInput(Contract):
    interpretation_snapshot_id: UUID
    idempotency_key: Annotated[str, Field(min_length=1, max_length=128)]


class PersistedInterpretation(Contract):
    id: UUID
    project_id: UUID
    patient_id: UUID
    context_snapshot_id: UUID
    context_hash: Hash
    execution_mode: Literal["rule_based_summary", "external_candidate_private"]
    visibility: Literal["visible_template", "private_candidate"]
    model_identifier: Label
    model_revision: Literal["unresolved"] = "unresolved"
    prompt_version: Label
    validator_version: Label
    corpus_manifest: str = Field(min_length=1, max_length=500)
    finding_count: int = Field(strict=True, ge=0)
    usage_tokens: int | None = Field(default=None, strict=True, ge=0)
    failure_stage: str | None = Field(default=None, max_length=200)
    status: Literal["validated_ready", "private_candidate", "superseded", "withdrawn"]
    superseded_by_id: UUID | None = None
    next_action: str


class SavedResultQuery(Contract):
    context_snapshot_id: UUID
    expected_context_hash: Hash | None = None
