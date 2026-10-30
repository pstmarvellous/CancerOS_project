"""Mandatory publication gate: numeric fidelity, allowed claims, abstention."""

import re
from typing import Literal

from fastapi import HTTPException

from canceros.context_contracts import InterpretationContext
from canceros.grounding_contracts import GroundingReport, ReasonCode
from canceros.interpretation_contracts import InterpretationReport
from canceros.provider_gateway import PrivateResult, ProviderFailure

GATE_VERSION: str = "grounding-gate/1"

PROHIBITED_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bstag(?:e|ing)\b|\bTNM\b|\bgrade\b", "staging_or_grade"),
    (r"\bsurviv(?:al|e)\b|\bprognos", "survival_or_prognosis"),
    (r"\bresistan", "resistance"),
    (r"\bRECIST\b|\bCTCAE\b|\bresponse\s+grade\b|\bcomplete\s+response\b|\bpartial\s+response\b", "formal_response_grade"),
    (r"\brecommend|\bprescrib|\bdose\b|\bdosage\b|\btreatment\s+rank", "treatment_advice"),
    (r"\bcaus(?:e[sd]?|ality)\b.*\badverse\b|\badverse\b.*\bcaus", "adverse_event_causation"),
    (r"\bdiagnos(?:is|ed|tic)\b", "diagnosis"),
    (r"\bconfiden(?:ce|t)\b|\bcalibrated\b|p\s*<\s*0\.05|95%\s*CI", "invented_confidence"),
)

ALLOWED_GENERAL_BACKGROUND = (
    "unreviewed general research",
    "background only",
    "general background",
)


def _prohibited(text: str) -> list[str]:
    lowered = text.lower()
    hits = []
    for pattern, label in PROHIBITED_PATTERNS:
        if re.search(pattern, lowered):
            hits.append(label)
    return hits


def validate_publication(
    context: InterpretationContext, report: InterpretationReport
) -> GroundingReport:
    reasons: list[ReasonCode] = []
    if report.context_hash != context.context_hash or report.snapshot_hash != context.snapshot_hash:
        reasons.append("CONTEXT_MISMATCH")
    measurement_ids = {m.reference_id for m in context.measurements}
    passage_ids = {g.passage_id for g in context.passages}
    measured_values = {
        (str(m.reference_id), m.metric_code, m.value, m.unit) for m in context.measurements
    }
    numeric_total = numeric_ok = supported = unsupported = prohibited = 0

    def insensitive(value):
        return (value or "").strip().lower()
    for finding in report.findings:
        if set(finding.measurement_refs) - measurement_ids or set(finding.passage_refs) - passage_ids:
            reasons.append("UNRESOLVED_REFERENCE")
            unsupported += 1
            continue
        if finding.kind == "observed_measurement":
            numeric_total += 1
            match = next(
                (
                    m
                    for m in context.measurements
                    if m.reference_id in finding.measurement_refs
                    and insensitive(m.metric_code) == insensitive(finding.metric_code or "")
                    and insensitive(m.value) == insensitive(finding.metric_value or "")
                    and insensitive(m.unit) == insensitive(finding.metric_unit or "")
                ),
                None,
            )
            if match is None:
                reasons.append("NUMERIC_MISMATCH")
                unsupported += 1
            else:
                numeric_ok += 1
                supported += 1
        elif finding.kind == "general_background":
            text = finding.text.lower()
            if any(marker in text for marker in ALLOWED_GENERAL_BACKGROUND) or not finding.passage_refs:
                supported += 1
            else:
                reasons.append("UNSUPPORTED_NOVEL_PROSE")
                unsupported += 1
        elif finding.kind == "gap":
            supported += 1
        else:
            reasons.append("UNSUPPORTED_NOVEL_PROSE")
            unsupported += 1
        hits = _prohibited(finding.text)
        if hits:
            reasons.append("PROHIBITED_CLAIM")
            prohibited += 1
            unsupported += 1
    if prohibited:
        verdict: Literal["published", "withheld_insufficient_evidence", "failed_grounding"] = (
            "failed_grounding"
        )
    elif reasons or unsupported:
        verdict = "failed_grounding"
    elif not report.findings or (numeric_total and not numeric_ok):
        verdict = "withheld_insufficient_evidence"
        reasons.append("ABSTAIN_CRITICAL_INSUFFICIENT")
    else:
        verdict = "published"
    ordered = tuple(dict.fromkeys(reasons))
    if verdict == "published":
        action = "publish_visible_template"
    elif verdict == "withheld_insufficient_evidence":
        action = "narrow_scope_or_request_curator_review"
    else:
        action = "reject_candidate_do_not_publish_remnant"
    _ = measured_values
    return GroundingReport(
        interpretation_snapshot_id=report.context_snapshot_id,
        context_snapshot_id=report.context_snapshot_id,
        verdict=verdict,
        reason_codes=ordered,
        numeric_statements=numeric_total,
        numeric_matched=numeric_ok,
        supported_claims=supported,
        unsupported_claims=unsupported,
        prohibited_critical=prohibited,
        next_action=action,
    )


class GroundingValidator:
    """Real fail-closed gate replacing the unavailable-validator placeholder."""

    version: str = GATE_VERSION

    def validate(self, result: PrivateResult) -> None:
        raise ProviderFailure("GROUNDING_VALIDATOR_UNAVAILABLE")


def validate_private_candidate(
    context: InterpretationContext, candidate_findings: list[dict]
) -> GroundingReport:
    draft = InterpretationReport.model_validate(
        {
            "context_snapshot_id": context.snapshot_id,
            "context_hash": context.context_hash,
            "snapshot_hash": context.snapshot_hash,
            "execution_mode": "external_candidate_private",
            "summary": "Private candidate pending grounding review.",
            "findings": candidate_findings,
            "visibility": "private_candidate",
            "next_action": "pending_grounding_review",
        }
    )
    report = validate_publication(context, draft)
    if report.verdict != "published":
        raise ProviderFailure("FAILED_GROUNDING")
    return report


def require_published(report: GroundingReport) -> None:
    if report.verdict != "published" or report.prohibited_critical:
        raise HTTPException(422)
