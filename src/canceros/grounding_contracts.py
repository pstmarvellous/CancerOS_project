"""Grounding gate contracts; validation logic lives in grounding_runs."""

from typing import Literal
from uuid import UUID

from pydantic import Field

from canceros.contracts import Contract, Hash

GroundingVerdict = Literal["published", "withheld_insufficient_evidence", "failed_grounding"]
ReasonCode = Literal[
    "SCHEMA_MISMATCH",
    "CONTEXT_MISMATCH",
    "UNRESOLVED_REFERENCE",
    "STALE_SOURCE_RIGHTS",
    "NUMERIC_MISMATCH",
    "UNIT_MISMATCH",
    "ORIGIN_MISMATCH",
    "PROHIBITED_CLAIM",
    "UNSUPPORTED_NOVEL_PROSE",
    "ABSTAIN_CRITICAL_INSUFFICIENT",
]


class GroundingCheckInput(Contract):
    interpretation_snapshot_id: UUID
    expected_context_hash: Hash | None = None


class GroundingReport(Contract):
    interpretation_snapshot_id: UUID
    context_snapshot_id: UUID
    verdict: GroundingVerdict
    reason_codes: tuple[ReasonCode, ...] = ()
    numeric_statements: int = Field(strict=True, ge=0)
    numeric_matched: int = Field(strict=True, ge=0)
    supported_claims: int = Field(strict=True, ge=0)
    unsupported_claims: int = Field(strict=True, ge=0)
    prohibited_critical: int = Field(strict=True, ge=0)
    next_action: str


class EvaluationSuiteVersion(Contract):
    name: Literal["grounding-language-suite/1"] = "grounding-language-suite/1"
    grounded_cases: int = Field(strict=True, ge=20)
    edge_cases: int = Field(strict=True, ge=20)
    adversarial_cases: int = Field(strict=True, ge=20)
