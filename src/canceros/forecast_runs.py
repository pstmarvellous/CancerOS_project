"""Private forecast requests retain provenance and always respect the real-evaluation gate."""

from typing import Literal
from uuid import UUID

from canceros.contracts import Availability, Contract, DecimalString, Provenance
from canceros.evaluation_splits import inherited_assignment, load_split
from canceros.forecast_baselines import ForecastProtocol, ForecastReport
from canceros.temporal_timeline import _partition
from canceros.temporal_trends import _normalized
from canceros.timeline_runs import TimelineQuery, read_window_points


class ForecastQuery(Contract):
    timeline: TimelineQuery
    protocol: ForecastProtocol
    method: Literal["locf", "last_two_linear", "ols_linear"]
    horizon_days: DecimalString
    split_id: UUID | None = None


def query_forecast(c, i, p, u, value: ForecastQuery) -> ForecastReport:
    points, restrictions = read_window_points(c, i, p, u, value.timeline)
    reasons = ["REAL_EVALUATION_UNAVAILABLE", "QUALIFIED_PROTOCOL_REVIEW_REQUIRED"]
    if restrictions:
        reasons.append("CURRENT_SOURCE_RESTRICTIONS")
    if any(point.origin != Provenance.SYNTHETIC_GENERATED for point in points):
        reasons.append("ENGINEERING_BASELINES_DO_NOT_ESTABLISH_REAL_POPULATION_SUPPORT")
    if value.split_id:
        manifest = load_split(c, p, value.split_id)
        assignment = inherited_assignment(c, i, p, u, value.split_id)
        if not assignment.grouping_current or assignment.demo_exposed:
            reasons.append("FROZEN_PATIENT_GROUP_REVIEW_REQUIRED")
        # The existing split contract cannot grant real forecasting clearance.
        if not manifest.independent_real_evaluation_cleared:
            reasons.append("INDEPENDENT_REAL_EVALUATION_NOT_CLEARED")
    else:
        reasons.append("FROZEN_PATIENT_SPLIT_REQUIRED")
    window = value.timeline.window
    anchor = window.event_cutoff
    if anchor is None or _partition(anchor, window.event_cutoff_shift_basis) is None:
        reasons.append("EXPLICIT_COMPARABLE_EVENT_ORIGIN_REQUIRED")
    if value.protocol.population != "synthetic_engineering_fixture_only":
        reasons.append("UNSUPPORTED_POPULATION")
    if value.horizon_days not in value.protocol.supported_horizons:
        reasons.append("UNSUPPORTED_HORIZON")
    eligible = [
        point
        for point in points
        if point.concept == value.protocol.metric_code
        and point.method_version == value.protocol.method_version
        and point.metric_definition == value.protocol.metric_definition
        and point.lesion_id == value.protocol.lesion_id
        and point.availability == Availability.AVAILABLE
        and not point.conflicts
        and point.numeric_result is not None
        and point.numeric_result.form == "exact"
        and anchor is not None
        and _partition(anchor, window.event_cutoff_shift_basis) is not None
        and _partition(point.time.reference, point.time.date_shift_basis)
        == _partition(anchor, window.event_cutoff_shift_basis)
    ]
    normalized = []
    for point in eligible:
        try:
            if _normalized(point)[1] == value.protocol.unit:
                normalized.append(point)
        except ValueError:
            continue
    eligible = normalized
    minimum = {"locf": 1, "last_two_linear": 2, "ols_linear": 3}[value.method]
    if len({str(point.time.reference) for point in eligible}) < minimum:
        reasons.append(f"AT_LEAST_{minimum}_COMPARABLE_DISTINCT_TIME_OBSERVATIONS_REQUIRED")
    return ForecastReport(
        method=value.method,
        protocol=value.protocol,
        window=window,
        horizon_days=value.horizon_days,
        status="abstained",
        estimate=None,
        exact_estimate=None,
        source_ids=sorted(
            {identifier for point in points for identifier in point.source_ids}, key=str
        ),
        point_ids=[point.id for point in points],
        reason_codes=reasons,
        next_action="Complete a reviewed endpoint/population/horizon protocol and independent real longitudinal evaluation; use descriptive history meanwhile",
    )
