"""Deterministic template interpretation over frozen contexts; no LLM arithmetic."""

from uuid import UUID

from fastapi import HTTPException

from canceros.context_contracts import InterpretationContext
from canceros.contracts import Provenance
from canceros.interpretation_contracts import (
    InterpretationFinding,
    InterpretationInput,
    InterpretationReport,
)
from canceros.provider_contracts import ExportMeasurement, ProviderInput, local_summary
from canceros.provider_gateway import ClosedOutputValidator, PrivateResult

TEMPLATE_VERSION: str = "interpretation-template/1"


def _finding_for_measurement(context: InterpretationContext, reference_id: UUID):
    member = next(m for m in context.measurements if m.reference_id == reference_id)
    return InterpretationFinding(
        kind="observed_measurement",
        text=f"Retained {member.metric_code} value {member.value} {member.unit} "
        f"(member time basis {member.member_time}).",
        measurement_refs=(member.reference_id,),
        metric_code=member.metric_code,
        metric_value=member.value,
        metric_unit=member.unit,
    )


def render_template(context: InterpretationContext) -> InterpretationReport:
    findings: list[InterpretationFinding] = []
    for member in context.measurements:
        findings.append(_finding_for_measurement(context, member.reference_id))
        if len(findings) >= 20:
            break
    for passage in context.passages:
        if len(findings) >= 20:
            break
        findings.append(
            InterpretationFinding(
                kind="general_background",
                text=f"Unreviewed general research passage retained for background only "
                f"(locator {passage.locator}).",
                passage_refs=(passage.passage_id,),
            )
        )
    for reason in list(context.missing_modalities)[:5]:
        if len(findings) >= 20:
            break
        findings.append(
            InterpretationFinding(kind="gap", text=f"Missing or unavailable: {reason}.")
        )
    if not findings:
        findings.append(
            InterpretationFinding(
                kind="gap",
                text="No verified measurements or eligible passages in this context; "
                "narrow the scope or request curator review.",
            )
        )
    measured = len(context.measurements)
    return InterpretationReport(
        context_snapshot_id=context.snapshot_id,
        context_hash=context.context_hash,
        snapshot_hash=context.snapshot_hash,
        execution_mode="rule_based_summary",
        summary=f"Rule-based summary of {measured} retained measurements, "
        f"{len(context.assertions)} unverified assertions and "
        f"{len(context.passages)} unreviewed passages.",
        findings=tuple(findings),
        uncertainties=tuple(context.conflicts[:5]) or ("No recorded conflicts.",),
        visibility="visible_template",
        next_action="proceed_to_bounded_generation_review"
        if context.next_action == "proceed_to_bounded_generation_review"
        else context.next_action,
    )


def _export_code(value: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in "_.-" else "_" for c in value.strip())
    return (cleaned[:64] or "unspecified").strip(".-") or "unspecified"


def export_input(context: InterpretationContext) -> ProviderInput:
    return ProviderInput(
        purpose=context.purpose,
        input_snapshot_hash=context.snapshot_hash,
        measurements=tuple(
            ExportMeasurement(
                reference_id=m.reference_id,
                metric_code=_export_code(m.metric_code),
                value=m.value,
                unit=_export_code(m.unit),
                provenance=Provenance.SYNTHETIC_GENERATED,
            )
            for m in context.measurements
        ),
        missingness=tuple(list(dict.fromkeys(_export_code(r) for r in context.missing_modalities))[:100]),
        evidence_ids=tuple(g.passage_id for g in context.passages),
    )


def build_interpretation(
    context: InterpretationContext, value: InterpretationInput
) -> InterpretationReport:
    if value.context_snapshot_id != context.snapshot_id:
        raise HTTPException(409)
    if value.expected_context_hash is not None and value.expected_context_hash != context.context_hash:
        raise HTTPException(409)
    if value.mode == "external_candidate":
        raise HTTPException(409)
    return render_template(context)


def describe_private_candidate(result: PrivateResult) -> dict:
    ClosedOutputValidator().validate(result)
    raise AssertionError("unreachable")


def template_summary_text(context: InterpretationContext) -> str:
    return local_summary(export_input(context)).summary
