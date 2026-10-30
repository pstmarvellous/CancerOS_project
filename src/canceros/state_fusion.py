"""Computed exact-membership research context; no store, imputation or clinical score."""

from decimal import Decimal, localcontext
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from canceros.clinical_contracts import ClinicalTime, ExactResult, MissingResult, NumericResult
from canceros.clinical_validation import UNITS
from canceros.contracts import (
    Availability,
    Context,
    Contract,
    DecimalString,
    Hash,
    Provenance,
    TimeReference,
)
from canceros.persistence import science_hash
from canceros.physical_measurements import CalculationDecimal
from canceros.temporal_trends import PointComparison
from canceros.twin_states import StateView

ConflictCategory = Literal[
    "NO_CONFLICT",
    "INCONSISTENT_UNITS",
    "INCONSISTENT_VALUES",
    "DATE_MISMATCH",
    "SOURCE_AMBIGUITY",
    "INCOMPATIBLE_MODALITIES",
    "INSUFFICIENT_DATA",
]


class FusionMember(Contract):
    id: UUID
    source_ids: list[UUID]
    source_hash: Hash
    modality: str
    concept: str
    time: ClinicalTime | None
    original_time: TimeReference | None = None
    role: Literal["current", "historical_context"]
    origin: Provenance
    context: Context
    availability: Availability = Availability.AVAILABLE
    numeric_result: NumericResult | None = None
    exact_value: CalculationDecimal | None = None
    metric_definition: str | None = None
    ordinal_value: DecimalString | None = None
    uncertainty: list[str] = Field(default_factory=list)
    primary_for_display: bool = False


class GroundedNoteAssertion(Contract):
    """Internal adapter input only; an assertion never becomes a structured measurement."""

    id: UUID
    patient_id: UUID
    branch_id: UUID
    note_record_id: UUID
    note_source_hash: Hash
    note_content_sha256: Hash
    target_member_id: UUID
    concept: str
    modality: str
    time: ClinicalTime
    result: NumericResult
    excerpt: Annotated[str, Field(min_length=1, max_length=1000)]
    origin: Provenance
    context: Context
    verification: Literal["unverified_extracted_assertion"] = "unverified_extracted_assertion"


class FusionConflict(Contract):
    category: ConflictCategory
    member_ids: list[UUID]
    reason: str
    primary_member_id: UUID | None = None
    next_action: str


class FusionBlock(Contract):
    title: Literal["Available", "Historical", "Missing", "Conflicting"]
    member_ids: list[UUID]
    reasons: list[str]
    next_action: str


class FusionReport(Contract):
    version: Literal["state-fusion/1"] = "state-fusion/1"
    canonical_state: StateView
    available_modalities: list[str]
    tumor_state: list[FusionMember]
    clinical_indicators: list[FusionMember]
    treatment_history: list[FusionMember]
    temporal_changes: list[PointComparison]
    note_assertions: list[GroundedNoteAssertion]
    conflicts: list[FusionConflict]
    blocks: list[FusionBlock]
    limitations: list[str]
    source_priority_policy: Literal[
        "usable_structured_member_over_unverified_assertion_display_only/1"
    ] = "usable_structured_member_over_unverified_assertion_display_only/1"


def _time(reference):
    return ClinicalTime(reference=reference, precision=reference.basis)


def _number(concept, result, exact_value=None):
    if result is None or result.form != "exact":
        return None
    quantity = result.quantity
    conversion = UNITS.get(concept, {}).get(quantity.unit)
    if concept in (
        "numerical_region_volume",
        "functional_region_volume",
        "anatomical_tumor_volume",
    ):
        conversion = {"mm3": ("mm3", Decimal(1)), "cm3": ("mm3", Decimal(1000))}.get(quantity.unit)
    if conversion is None:
        return (quantity.unit, Decimal(exact_value if exact_value is not None else quantity.value))
    with localcontext() as context:
        context.prec = 80
        return conversion[0], Decimal(
            exact_value if exact_value is not None else quantity.value
        ) * conversion[1]


def fuse_state(
    view: StateView,
    comparisons: list[PointComparison] | None = None,
    note_assertions: list[GroundedNoteAssertion] | None = None,
) -> FusionReport:
    """Project only validated owned members; the caller must authorize the canonical state.

    Comparisons must already have authorized endpoint provenance. This function additionally
    requires the selected state as the right endpoint and rejects context contamination.
    """
    snapshot = view.snapshot
    members: list[FusionMember] = []
    conflicts: list[FusionConflict] = []
    notes = {}

    def conflict(category, ids, reason, primary=None):
        conflicts.append(
            FusionConflict(
                category=category,
                member_ids=ids,
                reason=reason,
                primary_member_id=primary,
                next_action="Review the original members and their source-specific evidence",
            )
        )

    def add(member):
        if member.context != Context.SYNTHETIC or member.origin != Provenance.SYNTHETIC_GENERATED:
            raise ValueError("fusion_member_context_mismatch")
        if member.id in {existing.id for existing in members}:
            raise ValueError("fusion_duplicate_member")
        if member.time is None:
            conflict(
                "SOURCE_AMBIGUITY",
                [member.id],
                "Original shifted source time is retained but its documented shift basis is unavailable",
            )
            member = member.model_copy(update={"primary_for_display": False})
        elif member.role == "current" and member.time.reference != snapshot.time:
            conflict(
                "DATE_MISMATCH",
                [member.id],
                "Current member time differs from the selected state; no temporal substitution",
            )
            member = member.model_copy(update={"primary_for_display": False})
        members.append(member)

    for selected in snapshot.clinical_members:
        record, item = selected.record, selected.record.item
        if record.patient_id != snapshot.patient_id or selected.membership.record_id != record.id:
            raise ValueError("fusion_clinical_membership_mismatch")
        result = None
        if item.kind in ("laboratory", "vital"):
            result = (
                record.numeric_normalization.canonical_result
                if record.numeric_normalization
                else item.result
            )
        if item.kind == "note":
            notes[record.id] = selected
        add(
            FusionMember(
                id=record.id,
                source_ids=[record.id, item.source_locator_id],
                source_hash=selected.source_hash,
                modality=item.kind,
                concept=item.concept,
                time=item.time,
                role=selected.membership.role,
                origin=record.origin,
                context=record.context,
                availability=record.availability,
                numeric_result=result,
                exact_value=result.quantity.value if result and result.form == "exact" else None,
                ordinal_value=item.severity if item.kind == "symptom" else None,
                uncertainty=[
                    "certainty:" + item.certainty,
                    "quality:" + record.quality.value,
                    "availability:" + record.availability.value,
                    "scientific_review:" + record.scientific_review,
                ],
                primary_for_display=record.quality.value in ("pass", "not_applicable")
                and record.availability.value == "available"
                and item.certainty == "documented"
                and item.kind != "note"
                and (result is None or result.form == "exact"),
            )
        )
    for imaging in snapshot.imaging_members:
        measurement = imaging.measurement
        if imaging.membership.measurement_id != measurement.id:
            raise ValueError("fusion_imaging_membership_mismatch")
        values = measurement.values
        projected_result: NumericResult | None = (
            ExactResult.model_validate(
                {"form": "exact", "quantity": {"value": values.volume_mm3, "unit": "mm3"}}
            )
            if values.volume_mm3 is not None
            else None
        )
        reference = imaging.time
        time = (
            ClinicalTime.model_validate(
                {
                    "reference": reference.model_dump(mode="json"),
                    "precision": {
                        "relative_day": "relative_day",
                        "date": "day",
                        "timestamp": "second",
                        "unknown": "unknown",
                    }[reference.basis],
                }
            )
            if reference.time_domain != "source_shifted"
            else None
        )
        add(
            FusionMember(
                id=measurement.id,
                source_ids=[measurement.id] + [s.segmentation_id for s in measurement.selections],
                source_hash=imaging.source_hash,
                modality="imaging",
                concept=measurement.definition,
                metric_definition=measurement.definition,
                time=time,
                original_time=reference,
                role=imaging.membership.role,
                origin=Provenance.SYNTHETIC_GENERATED,
                context=Context.SYNTHETIC,
                availability=Availability.AVAILABLE
                if values.availability
                in ("available", "confirmed_absent", "configured_simulated_absent")
                and projected_result is not None
                else Availability.INVALID
                if values.availability == "invalid"
                else Availability.UNAVAILABLE,
                numeric_result=projected_result,
                exact_value=values.exact_volume_mm3,
                uncertainty=measurement.eligibility_blocks
                + ["scientific_review:pending", "measurement_availability:" + values.availability],
                primary_for_display=values.availability == "available"
                and not measurement.eligibility_blocks,
            )
        )
    for generated_geometry in snapshot.generated_geometry_members:
        geometry = generated_geometry.geometry
        if (
            geometry.branch_id != snapshot.branch_id
            or geometry.input_revision != snapshot.input_revision
        ):
            raise ValueError("fusion_geometry_membership_mismatch")
        realized_values = geometry.shape.realized_values
        projected_result = (
            ExactResult.model_validate(
                {"form": "exact", "quantity": {"value": realized_values.volume_mm3, "unit": "mm3"}}
            )
            if realized_values and realized_values.volume_mm3 is not None
            else None
        )
        add(
            FusionMember(
                id=geometry.id,
                source_ids=[geometry.id, geometry.baseline_measurement_id],
                source_hash=science_hash(geometry.model_dump(mode="json")),
                modality="imaging",
                concept=geometry.target_metric,
                metric_definition=geometry.target_metric,
                time=_time(geometry.time),
                role="current",
                origin=Provenance.SYNTHETIC_GENERATED,
                context=Context.SYNTHETIC,
                availability=Availability.AVAILABLE
                if geometry.status in ("ready", "zero") and projected_result is not None
                else Availability.UNAVAILABLE,
                numeric_result=projected_result,
                exact_value=realized_values.exact_volume_mm3 if realized_values else None,
                uncertainty=geometry.shape.reasons
                + [
                    "hypothetical_geometry_not_acquired_scan",
                    "anatomical_containment:not_established",
                    "scientific_review:pending",
                ],
                primary_for_display=geometry.status in ("ready", "zero")
                and projected_result is not None,
            )
        )
    for generated_clinical in snapshot.generated_clinical_members:
        for event in generated_clinical.events:
            if event.branch_id != snapshot.branch_id or event.run_id != generated_clinical.run_id:
                raise ValueError("fusion_generated_membership_mismatch")
            value = event.value
            concept = (
                value.code
                if value.kind == "quantity"
                else value.concept
                if value.kind == "symptom"
                else value.channel or "unidentified_missing_channel"
                if value.kind == "missing"
                else value.affected_concept
                if value.kind == "adverse_event"
                else "hypothetical_exposure"
                if value.kind == "treatment"
                else "research_note"
            )
            projected_result = (
                ExactResult.model_validate(
                    {
                        "form": "exact",
                        "quantity": {
                            "value": value.canonical_value or value.value,
                            "unit": value.canonical_unit or value.unit,
                        },
                    }
                )
                if value.kind == "quantity"
                else MissingResult(form="missing", missing_reason=value.reason)
                if value.kind == "missing"
                else None
            )
            reference = snapshot.time.model_copy(update={"value": event.relative_day})
            add(
                FusionMember(
                    id=event.event_id,
                    source_ids=[generated_clinical.batch_id, event.event_id],
                    source_hash=generated_clinical.source_hash,
                    modality=event.modality,
                    concept=concept,
                    time=_time(reference),
                    role="current",
                    origin=event.origin,
                    context=Context.SYNTHETIC,
                    availability=Availability.UNAVAILABLE
                    if value.kind == "missing"
                    else Availability.AVAILABLE,
                    numeric_result=projected_result,
                    exact_value=(value.canonical_value or value.value)
                    if value.kind == "quantity"
                    else None,
                    metric_definition=value.code
                    if value.kind == "quantity" and event.modality == "imaging"
                    else None,
                    ordinal_value=str(value.rating) if value.kind == "symptom" else None,
                    uncertainty=[
                        "configured_simulation_not_real_observation",
                        "scientific_review:pending",
                    ],
                    primary_for_display=value.kind not in ("missing", "text"),
                )
            )

    for index, member in enumerate(members):
        for other in members[index + 1 :]:
            if member.concept != other.concept or member.role != other.role:
                continue
            if member.time != other.time:
                continue  # Distinct visits are not contradictory values.
            ids = [member.id, other.id]
            if (
                member.modality != other.modality
                or member.metric_definition != other.metric_definition
            ):
                conflict(
                    "INCOMPATIBLE_MODALITIES",
                    ids,
                    "Matched concept has incompatible modality or metric meaning",
                )
            left, right = (
                _number(member.concept, member.numeric_result, member.exact_value),
                _number(other.concept, other.numeric_result, other.exact_value),
            )
            if left and right:
                if left[0] != right[0]:
                    conflict(
                        "INCONSISTENT_UNITS", ids, "No adopted conversion joins the source units"
                    )
                elif left[1] != right[1]:
                    conflict(
                        "INCONSISTENT_VALUES",
                        ids,
                        "Distinct structured assertions disagree; neither is averaged or selected",
                    )

    assertions = list(note_assertions or [])
    by_id = {member.id: member for member in members}
    for assertion in assertions:
        note, target = notes.get(assertion.note_record_id), by_id.get(assertion.target_member_id)
        if (
            note is None
            or target is None
            or assertion.patient_id != snapshot.patient_id
            or assertion.branch_id != snapshot.branch_id
            or assertion.note_source_hash != note.source_hash
            or note.record.item.kind != "note"
            or assertion.note_content_sha256 != note.record.item.content_sha256
            or assertion.origin != Provenance.SYNTHETIC_GENERATED
            or assertion.context != Context.SYNTHETIC
        ):
            raise ValueError("fusion_note_assertion_membership_mismatch")
        ids = [target.id, assertion.id]
        primary = target.id if target.primary_for_display else None
        if assertion.concept != target.concept:
            conflict(
                "SOURCE_AMBIGUITY",
                ids,
                "Assertion target concept is not the structured member concept",
                primary,
            )
        if assertion.modality != target.modality:
            conflict(
                "INCOMPATIBLE_MODALITIES",
                ids,
                "Assertion and structured target use incompatible modalities",
                primary,
            )
        if assertion.time != target.time:
            conflict(
                "DATE_MISMATCH",
                ids,
                "Assertion time does not match its target member time",
                primary,
            )
        left, right = (
            _number(target.concept, target.numeric_result, target.exact_value),
            _number(assertion.concept, assertion.result),
        )
        if left and right:
            if left[0] != right[0]:
                conflict(
                    "INCONSISTENT_UNITS",
                    ids,
                    "Assertion units have no adopted conversion to the structured target",
                    primary,
                )
            elif left[1] != right[1]:
                conflict(
                    "INCONSISTENT_VALUES",
                    ids,
                    "Unverified extracted assertion disagrees with the retained structured member",
                    primary,
                )
        else:
            conflict(
                "INSUFFICIENT_DATA",
                ids,
                "Missing or censored evidence cannot establish an exact numerical agreement",
                primary,
            )

    changes = list(comparisons or [])
    for change in changes:
        if (
            snapshot.id not in change.to_state_ids
            or change.context != Context.SYNTHETIC
            or change.origin != Provenance.SYNTHETIC_GENERATED
        ):
            raise ValueError("fusion_comparison_membership_mismatch")
    for reason in snapshot.conflicts:
        conflict("SOURCE_AMBIGUITY", [], "Canonical state conflict: " + reason)

    missing = list(snapshot.missing)
    for modality in ("imaging", "laboratory", "vital", "symptom", "treatment"):
        if not any(
            member.modality == modality
            and member.role == "current"
            and member.availability == Availability.AVAILABLE
            for member in members
        ):
            missing.append(modality + "_not_selected_as_current")
    missing.extend(["retrieved_evidence_unavailable", "predictive_model_output_unavailable"])
    if not assertions:
        missing.append("source_note_extraction_unavailable")
    if not changes:
        missing.append("temporal_comparisons_unavailable_for_selected_state")
    for member in members:
        if member.availability != Availability.AVAILABLE:
            missing.append(member.concept + ":" + member.availability.value)
        if member.numeric_result is not None and member.numeric_result.form == "missing":
            missing.append(member.concept + ":" + member.numeric_result.missing_reason)
    if missing:
        conflict(
            "INSUFFICIENT_DATA",
            [],
            "Missing sections remain unavailable; no carry-forward or synthetic supplementation",
        )
    conflicting_ids = {
        identifier
        for finding in conflicts
        if finding.category
        in ("INCONSISTENT_VALUES", "INCONSISTENT_UNITS", "INCOMPATIBLE_MODALITIES", "DATE_MISMATCH")
        and finding.primary_member_id is None
        for identifier in finding.member_ids
    }
    members = [
        member.model_copy(update={"primary_for_display": False})
        if member.id in conflicting_ids
        else member
        for member in members
    ]
    blocks = [
        FusionBlock(
            title="Available",
            member_ids=[
                m.id
                for m in members
                if m.role == "current" and m.availability == Availability.AVAILABLE
            ],
            reasons=["Exact selected-state members only"],
            next_action="Inspect original units, source time and provenance in the canonical state",
        ),
        FusionBlock(
            title="Historical",
            member_ids=[m.id for m in members if m.role == "historical_context"],
            reasons=view.restrictions
            + (
                ["Selected state is stale; immutable history remains visible"] if view.stale else []
            ),
            next_action="Use historical members as context; select a new explicit state for a current assessment",
        ),
        FusionBlock(
            title="Missing",
            member_ids=[],
            reasons=sorted(set(missing)),
            next_action="Acquire authorized missing observations or enable a separately validated evidence adapter",
        ),
        FusionBlock(
            title="Conflicting",
            member_ids=sorted({i for f in conflicts for i in f.member_ids}, key=str),
            reasons=[f.category + ": " + f.reason for f in conflicts],
            next_action="Review original sources and create an explicit corrected revision; preserve this state",
        ),
    ]
    return FusionReport(
        canonical_state=view,
        available_modalities=sorted(
            {m.modality for m in members if m.availability == Availability.AVAILABLE}
        ),
        tumor_state=[m for m in members if m.modality == "imaging"],
        clinical_indicators=[
            m for m in members if m.modality not in ("imaging", "treatment", "note")
        ],
        treatment_history=[m for m in members if m.modality == "treatment"],
        temporal_changes=changes,
        note_assertions=assertions,
        conflicts=conflicts,
        blocks=blocks,
        limitations=[
            "Engineering synthetic research context; authentic observed baseline and qualified scientific review remain unavailable",
            "Tumor measurements, symptom direction and other clinical indicators are independent dimensions; no diagnosis, response category, causal attribution or overall health score",
            "Source-specific uncertainty is retained separately from configured simulation variability; no predictive uncertainty is estimated",
            "Generated notes are not independently extracted source evidence",
            "No implicit carry-forward, learned fusion or LLM interpretation",
        ],
    )
