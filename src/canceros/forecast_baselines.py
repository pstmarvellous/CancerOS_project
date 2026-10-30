"""Earlier-only engineering comparators; this module never enables patient forecasts."""

from decimal import Decimal, localcontext
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from canceros.contracts import Availability, Context, Contract, DecimalString, Provenance
from canceros.evaluation_splits import SplitManifest, SplitRole
from canceros.physical_measurements import CalculationDecimal
from canceros.temporal_timeline import (
    TimelinePoint,
    TimelineWindow,
    _partition,
    _position,
    select_window,
)
from canceros.temporal_trends import _exact, _normalized, _wire

ForecastMethod = Literal["locf", "last_two_linear", "ols_linear"]
METHODS: tuple[ForecastMethod, ...] = ("locf", "last_two_linear", "ols_linear")


class ForecastProtocol(Contract):
    version: Literal["forecast-protocol/1"] = "forecast-protocol/1"
    metric_code: str
    unit: str
    method_version: str
    metric_definition: str | None = None
    lesion_id: UUID | None = None
    population: str = "synthetic_engineering_fixture_only"
    supported_horizons: Annotated[list[DecimalString], Field(min_length=1, max_length=32)]
    nonnegative: Literal[True] = True

    @model_validator(mode="after")
    def horizons(self):
        values = [Decimal(value) for value in self.supported_horizons]
        if any(value <= 0 for value in values) or len(set(values)) != len(values):
            raise ValueError("Protocol horizons must be distinct and positive")
        return self


class ForecastReport(Contract):
    version: Literal["baseline-forecast/1"] = "baseline-forecast/1"
    method: ForecastMethod
    method_version: str = "earlier-only-decimal-baselines/1"
    protocol: ForecastProtocol
    window: TimelineWindow
    horizon_days: DecimalString
    status: Literal["estimate", "abstained"]
    estimate: DecimalString | None = None
    exact_estimate: CalculationDecimal | None = None
    source_ids: list[UUID] = []
    point_ids: list[UUID] = []
    reason_codes: list[str] = []
    evaluation_status: Literal["synthetic_engineering_only_real_evaluation_unavailable"] = (
        "synthetic_engineering_only_real_evaluation_unavailable"
    )
    patient_facing_enabled: Literal[False] = False
    limitations: list[str] = [
        "Synthetic arithmetic fixtures do not establish clinical forecasting accuracy.",
        "No prediction intervals or causal treatment interpretation are available.",
    ]
    next_action: str = (
        "Obtain a reviewed real-data endpoint/horizon protocol and independent outcomes."
    )


def _eligible(point: TimelinePoint, protocol: ForecastProtocol, window: TimelineWindow) -> bool:
    if window.event_cutoff is None:
        return False
    partition = _partition(window.event_cutoff, window.event_cutoff_shift_basis)
    if (
        partition is None
        or _partition(point.time.reference, point.time.date_shift_basis) != partition
    ):
        return False
    if (
        point.concept != protocol.metric_code
        or point.method_version != protocol.method_version
        or point.metric_definition != protocol.metric_definition
        or point.lesion_id != protocol.lesion_id
        or point.context != Context.SYNTHETIC
        or point.origin != Provenance.SYNTHETIC_GENERATED
        or point.measurement_basis == "simulated_target_no_mask_realization"
        or point.ordinal_value is not None
        or point.availability != Availability.AVAILABLE
        or point.missing_reason
        or point.conflicts
        or point.numeric_result is None
        or point.numeric_result.form != "exact"
    ):
        return False
    try:
        value, unit = _normalized(point)
        return value is not None and value >= 0 and unit == protocol.unit
    except ValueError:
        return False


def forecast_baseline(
    points: list[TimelinePoint],
    window: TimelineWindow,
    protocol: ForecastProtocol,
    method: ForecastMethod,
    horizon_days: str,
) -> ForecastReport:
    """Fit only selected comparable history; LOCF forecasts at origin+horizon, not last time+horizon."""
    with localcontext() as context:
        context.prec = 80

        def abstain(reason, used=()):
            return ForecastReport(
                method=method,
                protocol=protocol,
                window=window,
                horizon_days=horizon_days,
                status="abstained",
                reason_codes=[reason],
                point_ids=[point.id for point in used],
                source_ids=sorted({i for point in used for i in point.source_ids}, key=str),
            )

        horizon = Decimal(horizon_days)
        if horizon <= 0 or horizon not in [Decimal(h) for h in protocol.supported_horizons]:
            return abstain("UNSUPPORTED_HORIZON")
        if (
            protocol.population != "synthetic_engineering_fixture_only"
            or window.scope.mode == "observed"
        ):
            return abstain("REAL_EVALUATION_UNAVAILABLE")
        if (
            window.event_cutoff is None
            or _partition(window.event_cutoff, window.event_cutoff_shift_basis) is None
        ):
            return abstain("EXPLICIT_COMPARABLE_ORIGIN_REQUIRED")
        selected = select_window(points, window)
        candidates = [point for point in selected if _eligible(point, protocol, window)]
        # A second same-metric assertion at the same comparable time makes that time unusable,
        # including missing/censored assertions; never choose a favorable duplicate.
        members = [
            point
            for point in selected
            if point.concept == protocol.metric_code
            and point.lesion_id == protocol.lesion_id
            and _partition(point.time.reference, point.time.date_shift_basis)
            == _partition(window.event_cutoff, window.event_cutoff_shift_basis)
        ]
        duplicates = {
            _position(point.time.reference)
            for point in members
            if sum(
                _position(other.time.reference) == _position(point.time.reference)
                for other in members
            )
            > 1
        }
        candidates = [
            point for point in candidates if _position(point.time.reference) not in duplicates
        ]
        minimum = {"locf": 1, "last_two_linear": 2, "ols_linear": 3}[method]
        if len(candidates) < minimum:
            return abstain(f"INSUFFICIENT_DISTINCT_HISTORY_REQUIRES_{minimum}", candidates)
        used = (
            candidates[-1:]
            if method == "locf"
            else candidates[-2:]
            if method == "last_two_linear"
            else candidates
        )
        xs = [_position(point.time.reference) for point in used]
        ys = [_normalized(point)[0] for point in used]
        values = [value for value in ys if value is not None]
        target = _position(window.event_cutoff) + horizon
        if method == "locf":
            estimate = values[-1]
        else:
            # Center times at the first observation, then use the equivalent n-scaled
            # least-squares formula to avoid rounding recurring intermediate means.
            centered = [x - xs[0] for x in xs]
            count = Decimal(len(centered))
            sx = sum(centered, Decimal(0))
            sy = sum(values, Decimal(0))
            denominator = count * sum((x * x for x in centered), Decimal(0)) - sx * sx
            slope = (
                count * sum((x * y for x, y in zip(centered, values)), Decimal(0)) - sx * sy
            ) / denominator
            intercept = (sy - slope * sx) / count
            estimate = intercept + slope * (target - xs[0])
        if estimate < 0:
            return abstain("NEGATIVE_FORECAST_UNSUPPORTED_NO_CLIPPING", used)
        try:
            wire = _wire(estimate)
        except ValueError:
            return abstain("COMPUTATION_OUT_OF_RANGE", used)
        exact = _exact(estimate)
        if exact is None:
            return abstain("COMPUTATION_OUT_OF_RANGE", used)
        return ForecastReport(
            method=method,
            protocol=protocol,
            window=window,
            horizon_days=horizon_days,
            status="estimate",
            estimate=wire,
            exact_estimate=exact,
            point_ids=[point.id for point in used],
            source_ids=sorted({i for point in used for i in point.source_ids}, key=str),
        )


class ForecastEvaluationCase(Contract):
    id: UUID
    patient_id: UUID
    group_id: UUID
    window: TimelineWindow
    horizon_days: DecimalString
    label_knowledge_as_of: AwareDatetime
    points: list[TimelinePoint]


class ForecastEvaluationResult(Contract):
    case_id: UUID
    patient_id: UUID
    group_id: UUID
    method: ForecastMethod
    horizon_days: DecimalString
    forecast: ForecastReport
    target_point_id: UUID | None = None
    target_value: CalculationDecimal | None = None
    signed_error: CalculationDecimal | None = None
    reason_codes: list[str]


class ForecastMetric(Contract):
    method: ForecastMethod
    horizon_days: DecimalString
    patient_id: UUID | None
    sample: Literal["method_eligible", "common_eligible"]
    attempted: int
    scored: int
    abstained: int
    excluded: int
    coverage: DecimalString
    mae: CalculationDecimal | None
    rmse: CalculationDecimal | None


class ForecastEvaluationReport(Contract):
    version: Literal["forecast-evaluation/1"] = "forecast-evaluation/1"
    protocol: ForecastProtocol
    split_id: UUID
    split_manifest: SplitManifest
    grouping_hash: str
    role: SplitRole
    cases: list[ForecastEvaluationResult]
    metrics: list[ForecastMetric]
    real_evaluation: Literal["unavailable"] = "unavailable"
    patient_facing_enabled: Literal[False] = False
    uncertainty: Literal["not_estimated_tiny_synthetic_cohort"] = (
        "not_estimated_tiny_synthetic_cohort"
    )


def evaluate_forecasts(
    cases: list[ForecastEvaluationCase],
    protocol: ForecastProtocol,
    split: SplitManifest,
    role: SplitRole = "test",
) -> ForecastEvaluationReport:
    """No fitting/tuning across origins or groups. Labels must be exact at origin+horizon."""
    if role not in ("train", "validation", "test"):
        raise ValueError("Demo/unassigned groups cannot be evaluated")
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("Evaluation case IDs must be unique")
    groups = {group.group_id: group for group in split.groups}
    memberships = [patient for group in split.groups for patient in group.patient_ids]
    if len(set(memberships)) != len(memberships) or len(groups) != len(split.groups):
        raise ValueError("Frozen split contains overlapping original-patient groups")
    results = []
    with localcontext() as context:
        context.prec = 80
        for case in cases:
            group = groups.get(case.group_id)
            if (
                group is None
                or case.patient_id not in group.patient_ids
                or any(point.patient_id != case.patient_id for point in case.points)
            ):
                raise ValueError("Case must inherit its frozen original-patient group")
            if (
                group.role != role
                or group.demo_exposed
                or group.exclusions
                or (role == "test" and not group.held_out_group_eligible)
            ):
                raise ValueError("Cross-role, demo-exposed or excluded group cannot be scored")
            if case.label_knowledge_as_of < case.window.knowledge_as_of:
                raise ValueError("Label cutoff precedes fitting knowledge cutoff")
            for method in METHODS:
                forecast = forecast_baseline(
                    case.points, case.window, protocol, method, case.horizon_days
                )
                reasons = list(forecast.reason_codes)
                labels = []
                if (
                    case.window.event_cutoff is not None
                    and Decimal(case.horizon_days) > 0
                    and _partition(case.window.event_cutoff, case.window.event_cutoff_shift_basis)
                    is not None
                ):
                    target_time = _position(case.window.event_cutoff) + Decimal(case.horizon_days)
                    label_window = case.window.model_copy(
                        update={"event_cutoff": None, "knowledge_as_of": case.label_knowledge_as_of}
                    )
                    at_target = [
                        point
                        for point in select_window(case.points, label_window)
                        if point.concept == protocol.metric_code
                        and point.lesion_id == protocol.lesion_id
                        and _partition(point.time.reference, point.time.date_shift_basis)
                        == _partition(
                            case.window.event_cutoff, case.window.event_cutoff_shift_basis
                        )
                        and _position(point.time.reference) == target_time
                    ]
                    labels = (
                        at_target
                        if len(at_target) == 1 and _eligible(at_target[0], protocol, case.window)
                        else []
                    )
                if len(labels) != 1:
                    reasons.append("EXACT_FUTURE_LABEL_UNAVAILABLE_OR_AMBIGUOUS")
                target = _normalized(labels[0])[0] if len(labels) == 1 else None
                error = None
                if target is not None and forecast.status == "estimate":
                    estimated = forecast.exact_estimate or forecast.estimate
                    assert estimated is not None
                    error = _exact(Decimal(estimated) - target)
                results.append(
                    ForecastEvaluationResult(
                        case_id=case.id,
                        patient_id=case.patient_id,
                        group_id=case.group_id,
                        method=method,
                        horizon_days=case.horizon_days,
                        forecast=forecast,
                        target_point_id=labels[0].id if len(labels) == 1 else None,
                        target_value=_exact(target) if target is not None else None,
                        signed_error=error,
                        reason_codes=reasons,
                    )
                )
        common = {
            case.id
            for case in cases
            if all(
                result.signed_error is not None for result in results if result.case_id == case.id
            )
        }
        metrics = []
        patients: list[UUID | None] = [None, *sorted({case.patient_id for case in cases}, key=str)]
        for method in METHODS:
            for horizon in sorted({case.horizon_days for case in cases}, key=Decimal):
                for patient in patients:
                    attempted = [
                        r
                        for r in results
                        if r.method == method
                        and r.horizon_days == horizon
                        and (patient is None or r.patient_id == patient)
                    ]
                    if not attempted:
                        continue
                    for sample in ("method_eligible", "common_eligible"):
                        scored = [
                            r
                            for r in attempted
                            if r.signed_error is not None
                            and (sample == "method_eligible" or r.case_id in common)
                        ]
                        errors = [
                            Decimal(r.signed_error) for r in scored if r.signed_error is not None
                        ]
                        metrics.append(
                            ForecastMetric(
                                method=method,
                                horizon_days=horizon,
                                patient_id=patient,
                                sample=sample,
                                attempted=len(attempted),
                                scored=len(scored),
                                abstained=sum(r.forecast.status == "abstained" for r in attempted),
                                excluded=sum(
                                    r.forecast.status == "estimate"
                                    and (
                                        r.signed_error is None
                                        or (sample == "common_eligible" and r.case_id not in common)
                                    )
                                    for r in attempted
                                ),
                                coverage=_wire(Decimal(len(scored)) / len(attempted)),
                                mae=_exact(sum((abs(e) for e in errors), Decimal(0)) / len(errors))
                                if errors
                                else None,
                                rmse=_exact(
                                    (sum((e * e for e in errors), Decimal(0)) / len(errors)).sqrt()
                                )
                                if errors
                                else None,
                            )
                        )
        return ForecastEvaluationReport(
            protocol=protocol,
            split_id=split.id,
            split_manifest=split,
            grouping_hash=split.grouping_hash,
            role=role,
            cases=results,
            metrics=metrics,
        )
