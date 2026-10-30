"""Scope-aware event/knowledge-time retrieval and nominal intervals, without value filling."""

import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from canceros.clinical_contracts import ClinicalRecord, ClinicalTime, ExactResult, NumericResult
from canceros.clinical_validation import UNITS, decimal_text
from canceros.contracts import (
    Availability,
    Context,
    Contract,
    DecimalString,
    Hash,
    MissingReason,
    Provenance,
    Quantity,
    TimeReference,
)
from canceros.physical_measurements import CalculationDecimal
from canceros.simulation_contracts import GeneratedEvent

MeasurementBasis = Literal[
    "source_record", "mask_realized", "simulated_target_no_mask_realization", "baseline_reference"
]


class TimelineScope(Contract):
    mode: Literal["observed", "source_fixture", "simulation"]
    data_revision: Annotated[int, Field(strict=True, ge=1)]
    branch_id: UUID | None = None
    run_id: UUID | None = None

    @model_validator(mode="after")
    def exact_scope(self):
        if self.mode == "simulation":
            if self.branch_id is None or self.run_id is None:
                raise ValueError("Simulation timeline requires exact branch and run")
        elif self.branch_id is not None or self.run_id is not None:
            raise ValueError("Unbranched source timeline cannot request a simulation run")
        return self


class TimelinePoint(Contract):
    id: UUID
    patient_id: UUID
    time: ClinicalTime
    recorded_at: AwareDatetime
    revision: Annotated[int, Field(strict=True, ge=1)]
    origin: Provenance
    context: Context
    modality: Annotated[str, Field(min_length=1, max_length=80)]
    concept: Annotated[str, Field(min_length=1, max_length=100)]
    numeric_result: NumericResult | None = None
    # Missing-result unit is dictionary-definition metadata, never an inferred recorded value.
    canonical_unit: Annotated[str, Field(min_length=1, max_length=32)] | None = None
    exact_value: CalculationDecimal | None = None
    metric_definition: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    ordinal_value: DecimalString | None = None
    instrument: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    instrument_version: Annotated[str, Field(min_length=1, max_length=80)] | None = None
    symptom_presence: Literal["present", "absent", "unknown", "not_assessed"] | None = None
    availability: Availability
    missing_reason: MissingReason | None = None
    conflicts: Annotated[list[str], Field(max_length=32)] = []
    source_ids: Annotated[list[UUID], Field(max_length=64)]
    source_hash: Hash
    state_ids: Annotated[list[UUID], Field(max_length=64)] = []
    geometry_result_id: UUID | None = None
    lesion_id: UUID | None = None
    measurement_basis: MeasurementBasis = "source_record"
    method_version: Annotated[str, Field(min_length=1, max_length=200)]
    summary: Annotated[str, Field(max_length=2000)] | None = None
    historical_context: bool = False
    branch_id: UUID | None = None
    run_id: UUID | None = None
    supersedes_id: UUID | None = None

    @model_validator(mode="after")
    def origin_and_membership(self):
        if (self.branch_id is None) != (self.run_id is None):
            raise ValueError("Point must preserve both branch and run identity")
        if self.context == Context.OBSERVED and (
            self.origin not in (Provenance.REAL_OBSERVED, Provenance.REAL_DERIVED)
            or self.time.reference.time_domain == "simulation"
        ):
            raise ValueError("Synthetic events cannot enter observed context")
        if self.context == Context.SYNTHETIC and self.origin in (
            Provenance.REAL_OBSERVED,
            Provenance.REAL_DERIVED,
        ):
            raise ValueError("Synthetic point cannot claim real observation origin")
        if self.ordinal_value is not None and (
            not self.instrument or not self.instrument_version or self.numeric_result is not None
        ):
            raise ValueError(
                "Ordinal severity requires its versioned instrument and separate representation"
            )
        if self.measurement_basis == "baseline_reference" and not self.historical_context:
            raise ValueError("Shared baseline reference must be marked historical context")
        if self.exact_value is not None and (
            self.numeric_result is None or self.numeric_result.form != "exact"
        ):
            raise ValueError(
                "An exact calculation cannot replace a missing or censored observation"
            )
        if self.canonical_unit is not None and self.numeric_result is not None:
            result = self.numeric_result
            actual_unit = (
                result.quantity.unit
                if result.form == "exact"
                else result.threshold.unit
                if result.form == "censored"
                else None
            )
            if actual_unit is not None and actual_unit != self.canonical_unit:
                raise ValueError("Canonical unit differs from the canonical numeric result")
        return self


class TimelineWindow(Contract):
    scope: TimelineScope
    event_cutoff: TimeReference | None = None
    knowledge_as_of: AwareDatetime
    event_cutoff_shift_basis: Annotated[str, Field(min_length=1, max_length=200)] | None = None


class FeatureSeries(Contract):
    concept: str
    unit: str | None
    method_version: str
    metric_definition: str | None = None
    lesion_id: UUID | None
    instrument: str | None
    instrument_version: str | None
    time_partition: str
    ordered_point_ids: list[UUID]
    interval_days: list[DecimalString]
    usable_count: int
    missing_count: int
    censored_count: int
    conflict_point_ids: list[UUID]
    latest_available_id: UUID | None
    age_days: DecimalString | None
    interval_semantics: Literal["nominal_source_time_no_imputation"] = (
        "nominal_source_time_no_imputation"
    )


class TemporalFeatures(Contract):
    version: Literal["temporal-features/1"] = "temporal-features/1"
    scope: TimelineScope
    series: list[FeatureSeries]
    selected_point_ids: list[UUID]
    unresolved_point_ids: list[UUID]
    treatment_point_ids: list[UUID]


def _partition(reference: TimeReference, shift_basis: str | None) -> str | None:
    if reference.basis == "unknown":
        return None
    if reference.time_domain == "source_shifted" and not shift_basis:
        return None
    anchor = (
        [str(reference.timeline_origin_id), str(reference.anchor_state_id)]
        if reference.basis == "relative_day"
        else []
    )
    return json.dumps(
        [
            reference.time_domain,
            reference.basis,
            anchor,
            shift_basis if reference.time_domain == "source_shifted" else None,
        ],
        separators=(",", ":"),
    )


def _position(reference: TimeReference) -> Decimal:
    if reference.basis == "relative_day":
        return Decimal(reference.value)
    if reference.basis == "date":
        return Decimal(reference.value.toordinal())
    if reference.basis == "timestamp":
        value = reference.value.astimezone(timezone.utc)
        return (
            Decimal(value.toordinal())
            + Decimal(value.hour * 3600 + value.minute * 60 + value.second) / Decimal(86400)
            + Decimal(value.microsecond) / Decimal(86400000000)
        )
    raise ValueError("Unknown event time has no numerical position")


def _matches(point: TimelinePoint, scope: TimelineScope) -> bool:
    if point.revision > scope.data_revision:
        return False
    if scope.mode == "simulation":
        if (point.branch_id, point.run_id) != (scope.branch_id, scope.run_id):
            return False
        if point.context == Context.SYNTHETIC:
            return point.origin == Provenance.SYNTHETIC_GENERATED
        return point.measurement_basis == "baseline_reference" and point.historical_context
    if point.branch_id is not None or point.run_id is not None:
        return False
    if scope.mode == "observed":
        return point.context == Context.OBSERVED and point.origin in (
            Provenance.REAL_OBSERVED,
            Provenance.REAL_DERIVED,
        )
    return point.context == Context.SYNTHETIC and point.origin == Provenance.SYNTHETIC_GENERATED


def _comparable_cutoff(point: TimelinePoint, window: TimelineWindow) -> bool:
    return (
        window.event_cutoff is not None
        and _partition(point.time.reference, point.time.date_shift_basis)
        == _partition(window.event_cutoff, window.event_cutoff_shift_basis)
        and _partition(point.time.reference, point.time.date_shift_basis) is not None
    )


def select_window(points: list[TimelinePoint], window: TimelineWindow) -> list[TimelinePoint]:
    with localcontext() as context:
        context.prec = 50
        window = TimelineWindow.model_validate_json(window.model_dump_json())
        points = [TimelinePoint.model_validate_json(point.model_dump_json()) for point in points]
        if len({point.patient_id for point in points}) > 1 or len(
            {point.id for point in points}
        ) != len(points):
            raise ValueError("Timeline input must have unique points for one authorized patient")
        selected = [
            point
            for point in points
            if _matches(point, window.scope)
            and point.recorded_at <= window.knowledge_as_of
            and (
                window.event_cutoff is None
                or not _comparable_cutoff(point, window)
                or _position(point.time.reference) <= _position(window.event_cutoff)
            )
        ]
        return sorted(
            selected,
            key=lambda point: (
                _partition(point.time.reference, point.time.date_shift_basis) or "~unresolved",
                _position(point.time.reference)
                if point.time.reference.basis != "unknown"
                else Decimal(0),
                str(point.id),
            ),
        )


def _day_text(value: Decimal) -> str:
    return decimal_text(value.quantize(Decimal("0.000000001")))


def _unit(point: TimelinePoint) -> str | None:
    if point.canonical_unit is not None:
        return point.canonical_unit
    result = point.numeric_result
    if result is not None and result.form == "exact":
        return result.quantity.unit
    if result is not None and result.form == "censored":
        return result.threshold.unit
    if point.concept in UNITS:
        return next(iter(UNITS[point.concept].values()))[0]
    return "mm3" if point.concept == "numerical_region_volume" else None


def extract_features(points: list[TimelinePoint], window: TimelineWindow) -> TemporalFeatures:
    with localcontext() as context:
        context.prec = 50
        selected = select_window(points, window)
        unresolved = []
        groups = defaultdict(list)
        treatments = []
        for point in selected:
            partition = _partition(point.time.reference, point.time.date_shift_basis)
            if partition is None or (
                window.event_cutoff is not None and not _comparable_cutoff(point, window)
            ):
                unresolved.append(point.id)
                continue
            if point.modality == "treatment":
                treatments.append(point.id)
            if (
                point.numeric_result is None
                and point.ordinal_value is None
                and point.modality not in ("imaging", "laboratory", "vital", "symptom")
            ):
                continue
            unit = _unit(point)
            key = (
                partition,
                point.concept,
                unit,
                point.method_version,
                point.lesion_id,
                point.instrument,
                point.instrument_version,
                point.metric_definition,
            )
            groups[key].append(point)
        series = []
        for key, members in sorted(groups.items(), key=lambda item: str(item[0])):
            members.sort(key=lambda point: (_position(point.time.reference), str(point.id)))
            positions = [_position(point.time.reference) for point in members]
            ties = {position for position in positions if positions.count(position) > 1}
            conflicts = [
                point.id
                for point in members
                if point.conflicts or _position(point.time.reference) in ties
            ]
            usable = [
                point
                for point in members
                if point.availability == Availability.AVAILABLE
                and point.id not in conflicts
                and (
                    (point.numeric_result is not None and point.numeric_result.form == "exact")
                    or point.ordinal_value is not None
                )
            ]
            latest = usable[-1] if usable else None
            if members[-1].id in conflicts:
                latest = None
            age = None
            if (
                latest is not None
                and window.event_cutoff is not None
                and _comparable_cutoff(latest, window)
            ):
                age = _day_text(_position(window.event_cutoff) - _position(latest.time.reference))
            series.append(
                FeatureSeries(
                    time_partition=key[0],
                    concept=key[1],
                    unit=key[2],
                    method_version=key[3],
                    lesion_id=key[4],
                    instrument=key[5],
                    instrument_version=key[6],
                    metric_definition=key[7],
                    ordered_point_ids=[point.id for point in members],
                    interval_days=[_day_text(b - a) for a, b in zip(positions, positions[1:])],
                    usable_count=len(usable),
                    missing_count=sum(
                        point.availability != Availability.AVAILABLE
                        or point.missing_reason is not None
                        or (
                            point.numeric_result is not None
                            and point.numeric_result.form == "missing"
                        )
                        or (
                            point.modality == "symptom"
                            and point.ordinal_value is None
                            and point.numeric_result is None
                        )
                        for point in members
                    ),
                    censored_count=sum(
                        point.numeric_result is not None and point.numeric_result.form == "censored"
                        for point in members
                    ),
                    conflict_point_ids=conflicts,
                    latest_available_id=latest.id if latest else None,
                    age_days=age,
                )
            )
        return TemporalFeatures(
            scope=window.scope,
            series=series,
            selected_point_ids=[point.id for point in selected],
            unresolved_point_ids=unresolved,
            treatment_point_ids=treatments,
        )


def from_clinical_record(
    record: ClinicalRecord,
    recorded_at: datetime,
    revision: int,
    source_hash: str,
    supersedes_id: UUID | None = None,
) -> TimelinePoint:
    item = record.item
    values = dict(
        id=record.id,
        patient_id=record.patient_id,
        time=item.time,
        recorded_at=recorded_at,
        revision=revision,
        origin=record.origin,
        context=record.context,
        modality=item.kind,
        concept=item.concept if item.kind != "note" else "source_note",
        availability=record.availability,
        source_ids=[record.id, item.source_locator_id],
        source_hash=source_hash,
        method_version=item.dictionary_version,
        supersedes_id=supersedes_id,
    )
    if item.kind in ("laboratory", "vital"):
        result = (
            record.numeric_normalization.canonical_result
            if record.numeric_normalization is not None
            else item.result
        )
        values.update(
            numeric_result=result,
            method_version=record.numeric_normalization.conversion_rule_version
            if record.numeric_normalization
            else item.dictionary_version,
            missing_reason=result.missing_reason if result.form == "missing" else None,
            exact_value=result.quantity.value if result.form == "exact" else None,
            canonical_unit=result.quantity.unit
            if result.form == "exact"
            else result.threshold.unit
            if result.form == "censored"
            else next(iter(UNITS[item.concept].values()))[0]
            if item.concept in UNITS
            else None,
        )
    elif item.kind == "symptom":
        values.update(
            ordinal_value=item.severity,
            instrument=item.instrument,
            instrument_version=item.instrument_version,
            symptom_presence=item.presence,
        )
    elif item.kind == "treatment":
        values.update(summary=item.event_type + "; " + item.exposure_status)
    return TimelinePoint.model_validate(values)


def from_generated_event(
    event: GeneratedEvent,
    patient_id: UUID,
    recorded_at: datetime,
    revision: int,
    source_hash: str,
    *,
    timeline_origin_id: UUID,
    state_ids: list[UUID] | None = None,
    geometry_result_id: UUID | None = None,
    lesion_id: UUID | None = None,
    measurement_basis: MeasurementBasis = "simulated_target_no_mask_realization",
) -> TimelinePoint:
    value = event.value
    values = dict(
        id=event.event_id,
        patient_id=patient_id,
        recorded_at=recorded_at,
        revision=revision,
        time=ClinicalTime.model_validate(
            {
                "reference": {
                    "basis": "relative_day",
                    "value": event.relative_day,
                    "time_domain": "simulation",
                    "timeline_origin_id": timeline_origin_id,
                },
                "precision": "relative_day",
            }
        ),
        origin=event.origin,
        context=Context.SYNTHETIC,
        modality=event.modality,
        concept=value.code
        if value.kind == "quantity"
        else value.concept
        if value.kind == "symptom"
        else value.channel or "unidentified_missing_channel"
        if value.kind == "missing"
        else value.affected_concept
        if value.kind == "adverse_event"
        else "hypothetical_exposure"
        if value.kind == "treatment"
        else "research_note",
        availability=Availability.UNAVAILABLE
        if value.kind == "missing"
        else Availability.AVAILABLE,
        source_ids=[event.event_id],
        source_hash=source_hash,
        state_ids=state_ids or [],
        geometry_result_id=geometry_result_id,
        lesion_id=lesion_id,
        measurement_basis=measurement_basis,
        method_version="clinical-generation/1",
        branch_id=event.branch_id,
        run_id=event.run_id,
    )
    if value.kind == "quantity":
        if value.canonical_value is not None:
            number, unit = value.canonical_value, value.canonical_unit
            assert unit is not None
        elif value.code in UNITS:
            unit, factor = UNITS[value.code][value.unit]
            number = decimal_text(Decimal(value.value) * factor)
        else:
            number, unit = value.value, value.unit
        values.update(
            numeric_result=ExactResult(form="exact", quantity=Quantity(value=number, unit=unit)),
            exact_value=number,
            canonical_unit=unit,
            metric_definition="numerical_region_volume" if event.modality == "imaging" else None,
        )
    elif value.kind == "symptom":
        values.update(
            ordinal_value=str(value.rating),
            instrument="engineering_ordinal",
            instrument_version="1",
            symptom_presence=value.presence,
        )
    elif value.kind == "missing":
        values.update(missing_reason=value.reason)
        values.update(
            canonical_unit=next(iter(UNITS[value.channel].values()))[0]
            if value.channel in UNITS
            else "mm3"
            if value.channel == "numerical_region_volume"
            else None
        )
        if event.modality == "symptom":
            values.update(instrument="engineering_ordinal", instrument_version="1")
    elif value.kind == "treatment":
        values.update(summary=value.action + "; " + value.assumption)
    elif value.kind == "adverse_event":
        values.update(
            summary="Configured clinical condition change; ungraded; hypothetical association, not causal"
        )
    else:
        values.update(summary=value.text)
    return TimelinePoint.model_validate(values)
