"""Independent descriptive arithmetic fixtures; no interpolation or clinical response assessment."""

from uuid import UUID

import pytest
from test_temporal_timeline import LATER, point, window

from canceros.clinical_contracts import ClinicalTime
from canceros.contracts import Availability, Context, Provenance
from canceros.temporal_trends import analyze_trends, compare_timeline_points


def quantity(identifier, day, value, unit="g/dL", **changes):
    return point(
        identifier,
        day,
        numeric_result={"form": "exact", "quantity": {"value": value, "unit": unit}},
        **changes,
    )


def compare(left, right, **kwargs):
    return analyze_trends(
        [left, right], window(), left_point_id=left.id, right_point_id=right.id, **kwargs
    ).comparison


def test_lab_unit_conversion_actual_irregular_interval_and_numeric_text_agreement():
    left = quantity(10, "2", "120", "g/L")
    right = quantity(11, "9", "9", "g/dL")
    result = compare(left, right)
    assert result.status == "comparable" and result.unit == "g/dL"
    assert result.absolute_change == "-3" and result.percentage_change == "-25"
    assert result.elapsed_days == "7" and result.slope_per_day == "-0.428571429"
    assert "change -3 g/dL" in result.description and "over 7 days" in result.description
    assert result.from_measurement_ids == left.source_ids
    assert result.comparison_context == "within_simulation"


def test_zero_baseline_percentage_null_with_valid_absolute_change():
    result = compare(quantity(10, "0", "0"), quantity(11, "10", "2"))
    assert result.status == "comparable" and result.absolute_change == "2"
    assert result.percentage_change is None and "ZERO_BASELINE" in result.reason_codes


def test_tolerance_is_numeric_engineering_choice_in_output_unit():
    result = compare(quantity(10, "0", "12"), quantity(11, "10", "12.01"), tolerance="0.02")
    assert result.change == "unchanged_within_tolerance" and result.absolute_change == "0.01"
    assert "no clinical significance" in result.description
    with pytest.raises(ValueError):
        analyze_trends([], window(), tolerance="-1")


def test_full_window_conflicts_block_even_if_requested_pair_omits_competing_point():
    first, second, duplicate = (
        quantity(10, "0", "12"),
        quantity(11, "10", "10"),
        quantity(12, "10", "100", "g/L"),
    )
    result = analyze_trends(
        [first, second, duplicate], window(), left_point_id=first.id, right_point_id=second.id
    ).comparison
    assert result.status == "not_comparable"
    assert "UNRESOLVED_SAME_TIME_CONFLICT" in result.reason_codes
    assert compare_timeline_points(second, duplicate).status == "not_comparable"


def test_unknown_censored_missing_points_remain_gaps_and_never_exact_arithmetic():
    first = quantity(10, "0", "12")
    censored = point(
        11,
        "10",
        numeric_result={
            "form": "censored",
            "comparator": "<",
            "threshold": {"value": "100", "unit": "g/L"},
        },
    )
    missing = point(
        12,
        "20",
        numeric_result={"form": "missing", "missing_reason": "not_collected"},
        missing_reason="not_collected",
        availability=Availability.UNAVAILABLE,
    )
    report = analyze_trends([first, censored, missing], window())
    assert len(report.series) == 1
    series = report.series[0]
    assert [entry.x_elapsed_days for entry in series.points] == ["0", "10", "20"]
    assert [entry.y for entry in series.points] == ["12", None, None]
    assert series.points[1].censored_threshold == "10" and "<10 g/dL" in series.points[1].label
    assert series.endpoint is None and all(
        segment.status != "comparable" for segment in series.segments
    )
    unknown = point(
        13,
        time=ClinicalTime(
            reference={
                "basis": "unknown",
                "time_domain": "simulation",
                "missing_reason": "unknown",
            },
            precision="unknown",
        ),
    )
    unresolved = analyze_trends(
        [first, unknown], window(), left_point_id=first.id, right_point_id=unknown.id
    )
    assert "TIME_UNRESOLVED" in unresolved.comparison.reason_codes


def test_one_point_has_no_invented_zero_change_or_slope():
    report = analyze_trends([quantity(10, "0", "12")], window())
    assert report.series[0].endpoint is None and report.series[0].segments == []


def test_ordinal_symptom_only_reports_direction_and_versioned_scale():
    left = point(
        10,
        "0",
        modality="symptom",
        concept="fatigue",
        numeric_result=None,
        ordinal_value="2",
        instrument="engineering_ordinal",
        instrument_version="1",
    )
    right = left.model_copy(
        update={"id": UUID(int=11), "time": point(11, "10").time, "ordinal_value": "5"}
    )
    result = compare(left, right)
    assert result.status == "not_comparable" and result.ordinal_direction == "increased"
    assert (
        result.absolute_change is None
        and result.percentage_change is None
        and result.slope_per_day is None
    )
    assert "ORDINAL_INSTRUMENT_NO_RATIO_ARITHMETIC" in result.reason_codes
    incompatible = right.model_copy(update={"instrument_version": "2"})
    assert "INSTRUMENT_MISMATCH" in compare_timeline_points(left, incompatible).reason_codes


@pytest.mark.parametrize(
    "change,reason",
    [
        ({"method_version": "different/1"}, "METHOD_MISMATCH"),
        ({"lesion_id": UUID(int=200)}, "LESION_MISMATCH"),
        ({"metric_definition": "functional_region_volume"}, "MASK_METRIC_MISMATCH"),
        ({"concept": "weight"}, "METRIC_MISMATCH"),
    ],
)
def test_incompatible_measurement_definitions_do_not_mix(change, reason):
    left = quantity(10, "0", "12")
    right = quantity(11, "10", "9", **change)
    assert reason in compare_timeline_points(left, right).reason_codes


def test_ids_outside_event_or_knowledge_window_cannot_bypass_filters():
    left, future = quantity(10, "0", "12"), quantity(11, "31", "9")
    result = analyze_trends(
        [left, future], window(), left_point_id=left.id, right_point_id=future.id
    ).comparison
    assert result.status == "insufficient_data" and result.reason_codes == ["POINT_OUTSIDE_WINDOW"]
    future = quantity(11, "10", "9", recorded_at=LATER)
    result = analyze_trends(
        [left, future], window(), left_point_id=left.id, right_point_id=future.id
    ).comparison
    assert result.reason_codes == ["POINT_OUTSIDE_WINDOW"]


def test_volume_conversion_and_reduction_regrowth_description_do_not_imply_clinical_response():
    points = [
        quantity(
            10,
            "0",
            "1",
            "cm3",
            modality="imaging",
            concept="numerical_region_volume",
            metric_definition="anatomical_volume",
        ),
        quantity(
            11,
            "7",
            "500",
            "mm3",
            modality="imaging",
            concept="numerical_region_volume",
            metric_definition="anatomical_volume",
        ),
        quantity(
            12,
            "21",
            "750",
            "mm3",
            modality="imaging",
            concept="numerical_region_volume",
            metric_definition="anatomical_volume",
        ),
    ]
    series = analyze_trends(points, window()).series[0]
    assert (
        series.segments[0].absolute_change == "-500" and series.segments[1].absolute_change == "250"
    )
    assert (
        series.endpoint.absolute_change == "-250"
        and series.endpoint.slope_per_day == "-11.904761905"
    )
    assert series.usable_count == 3 and series.endpoint.usable_count == 3
    assert "regrowth" in series.description
    assert [entry.x_elapsed_days for entry in series.points] == ["0", "7", "21"]


def test_tiny_physical_values_do_not_use_rounded_display_zero_as_denominator():
    left = quantity(
        10,
        "0",
        "0",
        "mm3",
        modality="imaging",
        concept="numerical_region_volume",
        metric_definition="numerical_region_volume",
        exact_value="0.00000000000001",
    )
    right = quantity(
        11,
        "10",
        "0",
        "mm3",
        modality="imaging",
        concept="numerical_region_volume",
        metric_definition="numerical_region_volume",
        exact_value="0.00000000000002",
    )
    result = compare(left, right)
    assert result.absolute_change == "0" and result.exact_absolute_change == "0.00000000000001"
    assert result.percentage_change == "100" and result.change == "increased"
    assert "ZERO_BASELINE" not in result.reason_codes
    assert "0.00000000000001 mm3" in result.description and "Display rounding" in result.description


def test_mixed_observed_and_hypothetical_pair_requires_explicit_verified_baseline_evidence():
    left = quantity(
        10,
        "0",
        "12",
        origin=Provenance.REAL_OBSERVED,
        context=Context.OBSERVED,
        time=ClinicalTime(
            reference={"basis": "date", "value": "2020-01-01", "time_domain": "source_calendar"},
            precision="day",
        ),
        branch_id=None,
        run_id=None,
    )
    right = quantity(11, "10", "9")
    result = compare_timeline_points(left, right)
    assert (
        result.comparison_context == "hypothetical_vs_observed"
        and result.status == "not_comparable"
    )
    assert "BASELINE_EVIDENCE_MISSING" in result.reason_codes
