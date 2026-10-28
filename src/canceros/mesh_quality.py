"""Conservative mesh QC and shape-preserving convex LOD; no general intersection claim."""

from collections import defaultdict, deque
from typing import Literal

import numpy as np
from scipy.spatial import ConvexHull, QhullError

from canceros.contracts import Contract
from canceros.mesh_reconstruction import MAX_TRIANGLES, MAX_VERTICES, Surface

# Frozen engineering display tolerances, never clinical thresholds.
POLICY = "mesh-display/1"
MAX_EXACT_SUPPORT_PRODUCTS = 500_000
MAX_CHANGE_MM = 0.05
MAX_VOLUME_FRACTION = 0.01


def exact_support(vertices, faces, points=None):
    """Exact integer predicates on stored binary64 coordinates, no geometric slack.

    Float denominators are powers of two. Multiplying by the largest denominator
    gives an exact common integer lattice, including translations and reflections.
    False includes a bounded-computation refusal, never an approximate pass.
    """
    points = vertices if points is None else points
    if len(faces) * len(points) > MAX_EXACT_SUPPORT_PRODUCTS:
        return False
    ratios = [[float(x).as_integer_ratio() for x in row] for row in [*vertices, *points]]
    denominator = max(d for row in ratios for _, d in row)
    lattice = [[n * (denominator // d) for n, d in row] for row in ratios]
    source, targets = lattice[: len(vertices)], lattice[len(vertices) :]
    for face in faces:
        a, b, c = (source[int(i)] for i in face)
        u, w = ([b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)])
        normal = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
        if normal == [0, 0, 0]:
            return False
        if any(sum(normal[i] * (point[i] - a[i]) for i in range(3)) > 0 for point in targets):
            return False
    return True


def exact_volume_sum(vertices, faces):
    ratios = [[float(x).as_integer_ratio() for x in row] for row in vertices]
    denominator = max(d for row in ratios for _, d in row)
    lattice = [[n * (denominator // d) for n, d in row] for row in ratios]
    result = 0
    for face in faces:
        a, b, c = (lattice[int(i)] for i in face)
        result += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )
    return result


def outward_hull(vertices):
    hull = ConvexHull(vertices)
    faces = hull.simplices.copy()
    cross = np.cross(
        vertices[faces[:, 1]] - vertices[faces[:, 0]], vertices[faces[:, 2]] - vertices[faces[:, 0]]
    )
    flip = np.einsum("ij,ij->i", cross, hull.equations[:, :3]) < 0
    faces[flip] = faces[flip][:, [0, 2, 1]]
    return faces


class SurfaceQuality(Contract):
    valid_structure: bool
    watertight: bool
    consistently_oriented: bool
    component_count: int
    euler_characteristic: int | None
    self_intersection: Literal["excluded_by_convex_support_certificate", "not_evaluated"]
    display_allowed: bool
    mesh_volume_mm3: float | None
    vertex_centroid_mm: tuple[float, float, float] | None
    failures: list[str]


def validate_surface(surface: Surface) -> SurfaceQuality:
    v, f, n = (
        np.asarray(surface.vertices),
        np.asarray(surface.triangles),
        np.asarray(surface.normals),
    )
    failures = []
    basic = (
        v.ndim == 2
        and v.shape[1:] == (3,)
        and 4 <= len(v) <= MAX_VERTICES
        and f.ndim == 2
        and f.shape[1:] == (3,)
        and 4 <= len(f) <= MAX_TRIANGLES
        and n.shape == v.shape
        and np.isfinite(v).all()
        and np.isfinite(n).all()
        and f.dtype.kind in "iu"
        and f.min() >= 0
        and f.max() < len(v)
    )
    if not basic:
        return SurfaceQuality(
            valid_structure=False,
            watertight=False,
            consistently_oriented=False,
            component_count=0,
            euler_characteristic=None,
            self_intersection="not_evaluated",
            display_allowed=False,
            mesh_volume_mm3=None,
            vertex_centroid_mm=None,
            failures=["invalid_vertices_indices_or_normals"],
        )
    a, b, c = (v[f[:, i]] for i in range(3))
    cross = np.cross(b - a, c - a)
    area2 = np.linalg.norm(cross, axis=1)
    if np.any(area2 <= 1e-12):
        failures.append("degenerate_triangle")
    if len(np.unique(np.sort(f, axis=1), axis=0)) != len(f):
        failures.append("duplicate_triangle")
    if len(np.unique(f)) != len(v):
        failures.append("unreferenced_vertices")
    if len(np.unique(v, axis=0)) != len(v):
        failures.append("duplicate_geometric_vertices")
    if not np.allclose(np.linalg.norm(n, axis=1), 1, atol=1e-6, rtol=0):
        failures.append("invalid_unit_normals")
    # Normals must agree with face winding, including reflected physical frames.
    expected = np.zeros_like(v)
    for i in range(3):
        np.add.at(expected, f[:, i], cross)
    lengths = np.linalg.norm(expected, axis=1)
    if np.any(lengths <= 0) or not np.allclose(
        expected / np.maximum(lengths[:, None], 1e-300), n, atol=1e-6, rtol=0
    ):
        failures.append("normal_winding_mismatch")
    if not (
        np.allclose(v.min(axis=0), surface.bounds_min_mm, atol=1e-8, rtol=0)
        and np.allclose(v.max(axis=0), surface.bounds_max_mm, atol=1e-8, rtol=0)
    ):
        failures.append("declared_bounds_mismatch")
    if not (
        np.array_equal(surface.display_to_patient, np.eye(4))
        and np.array_equal(surface.patient_to_display, np.eye(4))
    ):
        failures.append("unsupported_display_transform")
    edges = defaultdict(list)
    neighbors: dict[int, set[int]] = defaultdict(set)
    for face_id, face in enumerate(f):
        for start, end in zip(face, np.roll(face, -1)):
            edges[tuple(sorted((int(start), int(end))))].append((face_id, start < end))
    watertight = all(len(uses) == 2 for uses in edges.values())
    oriented = watertight and all(uses[0][1] != uses[1][1] for uses in edges.values())
    for uses in edges.values():
        for face_id, _ in uses:
            neighbors[face_id].update(other for other, _ in uses if other != face_id)
    remaining, components = set(range(len(f))), 0
    while remaining:
        components += 1
        pending = deque([remaining.pop()])
        while pending:
            for other in neighbors[pending.popleft()]:
                if other in remaining:
                    remaining.remove(other)
                    pending.append(other)
    euler = len(v) - len(edges) + len(f)
    if not watertight:
        failures.append("open_or_nonmanifold_edges")
    if not oriented:
        failures.append("inconsistent_orientation")
    # A closed edge-manifold can still pinch at a vertex. Require each vertex link
    # to be one connected cycle before treating it as an embedded sphere candidate.
    links = defaultdict(list)
    for face in f:
        for index in range(3):
            links[int(face[index])].append((int(face[(index + 1) % 3]), int(face[(index + 2) % 3])))
    for pairs in links.values():
        link: dict[int, set[int]] = defaultdict(set)
        for start, end in pairs:
            link[start].add(end)
            link[end].add(start)
        link_pending, seen = [next(iter(link))], set()
        while link_pending:
            vertex = link_pending.pop()
            if vertex not in seen:
                seen.add(vertex)
                link_pending.extend(link[vertex] - seen)
        if any(len(adjacent) != 2 for adjacent in link.values()) or len(seen) != len(link):
            failures.append("nonmanifold_vertex_link")
            break
    # Explicitly bounded certificate: a single closed genus-zero convex shell only.
    # Every oriented face must support all vertices; nonconvex/compound shells are
    # retained intact but need a future robust general self-intersection validator.
    convex = not failures and components == 1 and euler == 2 and exact_support(v, f)
    if convex:
        try:
            hull_faces = outward_hull(v)
            convex = exact_support(v, hull_faces) and exact_volume_sum(v, f) == exact_volume_sum(
                v, hull_faces
            )
        except QhullError:
            convex = False
    volume = None
    if convex:
        shifted = v - v.mean(axis=0)
        x, y, z = (shifted[f[:, i]] for i in range(3))
        signed = float(np.einsum("ij,ij->i", x, np.cross(y, z)).sum() / 6)
        if signed <= 0:
            convex = False
        else:
            volume = signed
    if not convex:
        failures.append("general_self_intersection_check_not_established")
    return SurfaceQuality(
        valid_structure=not any(
            x != "general_self_intersection_check_not_established" for x in failures
        ),
        watertight=watertight,
        consistently_oriented=oriented,
        component_count=components,
        euler_characteristic=euler,
        self_intersection="excluded_by_convex_support_certificate" if convex else "not_evaluated",
        display_allowed=convex,
        mesh_volume_mm3=volume,
        vertex_centroid_mm=tuple(v.mean(axis=0)),
        failures=failures,
    )


class LODComparison(Contract):
    accepted: bool
    reason: str
    vertex_reduction: int
    triangle_reduction: int
    bounds_change_mm: float | None
    volume_fraction_change: float | None
    volume_centroid_change_mm: float | None
    surface_displacement_bound_mm: float | None
    displacement_method: Literal["shared_convex_hull_support_certificate", "not_established"]


def volume_centroid(surface: Surface):
    v, f = np.asarray(surface.vertices), np.asarray(surface.triangles)
    origin = v.mean(axis=0)
    a, b, c = (v[f[:, i]] - origin for i in range(3))
    weights = np.einsum("ij,ij->i", a, np.cross(b, c))
    return origin + ((a + b + c) * weights[:, None]).sum(axis=0) / (4 * weights.sum())


def simplify_convex(surface: Surface) -> tuple[Surface | None, LODComparison]:
    original = validate_surface(surface)
    rejected = LODComparison(
        accepted=False,
        reason="original_not_certified_single_convex_shell",
        vertex_reduction=0,
        triangle_reduction=0,
        bounds_change_mm=None,
        volume_fraction_change=None,
        volume_centroid_change_mm=None,
        surface_displacement_bound_mm=None,
        displacement_method="not_established",
    )
    if not original.display_allowed or original.mesh_volume_mm3 is None:
        return None, rejected
    v = np.asarray(surface.vertices)
    try:
        hull = ConvexHull(v)
    except QhullError:
        return None, rejected.model_copy(update={"reason": "convex_hull_failed_keep_original"})
    faces = hull.simplices.copy()
    cross = np.cross(v[faces[:, 1]] - v[faces[:, 0]], v[faces[:, 2]] - v[faces[:, 0]])
    flip = np.einsum("ij,ij->i", cross, hull.equations[:, :3]) < 0
    faces[flip] = faces[flip][:, [0, 2, 1]]
    used, mapped = np.unique(faces, return_inverse=True)
    vertices, faces = v[used], mapped.reshape(-1, 3)
    normals = np.zeros_like(vertices)
    cross = np.cross(
        vertices[faces[:, 1]] - vertices[faces[:, 0]], vertices[faces[:, 2]] - vertices[faces[:, 0]]
    )
    for i in range(3):
        np.add.at(normals, faces[:, i], cross)
    normals /= np.linalg.norm(normals, axis=1)[:, None]
    candidate = Surface.model_validate(
        {
            **surface.model_dump(),
            "vertices": vertices.tolist(),
            "triangles": faces.tolist(),
            "normals": normals.tolist(),
        }
    )
    quality = validate_surface(candidate)
    bounds_delta = float(
        np.max(
            np.abs(
                np.array([surface.bounds_min_mm, surface.bounds_max_mm])
                - np.array([vertices.min(axis=0), vertices.max(axis=0)])
            )
        )
    )
    volume_delta = (
        abs((quality.mesh_volume_mm3 or 0) - original.mesh_volume_mm3) / original.mesh_volume_mm3
    )
    center_delta = float(np.linalg.norm(volume_centroid(candidate) - volume_centroid(surface)))
    accepted = (
        quality.display_allowed
        and exact_support(vertices, faces, v)
        and bounds_delta <= MAX_CHANGE_MM
        and volume_delta <= MAX_VOLUME_FRACTION
        and center_delta <= MAX_CHANGE_MM
    )
    return (candidate if accepted else None), LODComparison(
        accepted=accepted,
        reason="same_convex_boundary_retriangulated"
        if accepted
        else "tolerance_failed_keep_original",
        vertex_reduction=len(surface.vertices) - len(vertices),
        triangle_reduction=len(surface.triangles) - len(faces),
        bounds_change_mm=bounds_delta,
        volume_fraction_change=volume_delta,
        volume_centroid_change_mm=center_delta,
        surface_displacement_bound_mm=0.0 if accepted else None,
        displacement_method="shared_convex_hull_support_certificate"
        if accepted
        else "not_established",
    )
