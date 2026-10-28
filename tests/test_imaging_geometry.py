"""Independent coordinate arithmetic on artificial cuboids, not clinical QC."""

from decimal import Decimal

import numpy as np
import pytest
from pydantic import ValidationError
from test_imaging_formats import dicom_bytes, nifti_bytes

from canceros.imaging_formats import parse_dicom_series, parse_nifti
from canceros.imaging_geometry import (
    CanonicalGeometry,
    GeometryError,
    canonical_geometry,
    convert_frame,
    geometry_for,
    index_to_world,
    world_to_index,
)


def test_translated_anisotropic_cuboid_centers_and_support_boundaries():
    affine = [[2, 0, 0, 10], [0, 3, 0, -20], [0, 0, 4, 5], [0, 0, 0, 1]]
    geometry = canonical_geometry((3, 4, 5), affine)
    assert geometry.spacing_mm == ("2", "3", "4")
    assert geometry.voxel_volume_mm3 == "24"
    assert geometry.orientation_axis_codes == ("R", "A", "S")
    assert geometry.handedness == "right"
    assert geometry.phase_count is None
    # Derived by x=10+2i,y=-20+3j,z=5+4k, independently of tested helper.
    np.testing.assert_array_equal(index_to_world(geometry, [1, 2, 3]), [12, -14, 17])
    np.testing.assert_array_equal(world_to_index(geometry, [12, -14, 17]), [1, 2, 3])
    np.testing.assert_array_equal(index_to_world(geometry, [-0.5, -0.5, -0.5]), [9, -21.5, 3])
    np.testing.assert_array_equal(index_to_world(geometry, [2.5, 3.5, 4.5]), [15, -9.5, 23])
    # Full cuboid support is 6*12*20=1440mm3, not center-to-center extents.
    assert Decimal(geometry.voxel_volume_mm3) * 3 * 4 * 5 == 1440
    assert geometry.longitudinal_alignment == "not_established"


def test_rotation_axis_swap_and_reflection_are_not_silently_removed():
    affine = [[0, -3, 0, 10], [2, 0, 0, 20], [0, 0, 4, 30], [0, 0, 0, 1]]
    geometry = canonical_geometry((3, 4, 5), affine)
    assert geometry.orientation_axis_codes == ("A", "L", "S")
    np.testing.assert_array_equal(index_to_world(geometry, [1, 2, 3]), [4, 22, 42])
    reflection = canonical_geometry((3, 4, 5), np.diag([-2, 3, 4, 1]))
    assert reflection.handedness == "left"
    assert reflection.orientation_axis_codes == ("L", "A", "S")
    assert reflection.voxel_volume_mm3 == "24"
    np.testing.assert_array_equal(index_to_world(reflection, [1, 2, 3]), [-2, 6, 12])


def test_oblique_and_sheared_grids_preserve_full_affine_and_determinant_volume():
    c = np.sqrt(0.5)
    affine = np.array([[2 * c, -3 * c, 0.5, 5], [2 * c, 3 * c, 0, 6], [0, 0, 4, 7], [0, 0, 0, 1]])
    geometry = canonical_geometry((10, 11, 12), affine)
    assert geometry.voxel_volume_mm3 == "24"
    # Scalar triple product is 24; column norms multiply to >24 due to shear.
    product = np.prod([float(v) for v in geometry.spacing_mm])
    assert product > 24
    expected = [5 + 2 * c - 6 * c + 1.5, 6 + 2 * c + 6 * c, 19]
    np.testing.assert_allclose(index_to_world(geometry, [1, 2, 3]), expected, atol=1e-12)
    np.testing.assert_array_equal(geometry.affine_ras_mm, affine)
    points = np.array([[0, 0, 0], [9, 10, 11], [1.23, 4.56, 7.89], [-0.5, -0.5, -0.5]])
    worlds = index_to_world(geometry, points)
    recovered = world_to_index(geometry, worlds)
    physical_error = np.linalg.norm(index_to_world(geometry, recovered) - worlds, axis=1)
    assert max(physical_error) <= 1e-5


def test_lps_ras_conversion_has_direction_without_double_spacing_or_reindexing():
    lps = np.array([[2, 0, 0, 10], [0, 3, 0, 20], [0, 0, 4, 30], [0, 0, 0, 1]])
    ras = convert_frame(lps, "LPS", "RAS")
    expected = [[-2, 0, 0, -10], [0, -3, 0, -20], [0, 0, 4, 30], [0, 0, 0, 1]]
    np.testing.assert_array_equal(ras, expected)
    np.testing.assert_array_equal(convert_frame(ras, "RAS", "LPS"), lps)
    geometry = canonical_geometry((3, 4, 5), lps, source_frame="LPS")
    assert geometry.source_transform.conversion_direction == "source_world_to_canonical_world"
    np.testing.assert_array_equal(geometry.source_transform.original_affine, lps)
    np.testing.assert_array_equal(index_to_world(geometry, [1, 2, 3]), [-12, -26, 42])
    assert geometry.spacing_mm == ("2", "3", "4")


@pytest.mark.parametrize(
    "bad",
    [
        np.diag([0, 1, 1, 1]),
        np.diag([1e-4, 1, 1, 1]),
        np.diag([1001, 1, 1, 1]),
        [[1, 1, 0, 0], [0, 1e-9, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, np.nan, 0], [0, 0, 0, 1]],
        [[1, 0, 0, 0], [0, 1, 0, np.inf], [0, 0, 1, 0], [0, 0, 0, 1]],
        [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0.1, 0, 0, 1]],
        np.eye(3),
    ],
)
def test_invalid_geometry_rejected(bad):
    with pytest.raises(GeometryError):
        canonical_geometry((2, 3, 4), bad)


@pytest.mark.parametrize("units", ["unknown", "m", "micron", "voxel", ""])
def test_units_are_never_inferred_or_silently_converted(units):
    with pytest.raises(GeometryError, match="verified millimeter"):
        canonical_geometry((2, 3, 4), np.eye(4), units=units)


def test_fourth_axis_and_resource_limits():
    with pytest.raises(GeometryError, match="explicit DCE"):
        canonical_geometry((2, 3, 4, 2), np.eye(4))
    geometry = canonical_geometry((2, 3, 4, 2), np.eye(4), fourth_axis="dce_phase")
    assert geometry.shape_xyz == (2, 3, 4) and geometry.phase_count == 2
    with pytest.raises((GeometryError, ValidationError)):
        canonical_geometry((1024, 1024, 1024), np.eye(4))
    with pytest.raises((GeometryError, ValidationError)):
        canonical_geometry((2, 3, 4, 17), np.eye(4), fourth_axis="dce_phase")
    for shape in ((0, 3, 4), (True, 3, 4), (2.0, 3, 4), (2, 3)):
        with pytest.raises(GeometryError):
            canonical_geometry(shape, np.eye(4))


def test_geometry_for_both_parsers_preserves_original_transform():
    nifti = geometry_for(parse_nifti(nifti_bytes()))
    assert nifti.shape_xyz == (3, 4, 2)
    assert nifti.source_transform.source_frame == "RAS"
    dicom = geometry_for(parse_dicom_series([dicom_bytes(1), dicom_bytes(0)]))
    assert dicom.shape_xyz == (3, 2, 2)
    assert dicom.source_transform.source_frame == "LPS"
    assert dicom.orientation_axis_codes == ("L", "P", "S")
    assert dicom.voxel_volume_mm3 == "24"


@pytest.mark.parametrize(
    "changes",
    [
        {"spacing_mm": ["1", "1", "1"]},
        {"voxel_volume_mm3": "23"},
        {"handedness": "left"},
        {"orientation_axis_codes": ["A", "R", "S"]},
        {"origin_mm": [10, 0, 0]},
        {"phase_count": 2},
        {"max_roundtrip_error_mm": "1"},
    ],
)
def test_direct_contract_cannot_assert_inconsistent_geometry(changes):
    value = canonical_geometry((2, 3, 4), np.diag([2, 3, 4, 1])).model_dump()
    value.update(changes)
    with pytest.raises(ValidationError):
        CanonicalGeometry.model_validate(value)


def test_bad_coordinates_and_frames_fail_without_source_echo():
    geometry = canonical_geometry((2, 3, 4), np.eye(4))
    for point in ([1, 2], [1, 2, 3, 4], [[1, 2, np.nan]], [1e308, 0, 0], [], "PRIVATE_COORDINATES"):
        with pytest.raises(GeometryError) as caught:
            index_to_world(geometry, point)
        assert "PRIVATE" not in str(caught.value)
    with pytest.raises(GeometryError, match="explicit RAS and LPS"):
        convert_frame(np.eye(4), "unknown", "RAS")
