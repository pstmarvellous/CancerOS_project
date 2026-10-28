"""Conservative exact predicates, invalid surfaces and shape-preserving simplification."""

import numpy as np
from scipy.spatial import ConvexHull

from canceros.imaging_geometry import canonical_geometry
from canceros.mesh_quality import simplify_convex, validate_surface
from canceros.mesh_reconstruction import reconstruct


def cube():
    mask = np.ones((3, 4, 2), dtype=np.uint8)
    return reconstruct(mask, canonical_geometry(mask.shape, np.diag([2.0, 3.0, 4.0, 1.0])))


def changed(surface, vertices=None, triangles=None):
    v = np.array(vertices if vertices is not None else surface.vertices)
    f = np.array(triangles if triangles is not None else surface.triangles)
    normals = np.zeros_like(v)
    cross = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    for i in range(3):
        np.add.at(normals, f[:, i], cross)
    lengths = np.linalg.norm(normals, axis=1)
    normals /= np.maximum(lengths[:, None], 1e-300)
    return surface.model_copy(
        update={
            "vertices": v.tolist(),
            "triangles": f.tolist(),
            "normals": normals.tolist(),
            "bounds_min_mm": tuple(v.min(axis=0)),
            "bounds_max_mm": tuple(v.max(axis=0)),
        }
    )


def test_convex_shape_preserved_exactly_with_separate_reduced_lod():
    original = cube()
    before = original.model_dump_json()
    quality = validate_surface(original)
    lod, comparison = simplify_convex(original)
    assert quality.display_allowed and quality.mesh_volume_mm3 == 484
    assert quality.watertight and quality.component_count == 1
    assert lod and len(lod.triangles) == 44 and len(lod.vertices) == 24
    assert comparison.accepted and comparison.surface_displacement_bound_mm == 0
    assert (
        comparison.bounds_change_mm
        == comparison.volume_centroid_change_mm
        == comparison.volume_fraction_change
        == 0
    )
    assert original.model_dump_json() == before


def test_indices_degeneracy_open_normals_and_nonmanifold_rejected():
    original = cube()
    cases = [
        original.model_copy(
            update={"vertices": [(float("nan"), 0.0, 0.0), *original.vertices[1:]]}
        ),
        original.model_copy(update={"triangles": [(999999, 0, 1), *original.triangles[1:]]}),
        original.model_copy(update={"triangles": [(0, 0, 1), *original.triangles[1:]]}),
        original.model_copy(update={"triangles": original.triangles[:-1]}),
        original.model_copy(update={"triangles": [*original.triangles, original.triangles[0]]}),
        original.model_copy(update={"normals": [(-x, -y, -z) for x, y, z in original.normals]}),
    ]
    for invalid in cases:
        result = validate_surface(invalid)
        assert not result.display_allowed and result.mesh_volume_mm3 is None


def test_multiple_legitimate_components_retained_but_no_unverified_volume():
    mask = np.zeros((7, 3, 3), dtype=np.uint8)
    mask[1, 1, 1] = mask[5, 1, 1] = 1
    original = reconstruct(mask, canonical_geometry(mask.shape, np.eye(4)))
    quality = validate_surface(original)
    assert quality.valid_structure and quality.watertight and quality.component_count == 2
    assert not quality.display_allowed and quality.mesh_volume_mm3 is None
    lod, reason = simplify_convex(original)
    assert lod is None and not reason.accepted and len(original.triangles) == 16


def test_thin_folded_sphere_does_not_pass_with_epsilon_slack():
    v = np.array([(1.0, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)])
    hull = ConvexHull(v)
    f = hull.simplices.copy()
    cross = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    flip = np.einsum("ij,ij->i", cross, hull.equations[:, :3]) < 0
    f[flip] = f[flip][:, [0, 2, 1]]
    v[4] = [3, 0, -0.5]
    v[:, 2] *= 1e-8
    folded = changed(cube(), v, f)
    result = validate_surface(folded)
    assert result.watertight and result.consistently_oriented and result.euler_characteristic == 2
    assert not result.display_allowed and result.mesh_volume_mm3 is None


def test_slight_nonconvex_dent_fails_exact_predicate():
    original = cube()
    v = np.array(original.vertices)
    # Move a coplanar face interior point toward the center by a sub-tolerance amount.
    point = next(i for i, row in enumerate(v) if tuple(row) == (-1.0, 3.0, 0.0))
    v[point, 0] += 1e-9
    result = validate_surface(changed(original, v))
    assert not result.display_allowed


def test_geometric_double_cover_cannot_claim_convex_hull_volume():
    ring = [(1.0, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0)] * 2
    vertices = np.array([*ring, (0, 0, 1), (0, 0, -1)])
    faces = np.array(
        [(8, i, (i + 1) % 8) for i in range(8)] + [(9, (i + 1) % 8, i) for i in range(8)]
    )
    result = validate_surface(changed(cube(), vertices, faces))
    assert not result.display_allowed and result.mesh_volume_mm3 is None
