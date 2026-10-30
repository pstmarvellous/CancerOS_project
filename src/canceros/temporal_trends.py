"""Descriptive deterministic change over comparable evidence, without filling or clinical classes."""

import hashlib
import json
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from typing import Literal
from uuid import UUID

from pydantic import TypeAdapter

from canceros.clinical_contracts import ClinicalTime
from canceros.clinical_validation import UNITS, decimal_text
from canceros.contracts import Availability, Context, Contract, DecimalString, Provenance
from canceros.physical_measurements import CalculationDecimal
from canceros.temporal_timeline import (
    TimelinePoint,
    TimelineWindow,
    _partition,
    _position,
    _unit,
    extract_features,
    select_window,
)


class PointComparison(Contract):
    status: Literal["comparable", "not_comparable", "insufficient_data"]
    left_point_id: UUID | None
    right_point_id: UUID | None
    from_state_ids: list[UUID] = []
    to_state_ids: list[UUID] = []
    from_measurement_ids: list[UUID] = []
    to_measurement_ids: list[UUID] = []
    concept: str | None = None
    metric_code: str | None = None
    metric_definition: str | None = None
    unit: str | None = None
    lesion_id: UUID | None = None
    origin: Provenance | None = None
    context: Context | None = None
    comparison_context: Literal[
        "within_observed",
        "within_simulation",
        "source_fixture",
        "hypothetical_vs_observed",
        "incompatible_scopes",
    ]
    absolute_change: DecimalString | None = None
    percentage_change: DecimalString | None = None
    elapsed_days: DecimalString | None = None
    slope_per_day: DecimalString | None = None
    exact_absolute_change: CalculationDecimal | None = None
    exact_slope_per_day: CalculationDecimal | None = None
    change: Literal[
        "increased", "decreased", "unchanged_within_tolerance", "ordinal_direction", "unavailable"
    ] = "unavailable"
    ordinal_direction: Literal["increased", "decreased", "unchanged"] | None = None
    reason_codes: list[str]
    description: str
    method: Literal["later_minus_earlier/actual_elapsed_days"] = (
        "later_minus_earlier/actual_elapsed_days"
    )
    usable_count: int = 0


class TrendChartPoint(Contract):
    point_id: UUID
    x_elapsed_days: DecimalString | None
    y: DecimalString | None
    exact_value: CalculationDecimal | None
    label: str
    qualifier: str | None
    censored_threshold: CalculationDecimal | None = None
    reason_codes: list[str]
    time: ClinicalTime
    source_ids: list[UUID]
    origin: Provenance
    context: Context


class TrendSeries(Contract):
    key: str
    concept: str
    metric_definition: str | None
    unit: str | None
    lesion_id: UUID | None
    method_version: str
    origin: Provenance
    context: Context
    instrument: str | None
    instrument_version: str | None
    points: list[TrendChartPoint]
    segments: list[PointComparison]
    endpoint: PointComparison | None
    usable_count: int
    description: str


class TrendReport(Contract):
    version: Literal["temporal-trends/1"] = "temporal-trends/1"
    window: TimelineWindow
    tolerance: DecimalString
    series: list[TrendSeries]
    comparison: PointComparison | None
    interpretation: Literal["descriptive_only_no_clinical_significance_or_response_class"] = (
        "descriptive_only_no_clinical_significance_or_response_class"
    )


def _tolerance(value: str) -> Decimal:
    number = Decimal(TypeAdapter(DecimalString).validate_python(value))
    if number < 0:
        raise ValueError("Engineering numeric tolerance must be nonnegative")
    return number


def _wire(number: Decimal) -> str:
    if not number.is_finite() or abs(number) >= Decimal("1e15"):
        raise ValueError("Calculation exceeds bounded numeric wire representation")
    rounded = number.quantize(Decimal("0.000000001"), rounding=ROUND_HALF_EVEN)
    if abs(rounded) >= Decimal("1e15"):
        raise ValueError("Calculation exceeds bounded numeric wire representation")
    return decimal_text(rounded)


def _exact(number: Decimal) -> str | None:
    value = decimal_text(number)
    return value if len(value) <= 180 else None


def _normalized(point: TimelinePoint) -> tuple[Decimal | None, str | None]:
    unit = _unit(point)
    result = point.numeric_result
    if result is None or result.form != "exact":
        if point.concept in UNITS and unit in UNITS[point.concept]:
            unit = UNITS[point.concept][unit][0]
        elif point.modality == "imaging" and unit in ("mm3", "cm3"):
            unit = "mm3"
        return None, unit
    value = Decimal(point.exact_value if point.exact_value is not None else result.quantity.value)
    if point.concept in UNITS and unit in UNITS[point.concept]:
        canonical, factor = UNITS[point.concept][unit]
        return value * factor, canonical
    if point.modality == "imaging" and unit in ("mm3", "cm3"):
        return value * (Decimal(1000) if unit == "cm3" else Decimal(1)), "mm3"
    raise ValueError("No supported unit conversion is defined for this numeric concept")


def _context(left: TimelinePoint, right: TimelinePoint):
    if left.context != right.context:
        return "hypothetical_vs_observed"
    if left.context == Context.OBSERVED:
        return "within_observed"
    if left.branch_id is None and right.branch_id is None:
        return "source_fixture"
    if (left.branch_id, left.run_id) == (right.branch_id, right.run_id):
        return "within_simulation"
    return "incompatible_scopes"


def _base(left, right):
    return dict(
        left_point_id=left.id,
        right_point_id=right.id,
        from_state_ids=left.state_ids,
        to_state_ids=right.state_ids,
        from_measurement_ids=left.source_ids,
        to_measurement_ids=right.source_ids,
        concept=left.concept,
        metric_code=left.concept,
        metric_definition=left.metric_definition,
        lesion_id=left.lesion_id,
        origin=left.origin if left.origin == right.origin else None,
        context=left.context if left.context == right.context else None,
        comparison_context=_context(left, right),
    )


def _compare(left, right, tolerance, conflicts):
    base = _base(left, right)
    reasons = []
    for field, code in (
        ("patient_id", "PATIENT_MISMATCH"),
        ("concept", "METRIC_MISMATCH"),
        ("metric_definition", "MASK_METRIC_MISMATCH"),
        ("lesion_id", "LESION_MISMATCH"),
        ("method_version", "METHOD_MISMATCH"),
        ("origin", "ORIGIN_MISMATCH"),
    ):
        if getattr(left, field) != getattr(right, field):
            reasons.append(code)
    if base["comparison_context"] == "hypothetical_vs_observed":
        reasons.append("BASELINE_EVIDENCE_MISSING")
    elif base["comparison_context"] == "incompatible_scopes":
        reasons.append("BRANCH_RUN_MISMATCH")
    if any(
        point.method_version.strip().lower() in ("unknown", "not_recorded", "unavailable")
        for point in (left, right)
    ):
        reasons.append("METHOD_UNKNOWN")
    if any(
        point.modality == "imaging" and point.metric_definition is None for point in (left, right)
    ):
        reasons.append("MEASUREMENT_DEFINITION_UNKNOWN")
    partition = _partition(left.time.reference, left.time.date_shift_basis)
    if partition is None or partition != _partition(
        right.time.reference, right.time.date_shift_basis
    ):
        reasons.append("TIME_DOMAIN_OR_ANCHOR_MISMATCH")
    elif _position(right.time.reference) <= _position(left.time.reference):
        reasons.append("STRICTLY_LATER_TIME_REQUIRED")
    if left.conflicts or right.conflicts or left.id in conflicts or right.id in conflicts:
        reasons.append("UNRESOLVED_SAME_TIME_CONFLICT")
    if (
        left.availability != Availability.AVAILABLE
        or right.availability != Availability.AVAILABLE
        or left.missing_reason
        or right.missing_reason
    ):
        reasons.append("MISSING_OR_UNAVAILABLE_VALUE")
    if left.ordinal_value is not None or right.ordinal_value is not None:
        if (left.instrument, left.instrument_version) != (
            right.instrument,
            right.instrument_version,
        ):
            reasons.append("INSTRUMENT_MISMATCH")
        direction: Literal["increased", "decreased", "unchanged"] | None = None
        if not reasons and left.ordinal_value is not None and right.ordinal_value is not None:
            ordinal_before, ordinal_after = (
                Decimal(left.ordinal_value),
                Decimal(right.ordinal_value),
            )
            direction = (
                "increased"
                if ordinal_after > ordinal_before
                else "decreased"
                if ordinal_after < ordinal_before
                else "unchanged"
            )
        return PointComparison(
            **base,
            status="not_comparable",
            change="ordinal_direction" if direction else "unavailable",
            ordinal_direction=direction,
            reason_codes=[*reasons, "ORDINAL_INSTRUMENT_NO_RATIO_ARITHMETIC"],
            description=f"Internal ordinal rating {direction}; no interval or ratio arithmetic."
            if direction
            else "Ordinal comparison unavailable; no interval or ratio arithmetic.",
        )
    if any(
        point.numeric_result is None or point.numeric_result.form == "missing"
        for point in (left, right)
    ):
        reasons.append("MISSING_NUMERIC_VALUE")
    if any(
        point.numeric_result is not None and point.numeric_result.form == "censored"
        for point in (left, right)
    ):
        reasons.append("CENSORED_VALUE_NOT_EXACT")
    try:
        before, before_unit = _normalized(left)
        after, after_unit = _normalized(right)
        if before_unit != after_unit:
            reasons.append("UNIT_DIMENSION_MISMATCH")
    except ValueError:
        before = after = None
        before_unit = None
        reasons.append("UNSUPPORTED_UNIT")
    if reasons or before is None or after is None:
        return PointComparison(
            **base,
            unit=before_unit,
            status="insufficient_data"
            if "MISSING_NUMERIC_VALUE" in reasons or "MISSING_OR_UNAVAILABLE_VALUE" in reasons
            else "not_comparable",
            reason_codes=reasons or ["MISSING_NUMERIC_VALUE"],
            description="Comparison unavailable: " + "; ".join(reasons),
        )
    elapsed = _position(right.time.reference) - _position(left.time.reference)
    delta = after - before
    slope = delta / elapsed
    try:
        absolute, elapsed_text, slope_text = _wire(delta), _wire(elapsed), _wire(slope)
    except ValueError:
        return PointComparison(
            **base,
            unit=before_unit,
            status="not_comparable",
            reason_codes=["COMPUTATION_OUT_OF_RANGE"],
            description="Change cannot be represented within the numeric contract.",
        )
    percent = None
    if before == 0:
        reasons.append("ZERO_BASELINE")
    else:
        try:
            percent = _wire(delta / before * Decimal(100))
        except ValueError:
            reasons.append("PERCENTAGE_OUT_OF_RANGE")
    change: Literal["unchanged_within_tolerance", "increased", "decreased"] = (
        "unchanged_within_tolerance"
        if abs(delta) <= tolerance
        else "increased"
        if delta > 0
        else "decreased"
    )
    exact_delta = _exact(delta)
    rounding = (
        " Display rounding differs from the exact calculation."
        if Decimal(absolute) != delta
        else ""
    )
    description = (
        f"{left.concept}: {change.replace('_', ' ')}; change {exact_delta or absolute} {before_unit} "
        f"over {elapsed_text} days; slope {slope_text} {before_unit}/day.{rounding} "
        "Descriptive only; no clinical significance or formal response classification."
    )
    return PointComparison(
        **base,
        unit=before_unit,
        status="comparable",
        absolute_change=absolute,
        percentage_change=percent,
        elapsed_days=elapsed_text,
        slope_per_day=slope_text,
        exact_absolute_change=exact_delta,
        exact_slope_per_day=_exact(slope),
        change=change,
        reason_codes=reasons,
        description=description,
        usable_count=2,
    )


def compare_timeline_points(
    left: TimelinePoint, right: TimelinePoint, tolerance: str = "0"
) -> PointComparison:
    """Pair arithmetic only; public reads must use the full authorized window to resolve conflicts."""
    with localcontext() as context:
        context.prec = 80
        left = TimelinePoint.model_validate_json(left.model_dump_json())
        right = TimelinePoint.model_validate_json(right.model_dump_json())
        return _compare(left, right, _tolerance(tolerance), set())


def analyze_trends(
    points: list[TimelinePoint],
    window: TimelineWindow,
    tolerance: str = "0",
    left_point_id: UUID | None = None,
    right_point_id: UUID | None = None,
) -> TrendReport:
    with localcontext() as context:
        context.prec = 80
        numeric_tolerance = _tolerance(tolerance)
        selected = select_window(points, window)
        features = extract_features(points, window)
        unresolved = set(features.unresolved_point_ids)
        conflicts = {
            identifier for series in features.series for identifier in series.conflict_point_ids
        }
        groups: dict[tuple, list[TimelinePoint]] = {}
        for point in selected:
            if point.modality not in ("imaging", "laboratory", "vital", "symptom"):
                continue
            try:
                _, unit = _normalized(point)
            except ValueError:
                unit = _unit(point)
            key = (
                _partition(point.time.reference, point.time.date_shift_basis),
                point.concept,
                point.metric_definition,
                unit,
                point.lesion_id,
                point.method_version,
                point.origin,
                point.context,
                point.instrument,
                point.instrument_version,
            )
            groups.setdefault(key, []).append(point)
        for members in groups.values():
            known = [point for point in members if point.time.reference.basis != "unknown"]
            for point in known:
                if (
                    sum(
                        _position(other.time.reference) == _position(point.time.reference)
                        for other in known
                    )
                    > 1
                ):
                    conflicts.add(point.id)
        series = []
        for key, members in sorted(groups.items(), key=lambda item: str(item[0])):
            anchor = next(
                (
                    _position(point.time.reference)
                    for point in members
                    if point.id not in unresolved
                ),
                None,
            )
            chart = []
            usable = []
            for point in members:
                reasons = []
                value = None
                unit = key[3]
                qualifier = (
                    point.numeric_result.comparator
                    if point.numeric_result is not None and point.numeric_result.form == "censored"
                    else None
                )
                if point.id in unresolved:
                    reasons.append("TIME_UNRESOLVED")
                if point.id in conflicts or point.conflicts:
                    reasons.append("UNRESOLVED_SAME_TIME_CONFLICT")
                if point.availability != Availability.AVAILABLE or point.missing_reason:
                    reasons.append("MISSING_OR_UNAVAILABLE_VALUE")
                try:
                    value, unit = _normalized(point)
                except ValueError:
                    reasons.append("UNSUPPORTED_UNIT")
                if qualifier:
                    reasons.append("CENSORED_VALUE_NOT_EXACT")
                if point.ordinal_value is not None:
                    value = Decimal(point.ordinal_value)
                if value is None:
                    reasons.append("MISSING_NUMERIC_VALUE")
                if not reasons:
                    usable.append(point)
                y = None
                if value is not None and not reasons:
                    try:
                        y = _wire(value)
                    except ValueError:
                        reasons.append("VALUE_OUT_OF_RANGE")
                x = (
                    _wire(_position(point.time.reference) - anchor)
                    if anchor is not None and point.id not in unresolved
                    else None
                )
                exact = _exact(value) if value is not None else None
                threshold = None
                if (
                    qualifier
                    and point.numeric_result is not None
                    and point.numeric_result.form == "censored"
                ):
                    quantity = point.numeric_result.threshold
                    factor = (
                        UNITS[point.concept][quantity.unit][1]
                        if point.concept in UNITS and quantity.unit in UNITS[point.concept]
                        else Decimal(1000)
                        if point.modality == "imaging" and quantity.unit == "cm3"
                        else Decimal(1)
                    )
                    threshold = _exact(Decimal(quantity.value) * factor)
                label = (
                    f"{point.concept}: {exact} {unit or point.instrument or ''}"
                    if value is not None
                    else f"{point.concept}: unavailable"
                )
                if qualifier:
                    label = f"{point.concept}: {qualifier}{threshold} {unit}; censored, not an exact value"
                chart.append(
                    TrendChartPoint(
                        point_id=point.id,
                        x_elapsed_days=x,
                        y=y,
                        exact_value=exact,
                        label=label,
                        qualifier=qualifier,
                        censored_threshold=threshold,
                        reason_codes=reasons,
                        time=point.time,
                        source_ids=point.source_ids,
                        origin=point.origin,
                        context=point.context,
                    )
                )
            segments = [
                _compare(left, right, numeric_tolerance, conflicts)
                for left, right in zip(members, members[1:])
            ]
            endpoint = (
                _compare(usable[0], usable[-1], numeric_tolerance, conflicts)
                if len(usable) >= 2
                else None
            )
            if endpoint is not None:
                endpoint = endpoint.model_copy(update={"usable_count": len(usable)})
            directions = [segment.change for segment in segments if segment.status == "comparable"]
            has_turn = (
                "decreased" in directions
                and "increased" in directions[directions.index("decreased") + 1 :]
            )
            pattern = (
                (
                    "Measured reduction followed by regrowth."
                    if members[0].modality == "imaging"
                    else "Measured decrease followed by increase."
                )
                if has_turn
                else "Descriptive observed changes only."
            )
            series.append(
                TrendSeries(
                    key=hashlib.sha256(
                        json.dumps([str(part) for part in key]).encode()
                    ).hexdigest(),
                    concept=key[1],
                    metric_definition=key[2],
                    unit=key[3],
                    lesion_id=key[4],
                    method_version=key[5],
                    origin=key[6],
                    context=key[7],
                    instrument=key[8],
                    instrument_version=key[9],
                    points=chart,
                    segments=segments,
                    endpoint=endpoint,
                    usable_count=len(usable),
                    description=pattern,
                )
            )
        comparison = None
        if left_point_id is not None or right_point_id is not None:
            by_id = {point.id: point for point in selected}
            if left_point_id not in by_id or right_point_id not in by_id:
                comparison = PointComparison(
                    status="insufficient_data",
                    left_point_id=left_point_id,
                    right_point_id=right_point_id,
                    comparison_context="incompatible_scopes",
                    reason_codes=["POINT_OUTSIDE_WINDOW"],
                    description="Select two points inside the authorized event/knowledge window.",
                )
            elif left_point_id in unresolved or right_point_id in unresolved:
                comparison = PointComparison(
                    **_base(by_id[left_point_id], by_id[right_point_id]),
                    status="not_comparable",
                    reason_codes=["TIME_UNRESOLVED"],
                    description="Event times cannot be compared within this window.",
                )
            else:
                comparison = _compare(
                    by_id[left_point_id], by_id[right_point_id], numeric_tolerance, conflicts
                )
        return TrendReport(window=window, tolerance=tolerance, series=series, comparison=comparison)
