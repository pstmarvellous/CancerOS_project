"""Independent cuboid arithmetic, physical frames and explicit unavailable values."""

from decimal import Decimal, localcontext

import numpy as np
import pytest

from canceros.imaging_geometry import canonical_geometry
from canceros.physical_measurements import measure_region, relative_volume_change


@pytest.mark.parametrize(
    "affine,centroid,extent",
    [
        (np.diag([2.0, 3.0, 4.0, 1.0]), ("2", "4.5", "2"), ("6", "12", "8")),
        (
            np.array([[-2.0, 0, 0, 10], [0, 3, 0, 0], [0, 0, 4, 0], [0, 0, 0, 1]]),
            ("8", "4.5", "2"),
            ("6", "12", "8"),
        ),
        (
            np.array([[0.0, -3, 0, 10], [2, 0, 0, 20], [0, 0, 4, 30], [0, 0, 0, 1]]),
            ("5.5", "22", "32"),
            ("12", "6", "8"),
        ),
        (
            np.array([[2.0, 1, 0, 0], [0, 3, 0, 0], [0, 0, 4, 0], [0, 0, 0, 1]]),
            ("3.5", "4.5", "2"),
            ("10", "12", "8"),
        ),
    ],
)
def test_cuboid_volume_centroid_and_voxel_cell_box(affine, centroid, extent):
    mask = np.ones((3, 4, 2), dtype=np.uint16)
    original = mask.copy()
    values = measure_region(mask, canonical_geometry(mask.shape, affine))
    assert values.availability == "available" and values.voxel_count == 24
    assert values.exact_voxel_volume_mm3 == "24"
    assert values.exact_volume_mm3 == "576" and values.volume_cm3 == "0.576"
    assert values.centroid_ras_mm == centroid
    assert values.world_axis_aligned_box_extent_mm == extent
    assert "not_RECIST" in values.extent_definition
    np.testing.assert_array_equal(mask, original)


def test_multilabel_explicit_union_and_precision_preserved_before_rounding():
    mask = np.array([[[1]], [[2]], [[3]]], dtype=np.uint16)
    geometry = canonical_geometry(
        mask.shape, np.diag([0.0012345678912, 2.3456789123, 3.4567891234, 1.0])
    )
    values = measure_region(mask, geometry, (1, 2))
    assert values.voxel_count == 2
    with localcontext() as context:
        context.prec = 80
        independently = (
            Decimal("0.0012345678912") * Decimal("2.3456789123") * Decimal("3.4567891234") * 2
        )
        assert Decimal(values.exact_volume_mm3) == independently
        assert abs(Decimal(values.volume_mm3) - independently) < Decimal("1e-6")
    assert values.exact_volume_mm3 != values.volume_mm3


def test_absence_missing_invalid_and_zero_denominator_are_distinct():
    geometry = canonical_geometry((2, 2, 2), np.eye(4))
    assert measure_region(None, geometry).availability == "unavailable"
    empty = np.zeros((2, 2, 2), dtype=np.uint16)
    unverified = measure_region(empty, geometry)
    assert unverified.availability == "invalid" and unverified.volume_mm3 is None
    absence = measure_region(empty, geometry, verified_absence=True)
    assert absence.availability == "confirmed_absent" and absence.volume_mm3 == "0"
    assert absence.centroid_ras_mm is None
    assert measure_region(np.full((2, 2, 2), np.nan), geometry).availability == "invalid"
    with pytest.raises(ValueError):
        measure_region(empty, geometry, ())
    assert relative_volume_change("10", "0") is None
    assert relative_volume_change(None, "10") is None
    assert relative_volume_change("15", "10") == "50"
