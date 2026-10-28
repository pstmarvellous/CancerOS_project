"""Independent artificial metric arithmetic; no real reference approvals."""

import json

import numpy as np
import pytest

from canceros import segmentation_qc as qc
from canceros.imaging_geometry import canonical_geometry
from canceros.segmentation_qc import evaluate_masks, inspect_mask


def evaluate(candidate, reference, geometry):
    return evaluate_masks(
        candidate, reference, geometry, independent_reference=True, self_comparison=False
    )


def test_qc_keeps_multifocal_components_and_flags_boundary_without_deleting():
    array = np.zeros((5, 5, 5), dtype=np.uint16)
    array[0, 0, 0] = array[3, 3, 3] = 1
    array[2, 2, 2] = 5
    original = array.copy()
    report = inspect_mask(array, canonical_geometry(array.shape, np.diag([2, 3, 4, 1])))
    assert report.technical_status == "pass" and report.foreground_voxels == 3
    assert report.labels[0].components_6 == 2 and report.labels[0].boundary_voxels == 1
    assert report.labels[1].label == 5 and report.labels[1].voxel_count == 1
    assert "MULTIPLE_COMPONENTS_RETAINED_MAY_REPRESENT_MULTIFOCAL_REGIONS" in report.warnings
    assert "FOREGROUND_TOUCHES_IMAGE_BOUNDARY_EXTENT_REVIEW_REQUIRED" in report.warnings
    assert (
        report.scientific_review == "pending"
        and report.source_association == "not_established_here"
    )
    np.testing.assert_array_equal(array, original)


@pytest.mark.parametrize(
    "semantics,case,status",
    [
        ("not_recorded", "empty_unknown", "fail"),
        ("missing_annotation", "missing_annotation", "fail"),
        ("processing_failure", "processing_failure", "fail"),
        ("confirmed_absence", "confirmed_absence", "pass"),
    ],
)
def test_empty_semantics_are_distinct_not_inferred(semantics, case, status):
    mask = np.zeros((2, 3, 4), dtype=np.uint8)
    result = inspect_mask(mask, canonical_geometry(mask.shape, np.eye(4)), semantics)
    assert result.empty_case == case and result.technical_status == status
    assert result.foreground_voxels == 0
    assert result.scientific_review == "pending"


@pytest.mark.parametrize("value", [np.nan, np.inf, -0.5, 0.5, 65536])
def test_invalid_labels_fail_without_nan_or_fabricated_counts(value):
    mask = np.zeros((2, 3, 4))
    mask[0, 0, 0] = value
    result = inspect_mask(mask, canonical_geometry(mask.shape, np.eye(4)))
    assert result.technical_status == "fail"
    assert result.foreground_voxels is None and result.labels == ()
    json.dumps(result.model_dump(), allow_nan=False)


def test_qc_revalidates_geometry_and_contradictory_absence():
    mask = np.ones((2, 3, 4), dtype=np.uint8)
    geometry = canonical_geometry(mask.shape, np.eye(4))
    bad = geometry.model_copy(
        update={"affine_ras_mm": ((0, 0, 0, 0), (0, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1))}
    )
    assert inspect_mask(mask, bad).technical_status == "fail"
    assert not inspect_mask(mask, bad).geometry_valid
    assert inspect_mask(mask, geometry, "confirmed_absence").technical_status == "fail"


def test_known_dice_and_volume_error_from_independent_counts():
    candidate = np.zeros((5, 5, 5), dtype=np.uint8)
    reference = np.zeros_like(candidate)
    candidate[1:3, 1:3, 1:3] = 1  # 8voxels.
    reference[2:4, 1:3, 1:3] = 1  # 8voxels; 4 overlap.
    geometry = canonical_geometry(candidate.shape, np.diag([2, 3, 4, 1]))
    report = evaluate(candidate, reference, geometry)
    assert report.status == "eligible" and report.dice == "0.5"
    assert report.hd95_mm == "2"
    assert report.absolute_volume_error_mm3 == "0" and report.relative_volume_error == "0"
    assert report.scored_cases == 1 and report.failed_cases == 0
    reference[3, 2, 2] = 0  # Reference now7, candidate8 =>24mm3 error, relative1/7.
    report = evaluate(candidate, reference, geometry)
    assert report.absolute_volume_error_mm3 == "24"
    assert report.relative_volume_error == "0.142857143"


def test_hd95_full_affine_respects_shear_not_spacing_only_distance():
    candidate = np.zeros((5, 5, 5), dtype=np.uint8)
    reference = np.zeros_like(candidate)
    candidate[1, 1, 1] = 1
    reference[2, 2, 1] = 1
    # d=(1,1,0) maps to (3,3,0), Euclidean distance sqrt18.
    geometry = canonical_geometry(
        candidate.shape, [[2, 1, 0, 10], [0, 3, 0, 20], [0, 0, 4, 30], [0, 0, 0, 1]]
    )
    report = evaluate(candidate, reference, geometry)
    assert report.hd95_mm == "4.242640687"
    assert report.dice == "0"
    assert float(report.hd95_mm) != pytest.approx(np.sqrt(4 + 10), abs=1e-6)


def test_symmetric_percentile_is_concat_directional_not_max_directional_percentile():
    candidate = np.zeros((12, 2, 2), dtype=np.uint8)
    reference = np.zeros_like(candidate)
    candidate[1, 0, 0] = 1
    reference[1:11, 0, 0] = 1
    # Source->reference distances[0]; reverse[0,1,..9]; 11values, linear95%=8.5.
    report = evaluate(candidate, reference, canonical_geometry(candidate.shape, np.eye(4)))
    assert report.hd95_mm == "8.5"
    assert report.dice == "0.181818182"
    assert report.absolute_volume_error_mm3 == "9"


@pytest.mark.parametrize("case", ["both_empty", "candidate_empty", "reference_empty"])
def test_empty_metrics_have_explicit_denominators_and_no_infinite_distances(case):
    candidate = np.zeros((3, 3, 3), dtype=np.uint8)
    reference = np.zeros_like(candidate)
    if case == "candidate_empty":
        reference[1, 1, 1] = 1
    if case == "reference_empty":
        candidate[1, 1, 1] = 1
    report = evaluate(candidate, reference, canonical_geometry(candidate.shape, np.eye(4)))
    assert report.empty_case == case and report.hd95_mm is None
    assert report.dice == (None if case == "both_empty" else "0")
    assert report.failed_cases == (0 if case == "both_empty" else 1)
    assert report.correct_absence_cases == (1 if case == "both_empty" else 0)
    assert report.attempted_cases == report.eligible_attempted_cases == 1
    assert report.scored_cases == 0
    if case != "candidate_empty":
        assert report.relative_volume_error is None
    json.dumps(report.model_dump(), allow_nan=False)


def test_self_missing_and_nonindependent_references_are_excluded_not_accuracy():
    array = np.ones((2, 3, 4), dtype=np.uint8)
    geometry = canonical_geometry(array.shape, np.eye(4))
    for reference, independent, self_comparison in (
        (array.copy(), True, True),
        (array, True, False),
        (array.copy(), False, False),
        (None, False, False),
    ):
        result = evaluate_masks(
            array,
            reference,
            geometry,
            independent_reference=independent,
            self_comparison=self_comparison,
        )
        assert result.status == "not_evaluated" and result.dice is None
        assert result.attempted_cases == 1 and result.eligible_attempted_cases == 0
        assert result.exclusions


def test_invalid_and_resource_failed_cases_stay_in_attempt_denominator(monkeypatch):
    array = np.ones((2, 3, 4), dtype=np.uint8)
    geometry = canonical_geometry(array.shape, np.eye(4))
    invalid = array.astype(float)
    invalid[0, 0, 0] = np.nan
    result = evaluate(invalid, array, geometry)
    assert result.status == "not_evaluated" and result.failed_cases == 1
    assert result.eligible_attempted_cases == result.attempted_cases == 1
    monkeypatch.setattr(qc, "MAX_SURFACE_POINTS", 1)
    result = evaluate(array, array.copy(), geometry)
    assert result.status == "not_evaluated" and result.failed_cases == 1
    assert result.eligible_attempted_cases == 1
    assert "SURFACE_POINT_RESOURCE_LIMIT" in result.exclusions


def test_truthy_strings_and_multilabel_metrics_cannot_bypass_policy():
    array = np.ones((2, 3, 4), dtype=np.uint8)
    geometry = canonical_geometry(array.shape, np.eye(4))
    with pytest.raises(ValueError):
        evaluate_masks(
            array, array.copy(), geometry, independent_reference="yes", self_comparison=False
        )
    assert evaluate(array * 2, array, geometry).status == "not_evaluated"
