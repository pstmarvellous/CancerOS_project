"""Engineering fixtures for deterministic physical hypothetical geometry only."""

from decimal import Decimal

import numpy as np
import pytest
from pydantic import ValidationError

from canceros.imaging_geometry import canonical_geometry
from canceros.synthetic_shape import ShapeConfig, ShapeError, generate_shape


def baseline():
    mask = np.zeros((24, 24, 24), dtype=np.uint8)
    mask[10:14, 10:14, 10:14] = 1
    return mask


def test_growth_transform_zeros_have_stable_jsonb_representation():
    mask = np.zeros((3, 3, 2), dtype=np.uint8)
    mask[1, 1, 0] = 1
    affine = np.eye(4)
    affine[:3, 3] = (-1, -1, 0)
    result = generate_shape(mask, canonical_geometry(mask.shape, affine), "2", ShapeConfig(seed=1))
    transform = np.asarray(result.report.baseline_to_synthetic_world)
    assert not np.signbit(transform[transform == 0]).any()
    assert result.report.status == "blocked" and result.array is None


@pytest.mark.parametrize("target,scale,count", [("512", 2, 512), ("8", 0.5, 8), ("64", 1, 64)])
def test_cuboid_growth_shrinkage_and_identity(target, scale, count):
    mask = baseline()
    before = mask.copy()
    geometry = canonical_geometry(mask.shape, np.eye(4))
    generated = generate_shape(mask, geometry, target, ShapeConfig(seed=27))
    assert generated.report.status == "ready"
    assert generated.report.scale_factor == scale
    assert generated.report.realized_values.voxel_count == count
    assert generated.report.realized_values.exact_volume_mm3 == target
    assert generated.report.baseline_values.exact_volume_mm3 == "64"
    assert generated.array.dtype == np.uint8 and not generated.array.flags.writeable
    np.testing.assert_array_equal(mask, before)
    repeated = generate_shape(mask, geometry, target, ShapeConfig(seed=27))
    np.testing.assert_array_equal(repeated.array, generated.array)
    assert repeated.report == generated.report
    assert generate_shape(mask, geometry, target, ShapeConfig(seed=28)).report.seed == 28


@pytest.mark.parametrize(
    "affine",
    [
        np.diag([2.0, 3, 4, 1]),
        np.array([[-2.0, 0, 0, 90], [0, 3, 0, 23], [0, 0, 4, -8], [0, 0, 0, 1]]),
        np.array([[2.0, 1, 0, 30], [0, 3, 1, 20], [0, 0, 4, 10], [0, 0, 0, 1]]),
        np.array([[0.0, -3, 0, 80], [2, 0, 0, 20], [0, 0, 4, 10], [0, 0, 0, 1]]),
    ],
)
def test_full_affine_center_and_volume_no_double_spacing(affine):
    mask = baseline()
    geometry = canonical_geometry(mask.shape, affine)
    generated = generate_shape(mask, geometry, "12288", ShapeConfig(seed=0))
    assert generated.report.status == "ready"
    assert generated.report.realized_values.voxel_count == 512
    center = affine[:3, :3] @ np.array([11.5] * 3) + affine[:3, 3]
    np.testing.assert_allclose(generated.report.center_ras_mm, center)
    expected = np.diag([2.0, 2, 2, 1])
    expected[:3, 3] = -center
    np.testing.assert_allclose(generated.report.baseline_to_synthetic_world, expected)
    np.testing.assert_array_equal(
        generated.array,
        generate_shape(
            mask, canonical_geometry(mask.shape, np.eye(4)), "512", ShapeConfig(seed=0)
        ).array,
    )


def test_configured_zero_is_explicitly_hypothetical_not_verified_absence():
    mask = baseline()
    generated = generate_shape(
        mask, canonical_geometry(mask.shape, np.eye(4)), "0", ShapeConfig(seed=1)
    )
    assert generated.report.status == "zero" and not generated.array.any()
    assert generated.report.realized_values.availability == "configured_simulated_absent"
    assert generated.report.realized_values.exact_volume_mm3 == "0"
    assert generated.report.baseline_to_synthetic_world is None
    assert "not_cure_or_surgery" in generated.report.realized_values.reason


def test_nonzero_tiny_target_cannot_be_reported_as_configured_zero():
    mask = baseline()
    result = generate_shape(
        mask, canonical_geometry(mask.shape, np.eye(4)), "0.000000001", ShapeConfig(seed=1)
    )
    assert result.report.status == "blocked" and result.array is None
    assert result.report.reasons == ["nonzero_target_resampled_to_empty"]
    assert result.report.realized_values.availability == "invalid"
    assert result.report.target_mm3 == "0.000000001"


def test_failed_tolerance_retains_actual_measurement_and_original_target():
    mask = baseline()
    result = generate_shape(
        mask, canonical_geometry(mask.shape, np.eye(4)), "100", ShapeConfig(seed=1)
    )
    assert result.report.status == "blocked" and result.array is None
    assert result.report.reasons == ["realized_volume_outside_frozen_tolerance"]
    assert result.report.target_mm3 == "100"
    assert Decimal(result.report.realized_values.exact_volume_mm3) == 64
    assert result.report.tolerance_mm3 == "1"


def test_voxel_cell_clipping_detected_when_transformed_centers_are_inside():
    mask = np.zeros((5, 5, 5), dtype=np.uint8)
    mask[1:4, 1:4, 1:4] = 1
    # Centers become [0, 2, 4], inside; outer cell faces become [-1, 5].
    result = generate_shape(
        mask, canonical_geometry(mask.shape, np.eye(4)), "216", ShapeConfig(seed=1)
    )
    assert result.report.status == "blocked" and result.array is None
    assert result.report.reasons == ["scaled_voxel_cell_support_outside_fixed_grid"]
    assert result.report.realized_values is None


@pytest.mark.parametrize(
    "target", ["-1", "nan", "Infinity", "1e4", "1000000000000000", 3, "0.0000000001"]
)
def test_invalid_targets_raise_static_error(target):
    mask = baseline()
    with pytest.raises(ShapeError, match="Provide valid nonempty binary"):
        generate_shape(mask, canonical_geometry(mask.shape, np.eye(4)), target, ShapeConfig(seed=0))


@pytest.mark.parametrize("value", [0, 2, -1, np.nan, np.inf])
def test_empty_nonbinary_nonfinite_baselines_rejected(value):
    mask = np.full((3, 3, 3), value)
    with pytest.raises(ShapeError):
        generate_shape(mask, canonical_geometry(mask.shape, np.eye(4)), "8", ShapeConfig(seed=0))


@pytest.mark.parametrize("seed", [True, -1, 4294967296, "1", 1.5])
def test_seed_is_required_strict_bounded_and_version_frozen(seed):
    with pytest.raises(ValidationError):
        ShapeConfig(seed=seed)
    with pytest.raises(ValidationError):
        ShapeConfig(seed=1, version="other")


def test_invalid_grid_or_config_and_nonspatial_baselines_rejected():
    mask = baseline()
    geometry = canonical_geometry(mask.shape, np.eye(4))
    with pytest.raises(ShapeError):
        generate_shape(mask[:2], geometry, "64", ShapeConfig(seed=0))
    with pytest.raises(ShapeError):
        generate_shape(mask, geometry, "64", None)
    with pytest.raises(ValidationError):
        ShapeConfig()
