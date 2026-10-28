"""Decimal temporal changes and explicit incomparable states, with no registration input."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from canceros.contracts import Provenance
from canceros.temporal_measurements import ComparisonError, ScalarPoint, compare_points


def pair(before="100", after="75"):
    group = uuid4()
    left = ScalarPoint(
        event_id=uuid4(),
        measurement_id=uuid4(),
        study_id=uuid4(),
        annotation_class="functional_enhancement_region",
        definition="functional_region_volume",
        method="voxel_count_abs_det_affine/1",
        origin=Provenance.SYNTHETIC_GENERATED,
        volume_mm3=before,
        time_group_id=group,
        relative_day="0",
        eligible=True,
    )
    right = left.model_copy(
        update={
            "event_id": uuid4(),
            "measurement_id": uuid4(),
            "study_id": uuid4(),
            "volume_mm3": after,
            "relative_day": "10",
        }
    )
    return left, right


def test_negative_change_is_exact_scalar_arithmetic_without_registration_dependency():
    left, right = pair()
    before = left.model_dump_json(), right.model_dump_json()
    result = compare_points(left, right)
    assert result.eligibility and result.absolute_mm3 == "-25" and result.percent_change == "-25"
    assert not result.reasons and "not_RECIST" in result.meaning
    assert (left.model_dump_json(), right.model_dump_json()) == before
    assert "registration" not in ScalarPoint.model_fields


def test_missing_measurement_reference_is_a_gap_without_fabricated_identity():
    left, right = pair()
    left = left.model_copy(update={"measurement_id": None})
    result = compare_points(left, right)
    assert not result.eligibility and result.absolute_mm3 is None
    assert "measurement_reference_missing" in result.reasons


def test_series_keeps_unsupported_percent_as_an_explicit_gap():
    from canceros.lesion_tracking import _change

    result = _change(*pair("0.000000001", "999999999999999"))
    assert not result.eligibility and result.percent_change is None
    assert result.reasons == ["scalar_change_outside_supported_numeric_range"]


@pytest.mark.parametrize("after,delta", [("0", "0"), ("12.345678901", "12.345678901")])
def test_zero_baseline_retains_absolute_without_inventing_percentage(after, delta):
    result = compare_points(*pair("0", after))
    assert result.eligibility and result.absolute_mm3 == delta and result.percent_change is None
    assert result.reasons == ["zero_baseline_percentage_undefined"]


def test_decimal_precision_and_half_even_output():
    result = compare_points(*pair("0.000000003", "0.000000004"))
    assert result.absolute_mm3 == "0.000000001" and result.percent_change == "33.333333333"
    result = compare_points(*pair("200000000", "200000001"))
    assert result.absolute_mm3 == "1" and result.percent_change == "0.0000005"


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"annotation_class": "anatomical_tumor_contour"}, "annotation_class_mismatch"),
        ({"definition": "anatomical_tumor_volume"}, "definition_mismatch"),
        ({"method": "different_method/2"}, "method_mismatch"),
        ({"origin": Provenance.REAL_DERIVED}, "origin_mismatch"),
        ({"unit": "cm3"}, "unit_mismatch"),
        ({"annotation_class": "unknown"}, "annotation_class_unknown"),
        ({"definition": "unknown"}, "measurement_definition_unknown"),
        ({"method": "unknown"}, "measurement_method_unknown"),
        ({"time_group_id": None}, "time_group_unknown"),
        ({"time_group_id": uuid4()}, "time_group_mismatch"),
        ({"relative_day": None}, "relative_time_unknown"),
        ({"relative_day": "0"}, "strictly_later_comparable_time_required"),
        ({"relative_day": "-1"}, "strictly_later_comparable_time_required"),
        ({"volume_mm3": None}, "measurement_missing"),
        ({"volume_mm3": "-1"}, "negative_volume_invalid"),
        ({"eligible": False}, "point_not_eligible"),
    ],
)
def test_incompatible_points_block_all_changes(changes, reason):
    left, right = pair()
    result = compare_points(left, right.model_copy(update=changes))
    assert not result.eligibility and result.absolute_mm3 is None and result.percent_change is None
    assert reason in result.reasons


def test_unknown_matched_values_still_block_and_origins_are_never_promoted():
    left, right = pair()
    for field, value in (
        ("method", "not_established"),
        ("annotation_class", "unknown"),
        ("definition", "unknown"),
    ):
        result = compare_points(
            left.model_copy(update={field: value}), right.model_copy(update={field: value})
        )
        assert not result.eligibility
    assert left.origin == right.origin == Provenance.SYNTHETIC_GENERATED


def test_same_examination_phase_is_not_a_temporal_volume_change():
    left, right = pair()
    result = compare_points(left, right.model_copy(update={"study_id": left.study_id}))
    assert not result.eligibility and result.absolute_mm3 is None
    assert "distinct_examinations_required" in result.reasons


@pytest.mark.parametrize("annotation_class", ["bounding_box", "approximate_illustrative"])
def test_same_engineering_class_can_compare_without_becoming_anatomical(annotation_class):
    left, right = pair()
    result = compare_points(
        left.model_copy(
            update={"annotation_class": annotation_class, "definition": "numerical_region_volume"}
        ),
        right.model_copy(
            update={"annotation_class": annotation_class, "definition": "numerical_region_volume"}
        ),
    )
    assert result.eligibility and result.absolute_mm3 == "-25"
    assert "not_RECIST" in result.meaning


def test_nonfinite_and_overflow_are_static_failures_not_percentages():
    left, right = pair("0.000000001", "999999999999999")
    with pytest.raises(ComparisonError, match="computed_change_outside_quantity_bounds"):
        compare_points(left, right)
    with pytest.raises(ComparisonError, match="finite_bounded_scalar_quantity_required"):
        compare_points(left, right.model_copy(update={"volume_mm3": "NaN"}))
    with pytest.raises(ValidationError):
        ScalarPoint.model_validate({**left.model_dump(), "volume_mm3": "Infinity"})
