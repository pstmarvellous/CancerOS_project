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

TEMPLATE_VERSION: str = "interpretation-template/2"


def _finding_for_measurement(context: InterpretationContext, reference_id: UUID):
    member = next(m for m in context.measurements if m.reference_id == reference_id)
    synthetic = member.origin == "SYNTHETIC_GENERATED"
    text = (
        f"At {member.member_time}, {'the modeled' if synthetic else 'the recorded'} "
        f"{member.metric_code} measures {member.value} {member.unit}."
    )
    if synthetic:
        text += " This is a hypothetical simulation for demonstration."
    return InterpretationFinding(
        kind="observed_measurement",
        text=text,
        measurement_refs=(member.reference_id,),
        metric_code=member.metric_code,
        metric_value=member.value,
        metric_unit=member.unit,
    )


def render_template(context: InterpretationContext) -> InterpretationReport:
    findings: list[InterpretationFinding] = []
    candidate_count = (
        len(context.measurements)
        + len(context.comparison_measurements)
        + len(context.passages)
        + len(context.missing_modalities)
    )
    for member in context.measurements:
        findings.append(_finding_for_measurement(context, member.reference_id))
        if len(findings) >= 20:
            break
    # Comparisons remain independently cited values. Do not invent arithmetic,
    # lesion correspondence, treatment effects or a clinical response category.
    for member in context.comparison_measurements:
        if len(findings) >= 20:
            break
        findings.append(
            InterpretationFinding(
                kind="observed_measurement",
                text=f"Selected comparison at {member.member_time}: "
                f"{member.metric_code} measures {member.value} {member.unit}. "
                + (
                    "Hypothetical simulation for demonstration."
                    if member.origin == "SYNTHETIC_GENERATED"
                    else "Recorded source value."
                ),
                measurement_refs=(member.reference_id,),
                metric_code=member.metric_code,
                metric_value=member.value,
                metric_unit=member.unit,
            )
        )
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
    for reason in context.missing_modalities:
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
    truncated = max(0, candidate_count - len(findings))
    limitations = list(InterpretationReport.model_fields["limitations"].default)
    if truncated:
        limitations.append(
            f"Template display limit: {truncated} eligible findings were omitted; "
            "inspect the complete context or narrow the scope. Comparisons and background may be omitted."
        )
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
        limitations=tuple(limitations),
        visibility="visible_template",
        next_action="narrow_scope_or_inspect_complete_context"
        if truncated
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
        missingness=tuple(
            list(dict.fromkeys(_export_code(r) for r in context.missing_modalities))[:100]
        ),
        evidence_ids=tuple(g.passage_id for g in context.passages),
    )


def build_interpretation(
    context: InterpretationContext, value: InterpretationInput
) -> InterpretationReport:
    if value.context_snapshot_id != context.snapshot_id:
        raise HTTPException(409)
    if (
        value.expected_context_hash is not None
        and value.expected_context_hash != context.context_hash
    ):
        raise HTTPException(409)
    if value.mode == "external_candidate":
        raise HTTPException(409)
    return render_template(context)


def describe_private_candidate(result: PrivateResult) -> dict:
    ClosedOutputValidator().validate(result)
    raise AssertionError("unreachable")


def template_summary_text(context: InterpretationContext) -> str:
    return local_summary(export_input(context)).summary
