"""Bounded CPU surfaces in the original patient physical frame; masks remain authoritative."""

from typing import Literal

import numpy as np
from skimage.measure import marching_cubes

from canceros.contracts import Contract
from canceros.imaging_geometry import CanonicalGeometry, index_to_world

MAX_VERTICES = 50_000
MAX_TRIANGLES = 100_000
IDENTITY = ((1.0, 0.0, 0.0, 0.0), (0.0, 1.0, 0.0, 0.0), (0.0, 0.0, 1.0, 0.0), (0.0, 0.0, 0.0, 1.0))


class MeshError(ValueError):
    pass


class Surface(Contract):
    vertices: list[tuple[float, float, float]]
    triangles: list[tuple[int, int, int]]
    normals: list[tuple[float, float, float]]
    bounds_min_mm: tuple[float, float, float]
    bounds_max_mm: tuple[float, float, float]
    frame: Literal["RAS"] = "RAS"
    unit: Literal["mm"] = "mm"
    algorithm: Literal["skimage-0.26.0-lewiner/1"] = "skimage-0.26.0-lewiner/1"
    surface_convention: Literal["binary_0.5_isosurface_one_zero_pad_integer_voxel_centers"] = (
        "binary_0.5_isosurface_one_zero_pad_integer_voxel_centers"
    )
    display_to_patient: tuple[tuple[float, float, float, float], ...] = IDENTITY
    patient_to_display: tuple[tuple[float, float, float, float], ...] = IDENTITY
    measurement_authority: Literal["source_mask_not_surface"] = "source_mask_not_surface"


def reconstruct(mask: np.ndarray, geometry: CanonicalGeometry) -> Surface:
    if (
        mask.shape != geometry.shape_xyz
        or mask.ndim != 3
        or not np.isfinite(mask).all()
        or not np.isin(mask, (0, 1)).all()
    ):
        raise MeshError("finite_binary_mask_on_declared_grid_required")
    if not mask.any():
        raise MeshError("empty_mask_has_no_surface")
    # XYZ input stays XYZ. Unit spacing avoids applying physical scale twice.
    vertices, faces, _, _ = marching_cubes(
        np.pad(mask.astype(np.float32), 1),
        level=0.5,
        spacing=(1, 1, 1),
        gradient_direction="ascent",
        step_size=1,
        allow_degenerate=False,
        method="lewiner",
    )
    if len(vertices) > MAX_VERTICES or len(faces) > MAX_TRIANGLES:
        raise MeshError("surface_budget_exceeded_keep_mask_and_measurements")
    vertices = index_to_world(geometry, vertices.astype(np.float64) - 1)
    faces = faces.astype(np.int64)
    if np.linalg.det(np.asarray(geometry.affine_ras_mm)[:3, :3]) < 0:
        faces = faces[:, [0, 2, 1]]
    # Guard the pinned upstream winding convention; translate for numerical stability.
    shifted = vertices - vertices.mean(axis=0)
    a, b, c = (shifted[faces[:, n]] for n in range(3))
    signed = np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6
    if signed <= 0 or not np.isfinite(signed):
        raise MeshError("unsupported_surface_orientation")
    a, b, c = (vertices[faces[:, n]] for n in range(3))
    face_normals = np.cross(b - a, c - a)
    lengths = np.linalg.norm(face_normals, axis=1)
    if not np.isfinite(vertices).all() or np.any(lengths <= 0):
        raise MeshError("invalid_surface_geometry")
    normals = np.zeros_like(vertices)
    for column in range(3):
        np.add.at(normals, faces[:, column], face_normals)
    lengths = np.linalg.norm(normals, axis=1)
    if np.any(lengths <= 0):
        raise MeshError("unsupported_vertex_normal")
    normals /= lengths[:, None]
    return Surface(
        vertices=vertices.tolist(),
        triangles=faces.tolist(),
        normals=normals.tolist(),
        bounds_min_mm=tuple(vertices.min(axis=0)),
        bounds_max_mm=tuple(vertices.max(axis=0)),
    )
