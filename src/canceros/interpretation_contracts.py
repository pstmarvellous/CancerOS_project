"""Bounded interpretation contracts; validators and persistence live in COS-064/065."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from canceros.contracts import Contract, Hash

Code = Annotated[str, Field(strict=True, pattern=r"^[a-zA-Z0-9_.-]{1,64}$")]
MAX_FINDINGS = 20


class InterpretationFinding(Contract):
    kind: Literal["observed_measurement", "synthetic_scenario", "general_background", "gap"]
    text: Annotated[str, Field(min_length=1, max_length=1000)]
    measurement_refs: tuple[UUID, ...] = Field(default=(), max_length=20)
    passage_refs: tuple[UUID, ...] = Field(default=(), max_length=20)
    metric_code: Code | None = None
    metric_value: str | None = None
    metric_unit: str | None = None


class InterpretationInput(Contract):
    context_snapshot_id: UUID
    expected_context_hash: Hash | None = None
    mode: Literal["template", "external_candidate"] = "template"


class InterpretationReport(Contract):
    schema_version: Literal["interpretation/1"] = "interpretation/1"
    context_snapshot_id: UUID
    context_hash: Hash
    snapshot_hash: Hash
    execution_mode: Literal["rule_based_summary", "external_candidate_private"] = (
        "rule_based_summary"
    )
    summary: Annotated[str, Field(min_length=1, max_length=2000)]
    findings: tuple[InterpretationFinding, ...] = Field(max_length=MAX_FINDINGS)
    uncertainties: tuple[str, ...] = ()
    limitations: tuple[str, ...] = (
        "Rule-based summary only; no clinical interpretation, diagnosis or advice.",
        "External candidates remain private until grounding/safety validation passes.",
    )
    visibility: Literal["visible_template", "private_candidate"] = "visible_template"
    next_action: str
