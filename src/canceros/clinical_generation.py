"""Materialize explicit synthetic clinical inputs; no inferred source tests or distributions."""

import json
from decimal import Decimal, localcontext
from typing import Annotated, Literal
from uuid import UUID, uuid5

from pydantic import Field, model_validator

from canceros.clinical_validation import UNITS, decimal_text
from canceros.contracts import Contract, DecimalString, Provenance
from canceros.sampling import SampledObservations, SamplingError, sample_observations
from canceros.simulation_contracts import (
    GeneratedAdverseEvent,
    GeneratedEvent,
    GeneratedMissing,
    GeneratedQuantity,
    GeneratedSymptom,
    GeneratedTreatment,
    SimulationConfig,
)
from canceros.simulation_plugins import PluginOutput, SimulationAdverseEvent

GENERATOR_VERSION: Literal["clinical-generation/1"] = "clinical-generation/1"


class ClinicalGenerationError(ValueError):
    """A bounded unsupported configuration or inconsistent explicit value blocks the batch."""


class GeneratedNote(Contract):
    note_id: UUID
    run_id: UUID
    branch_id: UUID
    relative_day: DecimalString
    evidence_event_ids: Annotated[list[UUID], Field(min_length=1, max_length=16)]
    text: Annotated[str, Field(strict=True, min_length=1, max_length=2000)]
    origin: Literal[Provenance.SYNTHETIC_GENERATED] = Provenance.SYNTHETIC_GENERATED


class ClinicalBatch(Contract):
    version: Literal["clinical-generation/1"] = GENERATOR_VERSION
    run_id: UUID
    branch_id: UUID
    events: Annotated[list[GeneratedEvent], Field(max_length=256)]
    notes: Annotated[list[GeneratedNote], Field(max_length=256)]
    adverse_events: Annotated[list[SimulationAdverseEvent], Field(max_length=16)] = []
    unmaterialized_slot_ids: Annotated[list[str], Field(max_length=64)] = []
    baseline_clinical_values: Literal["not_inferred_or_modified"] = "not_inferred_or_modified"
    sampling: SampledObservations | None = None
    imaging_measurement_basis: Literal["not_included", "simulated_target_no_mask_realization"] = (
        "not_included"
    )
    origin: Literal[Provenance.SYNTHETIC_GENERATED] = Provenance.SYNTHETIC_GENERATED

    @model_validator(mode="after")
    def scoped_graph(self):
        events = {event.event_id: event for event in self.events}
        if len(events) != len(self.events) or len({note.note_id for note in self.notes}) != len(
            self.notes
        ):
            raise ValueError("Clinical batch IDs must be unique")
        members: list[GeneratedEvent | GeneratedNote] = [*self.events, *self.notes]
        for member in members:
            if member.run_id != self.run_id or member.branch_id != self.branch_id:
                raise ValueError("Clinical batch member belongs to a different run or branch")
        for note in self.notes:
            if any(
                identifier not in events
                or Decimal(events[identifier].relative_day) != Decimal(note.relative_day)
                for identifier in note.evidence_event_ids
            ):
                raise ValueError(
                    "Research note evidence must belong to this batch and actual relative time"
                )
        return self


def _identifier(run_id: UUID, branch_id: UUID, slot_id: str, channel: str) -> UUID:
    return uuid5(
        run_id,
        json.dumps(
            [GENERATOR_VERSION, str(branch_id), slot_id, channel],
            ensure_ascii=True,
            separators=(",", ":"),
        ),
    )


def _note(event: GeneratedEvent) -> GeneratedNote:
    value = event.value
    if value.kind == "quantity":
        description = f"{value.code} {value.value} {value.unit} (canonical {value.canonical_value} {value.canonical_unit})"
    elif value.kind == "symptom":
        description = (
            f"{value.concept} {value.rating} {value.scale}; {value.presence}; "
            f"{value.negation}; {value.resolution_status}; hypothetical self report"
        )
    elif value.kind == "treatment":
        description = f"{value.action}; {value.category}; hypothetical assumption, no prescription"
    elif value.kind == "adverse_event":
        description = (
            f"{value.affected_concept}; configured onset day {value.onset_day}; "
            f"configured resolution {value.resolution_day or 'not configured'}; ungraded; "
            "hypothetical association, no causal attribution"
        )
    elif value.kind == "missing":
        description = f"{value.channel or 'configured channel'} missing: {value.reason}"
    else:
        raise ClinicalGenerationError("Unsupported note value kind")
    return GeneratedNote(
        note_id=uuid5(event.event_id, "clinical-generation/1:note"),
        run_id=event.run_id,
        branch_id=event.branch_id,
        relative_day=event.relative_day,
        evidence_event_ids=[event.event_id],
        text=f"Simulated research observation; no physician encounter or actual clinical test. Relative day {event.relative_day}: {description}.",
    )


def _concurrent_constraints(events: list[GeneratedEvent]) -> None:
    concurrent: dict[Decimal, dict[str, Decimal]] = {}
    for event in events:
        if event.value.kind != "quantity":
            continue
        value = event.value
        group = concurrent.setdefault(Decimal(event.relative_day), {})
        if value.code in group:
            raise ClinicalGenerationError(
                "Duplicate concurrent concept requires explicit reconciliation"
            )
        assert value.canonical_value is not None
        group[value.code] = Decimal(value.canonical_value)
    for group in concurrent.values():
        if "anc" in group and "wbc" in group and group["anc"] > group["wbc"]:
            raise ClinicalGenerationError("Concurrent canonical ANC cannot exceed WBC")
        if (
            "systolic_bp" in group
            and "diastolic_bp" in group
            and group["systolic_bp"] <= group["diastolic_bp"]
        ):
            raise ClinicalGenerationError(
                "Concurrent systolic pressure must exceed diastolic pressure"
            )


def generate_clinical(
    config: SimulationConfig, output: PluginOutput, run_id: UUID
) -> ClinicalBatch:
    config = SimulationConfig.model_validate_json(config.model_dump_json())
    output = PluginOutput.model_validate_json(output.model_dump_json())
    if config.treatment.category != "no_specific_assumption":
        raise ClinicalGenerationError("Specific treatment exposure rules remain unreviewed")
    if output.clinical_profile != config.clinical_profile or output.family not in (
        None,
        config.scenario.family,
    ):
        raise ClinicalGenerationError("Plugin output differs from frozen clinical configuration")
    condition = output.clinical_condition
    if config.scenario.family == "SC-05" and (
        condition is None
        or condition.parameters != config.sc05_parameters
        or condition.exposure_context != config.treatment
    ):
        raise ClinicalGenerationError("SC-05 clinical descriptor differs from frozen configuration")
    if config.scenario.family != "SC-05" and condition is not None:
        raise ClinicalGenerationError("Unexpected clinical-condition descriptor")
    try:
        sampling = sample_observations(config, output)
    except SamplingError as error:
        raise ClinicalGenerationError(str(error)) from error
    slots = {slot.slot_id: slot for slot in sampling.slots}
    samples = {(point.slot_id, point.channel): point for point in sampling.clinical_values}
    events: list[GeneratedEvent] = []

    def emit(slot_id, channel, value):
        slot = slots[slot_id]
        events.append(
            GeneratedEvent(
                event_id=_identifier(run_id, config.branch_id, slot_id, channel),
                run_id=run_id,
                branch_id=config.branch_id,
                slot_id=slot_id,
                relative_day=slot.relative_day,
                modality=slot.modality,
                value=value,
            )
        )

    for point in config.clinical_profile.points:
        sampled = samples[(point.slot_id, point.code)]
        if sampled.value is None:
            assert sampled.missing_reason is not None
            emit(
                point.slot_id,
                "quantity:" + point.code,
                GeneratedMissing(kind="missing", reason=sampled.missing_reason, channel=point.code),
            )
            continue
        if point.code not in UNITS or point.unit not in UNITS[point.code]:
            raise ClinicalGenerationError(
                "Configured clinical concept/unit definition is unavailable"
            )
        if point.code == "weight" and Decimal(sampled.value) <= 0:
            raise ClinicalGenerationError("Configured weight must be positive")
        unit, factor = UNITS[point.code][point.unit]
        with localcontext() as context:
            context.prec = 50
            canonical = decimal_text(Decimal(sampled.value) * factor)
        emit(
            point.slot_id,
            "quantity:" + point.code,
            GeneratedQuantity(
                kind="quantity",
                code=point.code,
                value=sampled.value,
                unit=point.unit,
                canonical_value=canonical,
                canonical_unit=unit,
                definition_version="canceros-local/1",
                generator_version=GENERATOR_VERSION,
            ),
        )
    if condition is not None:
        previous: dict[str, str] = {}
        for symptom_point in sorted(
            condition.parameters.symptom_course,
            key=lambda point: (Decimal(slots[point.slot_id].relative_day), point.concept),
        ):
            sampled = samples[(symptom_point.slot_id, symptom_point.concept)]
            if sampled.value is None:
                assert sampled.missing_reason is not None
                emit(
                    symptom_point.slot_id,
                    "symptom:" + symptom_point.concept,
                    GeneratedMissing(
                        kind="missing", reason=sampled.missing_reason, channel=symptom_point.concept
                    ),
                )
                previous.pop(symptom_point.concept, None)
                continue
            rating = int(Decimal(sampled.value))
            presence: Literal["present", "absent"] = "present" if rating > 0 else "absent"
            resolution: Literal["present", "configured_resolution", "absent_no_previous_report"] = (
                "present"
                if presence == "present"
                else "configured_resolution"
                if previous.get(symptom_point.concept) == "present"
                else "absent_no_previous_report"
            )
            emit(
                symptom_point.slot_id,
                "symptom:" + symptom_point.concept,
                GeneratedSymptom(
                    kind="symptom",
                    concept=symptom_point.concept,
                    rating=rating,
                    presence=presence,
                    negation="affirmed" if presence == "present" else "negated",
                    resolution_status=resolution,
                ),
            )
            previous[symptom_point.concept] = presence
        for descriptor in condition.events:
            matches = [
                slot
                for slot in config.schedule.slots
                if slot.modality == "adverse_event"
                and Decimal(slot.relative_day) == Decimal(descriptor.onset_day)
            ]
            for slot in matches:
                emit(
                    slot.slot_id,
                    "adverse_event:" + descriptor.affected_concept,
                    GeneratedAdverseEvent(kind="adverse_event", **descriptor.model_dump()),
                )
    active_day: Decimal | None = None
    for event in config.treatment.events:
        day = Decimal(event.relative_day)
        if event.category == "hypothetical_exposure_start":
            if active_day is not None:
                raise ClinicalGenerationError(
                    "Hypothetical exposure start overlaps an active window"
                )
            active_day = day
        else:
            if active_day is None or day <= active_day:
                raise ClinicalGenerationError(
                    "Hypothetical exposure stop requires a strictly earlier start"
                )
            active_day = None
        matches = [
            slot
            for slot in config.schedule.slots
            if slot.modality == "treatment" and Decimal(slot.relative_day) == day
        ]
        if len(matches) != 1:
            raise ClinicalGenerationError(
                "Explicit treatment event requires a matching configured treatment slot"
            )
        emit(
            matches[0].slot_id,
            "treatment:" + event.event_id,
            GeneratedTreatment(
                kind="treatment",
                event_reference=event.event_id,
                action=event.category,
            ),
        )
    _concurrent_constraints(events)
    events.sort(
        key=lambda event: (Decimal(event.relative_day), event.modality, str(event.event_id))
    )
    materialized = {event.slot_id for event in events}
    return ClinicalBatch(
        run_id=run_id,
        branch_id=config.branch_id,
        events=events,
        notes=[_note(event) for event in events],
        adverse_events=condition.events if condition is not None else [],
        sampling=sampling,
        unmaterialized_slot_ids=[
            slot.slot_id
            for slot in config.schedule.slots
            if slot.modality != "imaging" and slot.slot_id not in materialized
        ],
    )


def materialize_measurement_only(
    config: SimulationConfig, output: PluginOutput, run_id: UUID
) -> ClinicalBatch:
    """Complete tabular imaging positions without claiming a mask-derived measurement."""
    if config.geometry_policy != "none":
        raise ClinicalGenerationError(
            "Target-only imaging materialization requires geometry policy none"
        )
    batch = generate_clinical(config, output, run_id)
    assert batch.sampling is not None
    events = batch.events.copy()
    for target in batch.sampling.tumor_targets:
        value: GeneratedMissing | GeneratedQuantity
        if target.target_mm3 is None:
            assert target.missing_reason is not None
            value = GeneratedMissing(
                kind="missing", reason=target.missing_reason, channel="numerical_region_volume"
            )
        else:
            value = GeneratedQuantity(
                kind="quantity",
                code="numerical_region_volume",
                value=target.target_mm3,
                unit="mm3",
                canonical_value=target.target_mm3,
                canonical_unit="mm3",
                definition_version="canceros-local/1",
                generator_version=GENERATOR_VERSION,
            )
        events.append(
            GeneratedEvent(
                event_id=_identifier(
                    run_id, config.branch_id, target.slot_id, "quantity:numerical_region_volume"
                ),
                branch_id=config.branch_id,
                run_id=run_id,
                slot_id=target.slot_id,
                relative_day=target.relative_day,
                modality="imaging",
                value=value,
            )
        )
    events.sort(
        key=lambda event: (Decimal(event.relative_day), event.modality, str(event.event_id))
    )
    data = batch.model_dump(mode="json")
    data.update(
        events=[event.model_dump(mode="json") for event in events],
        notes=[_note(event).model_dump(mode="json") for event in events],
        imaging_measurement_basis="simulated_target_no_mask_realization",
    )
    return ClinicalBatch.model_validate(data)
