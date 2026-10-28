"""Independent physical coordinates, surface winding and unchanged mask values."""

import numpy as np
import pytest

from canceros.imaging_geometry import canonical_geometry
from canceros.mesh_reconstruction import MeshError, reconstruct
from canceros.physical_measurements import measure_region


@pytest.mark.parametrize("reflection", [1, -1])
def test_boundary_cube_anisotropic_translated_reflected_and_normals(reflection):
    mask = np.ones((3, 4, 2), dtype=np.uint8)
    affine = np.diag([2.0 * reflection, 3.0, 4.0, 1.0])
    affine[:3, 3] = [10, 20, 30]
    geometry = canonical_geometry(mask.shape, affine)
    before = measure_region(mask, geometry)
    surface = reconstruct(mask, geometry)
    vertices, faces = np.array(surface.vertices), np.array(surface.triangles)
    np.testing.assert_allclose(surface.bounds_min_mm, (9 if reflection == 1 else 5, 18.5, 28))
    np.testing.assert_allclose(surface.bounds_max_mm, (15 if reflection == 1 else 11, 30.5, 36))
    a, b, c = (vertices[faces[:, k]] - vertices.mean(axis=0) for k in range(3))
    assert np.einsum("ij,ij->i", a, np.cross(b, c)).sum() > 0
    np.testing.assert_allclose(np.linalg.norm(surface.normals, axis=1), 1)
    np.testing.assert_allclose(
        np.array(surface.display_to_patient) @ np.array(surface.patient_to_display), np.eye(4)
    )
    assert measure_region(mask, geometry) == before and before.volume_mm3 == "576"
    assert surface.unit == "mm" and surface.measurement_authority == "source_mask_not_surface"


def test_rotated_sheared_single_voxel_and_no_second_spacing_application():
    mask = np.zeros((3, 3, 3), dtype=np.uint8)
    mask[1, 1, 1] = 1
    affine = np.array([[0.0, -3, 1, 10], [2, 0, 0, 20], [0, 0, 4, 30], [0, 0, 0, 1]])
    mesh = reconstruct(mask, canonical_geometry(mask.shape, affine))
    # Single-voxel 0.5 surface has six axis points, not an invented box.
    expected = np.array(
        [[0.5, 1, 1], [1.5, 1, 1], [1, 0.5, 1], [1, 1.5, 1], [1, 1, 0.5], [1, 1, 1.5]]
    )
    expected = expected @ affine[:3, :3].T + affine[:3, 3]
    assert {tuple(v) for v in mesh.vertices} == {tuple(v) for v in expected}


@pytest.mark.parametrize("kind", ["empty", "nan", "illegal", "shape"])
def test_bad_masks_fail_without_surrogate(kind):
    mask = np.ones((2, 2, 2))
    if kind == "empty":
        mask[:] = 0
    if kind == "nan":
        mask[0, 0, 0] = np.nan
    if kind == "illegal":
        mask[0, 0, 0] = 2
    if kind == "shape":
        mask = mask[0]
    with pytest.raises(MeshError):
        reconstruct(mask, canonical_geometry((2, 2, 2), np.eye(4)))
