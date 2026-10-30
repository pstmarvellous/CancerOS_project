"""Interpretation job contracts; orchestration lives in interpretation_jobs."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from canceros.contracts import Contract, Hash


class InterpretationJobInput(Contract):
    state_id: UUID
    expected_snapshot_hash: Hash | None = None
    purpose: Literal["research_summary", "fact_extraction"] = "research_summary"
    mode: Literal["template", "external_candidate"] = "template"
    idempotency_key: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")


class InterpretationJob(Contract):
    id: UUID
    context_snapshot_id: UUID
    context_hash: Hash
    snapshot_hash: Hash
    execution_mode: Literal["rule_based_summary", "external_candidate_private"]
    visibility: Literal["visible_template", "private_candidate"]
    status: Literal["validated_ready", "failed_grounding", "withheld_insufficient_evidence"]
    reason_codes: tuple[str, ...] = ()
    finding_count: int = Field(strict=True, ge=0)
    saved_id: UUID | None = None
    fallback_label: str | None = None
    next_action: str


class InterpretationJobPage(Contract):
    items: tuple[InterpretationJob, ...]
